"""Telegram notification functionality."""
import asyncio
import logging
import html
import threading
from asgiref.sync import sync_to_async

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from django.conf import settings
from django.utils import timezone

from app.models import SurveySubmission, Response, SubmissionStatus
from bot.states import FilterStates
from app.utils.db_reconnect import with_db_reconnect, with_db_reconnect_async

logger = logging.getLogger(__name__)


# --- Telegram Bot and Topic Management Utilities ---

async def get_bot_instance() -> Bot | None:
    """Initializes and returns a Bot instance based on settings.
    Returns None if token is not configured.
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        # This case will be handled in the model's save method to raise ValidationError
        logger.error("TELEGRAM_BOT_TOKEN is not configured.")
        return None
    return Bot(token=token)


async def get_chat_info(bot: Bot, chat_id: str):
    """Gets information about a chat. Raises TelegramAPIError on failure."""
    return await bot.get_chat(chat_id=chat_id)


async def get_chat_member_info(bot: Bot, chat_id: str, user_id: int):
    """Gets information about a member of a chat. Raises TelegramAPIError on failure."""
    return await bot.get_chat_member(chat_id=chat_id, user_id=user_id)


async def check_telegram_permissions_and_forum_status(bot: Bot, chat_id: str) -> tuple[bool, str]:
    """Checks if the chat is a forum and the bot has admin rights to manage topics.
    Returns (True, success_message) or (False, error_message).
    """
    try:
        chat_info = await get_chat_info(bot, chat_id)
    except TelegramAPIError as e:
        logger.warning(f"Could not retrieve chat information for chat_id {chat_id}: {e}")
        return False, f"Could not retrieve chat info: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error retrieving chat info for {chat_id}: {e}", exc_info=True)
        return False, f"Unexpected error retrieving chat info: {e}"

    if not chat_info.is_forum:
        return False, "The specified chat is not a forum (topics are not enabled)."

    try:
        bot_id = bot.id
        member = await get_chat_member_info(bot, chat_id, bot_id)
    except TelegramAPIError as e:
        logger.warning(f"Could not retrieve bot's membership info in chat {chat_id}: {e}")
        return False, f"Could not retrieve bot's membership info for {chat_id}: {e}"
    except Exception as e:
        logger.error(f"Unexpected error retrieving bot's membership info for {chat_id}: {e}", exc_info=True)
        return False, f"Unexpected error retrieving bot's membership info: {e}"

    if member.status not in ['administrator', 'creator']:
        return False, "The bot is not an administrator in the specified chat."

    if not member.can_manage_topics:
        return False, "The bot does not have permission to manage topics in this chat."

    return True, "The bot has the required permissions in the forum chat."


async def create_telegram_forum_topic(bot: Bot, chat_id: str, topic_name: str) -> int | None:
    """Creates a new forum topic. Returns topic_id on success, None on failure."""
    try:
        topic = await bot.create_forum_topic(chat_id=chat_id, name=topic_name)
        logger.info(
            f"Successfully created Telegram topic '{topic_name}' (ID: {topic.message_thread_id}) in chat {chat_id}.")
        return topic.message_thread_id
    except TelegramAPIError as e:
        # This error will be caught in the model's save method to raise ValidationError
        logger.error(f"Telegram API error creating topic '{topic_name}' in chat {chat_id}: {e.message}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating Telegram topic '{topic_name}' in chat {chat_id}: {e}", exc_info=True)
        return None  # Or re-raise a custom exception


async def edit_telegram_forum_topic(bot: Bot, chat_id: str, topic_id: int, new_topic_name: str) -> bool:
    """Edits the name of an existing forum topic. Returns True on success, False on failure."""
    try:
        await bot.edit_forum_topic(chat_id=chat_id, message_thread_id=topic_id, name=new_topic_name)
        logger.info(f"Successfully edited Telegram topic ID {topic_id} in chat {chat_id} to '{new_topic_name}'.")
        return True
    except TelegramAPIError as e:
        # This error will be caught in the model's save method to raise ValidationError
        logger.error(
            f"Telegram API error editing topic ID {topic_id} to '{new_topic_name}' in chat {chat_id}: {e.message}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error editing Telegram topic ID {topic_id} in chat {chat_id}: {e}", exc_info=True)
        return False  # Or re-raise a custom exception


# @with_db_reconnect_async  # Temporarily commented out for debugging
async def get_survey_topic_id_from_submission(submission_id: int) -> int | None:
    """Retrieves the telegram_topic_id from the Survey related to the given submission_id."""
    @sync_to_async(thread_sensitive=True)
    def _get_survey_topic_id_sync():
        try:
            submission = SurveySubmission.objects.select_related('survey').get(id=submission_id)
            if submission.survey and submission.survey.telegram_topic_id is not None:
                return submission.survey.telegram_topic_id
            return None
        except SurveySubmission.DoesNotExist:
            logger.warning(f"SurveySubmission with id {submission_id} does not exist when trying to get topic_id.") # Matched user's log message format
            return None
        except Exception as e:
            # Log the full error with traceback for better debugging
            logger.error(f"Error retrieving survey_topic_id for submission_id {submission_id}: {e}", exc_info=True)
            return None

    # Call the decorated synchronous function (which is now async)
    return await _get_survey_topic_id_sync()


# --- End Telegram Bot and Topic Management Utilities ---

async def notify_admin_about_error(bot: Bot, error: Exception, context: str, submission_id: int = None) -> None:
    """
    Send error notification to admin.
    
    Args:
        bot: Bot instance to use for sending message
        error: Exception that occurred
        context: Context where error occurred
        submission_id: Optional submission ID related to error
    """
    try:
        error_text = str(error)
        if len(error_text) > 100:
            error_text = f"...{error_text[-100:]}"  # Берем последние 100 символов

        message = f"❌ Xatolik: {context}\n"
        if submission_id:
            message += f"Ariza ID: #{submission_id}\n"
        message += f"Xatolik: {error_text}"

        await bot.send_message(
            chat_id=settings.TELEGRAM_ADMIN_ID,
            text=message
        )
    except Exception as admin_error:
        logger.error(f"Failed to notify admin about error: {admin_error}", exc_info=True)


async def send_telegram_message(message: str, submission_id: int = None, survey_topic_id: int | None = None) -> bool:
    """
    Send a message to the configured Telegram chat.
    
    Args:
        message: Formatted message text to send
        submission_id: ID of the submission to create admin link (optional)
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
    enabled = getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False)

    if not all([token, chat_id, enabled]):
        logger.warning(
            "Telegram notifications are not configured properly. "
            "Make sure TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and "
            "TELEGRAM_NOTIFICATIONS_ENABLED are set in settings."
        )
        return False

    bot = None
    actual_topic_id = survey_topic_id
    try:
        bot = await get_bot_instance()
        if not bot:
            # This case should ideally be prevented by checks in Survey.save(),
            # but as a fallback, log and exit if bot isn't configured.
            logger.error("send_telegram_message: Bot instance could not be created. TELEGRAM_BOT_TOKEN likely missing.")
            return False

        if submission_id and actual_topic_id is None:
            # If submission_id is provided and no explicit topic_id, try to get it from survey
            # This call is already async due to @sync_to_async
            actual_topic_id = await get_survey_topic_id_from_submission(submission_id)
            if actual_topic_id:
                logger.info(f"Retrieved topic_id {actual_topic_id} for submission {submission_id} to send message.")
            else:
                logger.info(
                    f"No specific topic_id found for submission {submission_id}, message will be sent to general chat if configured, or fail if chat is forum-only.")

        # Create inline keyboard with buttons if submission_id is provided
        keyboard = None
        if submission_id:
            keyboard = await create_submission_keyboard(submission_id)

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            message_thread_id=actual_topic_id,  # Send to specific topic if ID is available
            disable_web_page_preview=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}", exc_info=True)
        if bot:
            await notify_admin_about_error(
                bot=bot,
                error=e,
                context="Guruhga xabar yuborib bo'lmadi",
                submission_id=submission_id
            )
        return False
    finally:
        if bot:
            await bot.session.close()


@sync_to_async
def get_submission_data(submission_id: int):
    """
    Get submission data from the database.
    
    Args:
        submission_id: Submission ID
        
    Returns:
        tuple: (submission, responses)
    """
    submission = SurveySubmission.objects.get(id=submission_id)
    responses = (
        Response.objects
        .filter(submission_id=submission_id)
        .select_related('question', 'question__field_type')
        .prefetch_related('selected_options', 'selected_options__parent')
        .order_by('question_id')
    )
    return submission, list(responses)


async def format_submission_notification(submission_id: int) -> str:
    """
    Format a message about a new submission, using field_key instead of question.title,
    with decorative elements and improved formatting.
    """
    try:
        submission, responses = await get_submission_data(submission_id)
        current_time = timezone.now().strftime("%d.%m.%Y %H:%M:%S")

        # Separator line
        separator = "━━━━━━━━━━━━━━━━━━━━"

        # Message header
        message_lines = [
            "<b>📋 YANGI ARIZA</b>",
            separator,
            f"<b>Ariza ID:</b> #{submission_id}",
            f"<b>Vaqt:</b> {current_time}",
            f"<b>Holati:</b> {html.escape(submission.status.code)}",
            "",
            "<b>Ma'lumotlar:</b>",
            separator
        ]

        # Iterate through all responses
        for response in responses:
            # Use field_key (if not, use question.title as a fallback)
            field_key = (response.question.field_type.field_key
                         if response.question.field_type
                         else response.question.title)

            # For text responses
            if response.question.input_type == 'text':
                safe_key = html.escape(field_key)
                safe_value = html.escape(response.text_answer or "Ko'rsatilmagan")
                message_lines.append(f"""  • <b>{safe_key}:</b> {safe_value}""")
                continue

            # For multiple choice options (if it's checkboxes, selects, etc.)
            selected_options = list(response.selected_options.all())

            if selected_options:
                # Sort: first with parent, then single
                sorted_options = sorted(selected_options, key=lambda opt: opt.parent is None)

                if len(sorted_options) > 1:
                    safe_key = html.escape(field_key)
                    message_lines.append(f"  • <b>{safe_key}:</b>")
                    for option in sorted_options:
                        # If the option has a custom input and user input
                        if option.has_custom_input and response.text_answer:
                            if option.parent:
                                parent_text = html.escape(option.parent.text)
                                answer_text = html.escape(response.text_answer)
                                message_lines.append(f"    ◦ {parent_text} → {answer_text}")
                            else:
                                answer_text = html.escape(response.text_answer)
                                message_lines.append(f"    ◦ {answer_text}")
                        else:
                            if option.parent:
                                parent_text = html.escape(option.parent.text)
                                option_text = html.escape(option.text)
                                message_lines.append(f"    ◦ {parent_text} → {option_text}")
                            else:
                                option_text = html.escape(option.text)
                                message_lines.append(f"    ◦ {option_text}")
                else:
                    option = sorted_options[0]
                    # If the option has a custom input and user input
                    if option.has_custom_input and response.text_answer:
                        if option.parent:
                            safe_key = html.escape(field_key)
                            parent_text = html.escape(option.parent.text)
                            answer_text = html.escape(response.text_answer)
                            message_lines.append(f"  • <b>{safe_key}:</b> {parent_text} → {answer_text}")
                        else:
                            safe_key = html.escape(field_key)
                            answer_text = html.escape(response.text_answer)
                            message_lines.append(f"  • <b>{safe_key}:</b> {answer_text}")
                    else:
                        if option.parent:
                            safe_key = html.escape(field_key)
                            parent_text = html.escape(option.parent.text)
                            option_text = html.escape(option.text)
                            message_lines.append(f"  • <b>{safe_key}:</b> {parent_text} → {option_text}")
                        else:
                            safe_key = html.escape(field_key)
                            option_text = html.escape(option.text)
                            message_lines.append(f"  • <b>{safe_key}:</b> {option_text}")

            # If the user didn't select anything
            else:
                safe_key = html.escape(field_key)
                message_lines.append(f"  • <b>{safe_key}:</b> Ko'rsatilmagan")

        # Add a comment if it exists
        if submission.comment:
            message_lines.extend([
                "",
                "<b>💬 Izoh:</b>",
                separator,
                html.escape(submission.comment)
            ])

        # Add a bottom separator line
        message_lines.append(separator)

        # Closing message
        message_lines.append("")
        message_lines.append("<i>Batafsil ma'lumot uchun admin panelni tekshiring.</i>")

        return "\n".join(message_lines)

    except Exception as e:
        logger.error(f"Error formatting submission notification: {e}")
        return (
            f"<b>🔔 YANGI ARIZA #{submission_id}</b>\n\n"
            "Yangi ariza kelib tushdi. "
            "Batafsil ma'lumot uchun admin panelni tekshiring."
        )


async def notify_new_submission(submission_id: int) -> None:
    """
    Send notification about new submission.
    This function runs asynchronously and can be called from Django signals.
    
    Args:
        submission_id: ID of the submission
    """
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        message = await format_submission_notification(submission_id)
        await send_telegram_message(message, submission_id)
        logger.info(f"Telegram notification sent for submission #{submission_id}")
    except Exception as e:
        logger.error(f"Failed to send submission notification: {e}")
        await notify_admin_about_error(
            bot=bot,
            error=e,
            context="Yangi ariza haqida xabar yuborib bo'lmadi",
            submission_id=submission_id
        )
    finally:
        await bot.session.close()


def notify_new_submission_async(submission_id: int) -> None:
    """
    Asynchronously sends a notification about a new submission to Telegram.
    Launches the process in a separate thread, not blocking the main request processing thread.
    
    Args:
        submission_id: Submission ID
    """

    async def run_async():
        await notify_new_submission(submission_id)

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_async())
        loop.close()

    thread = threading.Thread(
        target=run_in_thread,
        daemon=True  # The thread will exit when the main process exits
    )
    thread.start()
    logger.info(f"Started background notification thread for submission #{submission_id}")


@sync_to_async
def get_submission_by_id(submission_id: int) -> 'SurveySubmission':
    """Get submission by ID."""
    return SurveySubmission.objects.get(id=submission_id)


@sync_to_async
@with_db_reconnect(max_attempts=3, backoff_time=0.5)
def get_submission_and_update_status(submission_id: int, new_status: str = None,
                                     comment: str = None) -> 'SurveySubmission':
    """
    Get the submission object and update its status or comment.
    
    Args:
        submission_id: Submission ID
        new_status: New status code (optional)
        comment: New comment (optional)
        
    Returns:
        SurveySubmission: Updated submission object
    """
    submission = SurveySubmission.objects.select_related('status').get(id=submission_id)
    update_fields = []

    if new_status:
        try:
            status_obj = SubmissionStatus.objects.get(code=new_status)
            submission.status = status_obj
            update_fields.append('status')
        except SubmissionStatus.DoesNotExist:
            logger.error(f"Status with code '{new_status}' not found")
            raise ValueError(f"Status with code '{new_status}' not found")

    if comment is not None:
        submission.comment = comment
        update_fields.append('comment')

    if update_fields:
        submission.save(update_fields=update_fields)

    return submission


async def handle_comment_callback(callback_query: CallbackQuery, state: FSMContext):
    """Handle comment editing callbacks."""
    try:
        # Get action and parameters
        action, *params = callback_query.data.split(':')

        if action == 'edit_comment':
            # Handle comment editing
            submission_id = int(params[0])

            # Store submission id and original message id for editing
            await state.update_data(
                editing_submission_id=submission_id,
                original_message_id=callback_query.message.message_id
            )
            await state.set_state(FilterStates.editing_comment)

            # Create keyboard with back button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"comment_back:{submission_id}")]
            ])

            await callback_query.message.edit_text(
                "Izoh qoldiring:",
                reply_markup=keyboard
            )
            await callback_query.answer()

        elif action == 'comment_back':
            # Regenerate submission text and keyboard
            submission_id = int(params[0])
            message_text = await format_submission_notification(submission_id)
            keyboard = await create_submission_keyboard(submission_id)
            await callback_query.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

            await state.clear()
            await callback_query.answer()

    except Exception as e:
        logger.error(f"Failed to handle comment callback: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi")


async def handle_status_callback(callback_query: CallbackQuery, state: FSMContext):
    """Handle status selection and update callbacks."""
    try:
        # Get action and parameters
        action, *params = callback_query.data.split(':')

        if action == 'show_status':
            # Show status selection menu
            submission_id = int(params[0])
            keyboard = await create_status_selection_keyboard(submission_id, state)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

        elif action == 'select_status':
            # Save the selected status to the temporary storage and update the keyboard
            submission_id, new_status = params
            await state.update_data(**{f'temp_status_{submission_id}': new_status})
            keyboard = await create_status_selection_keyboard(submission_id, state)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

        elif action == 'apply_status':
            # Apply the selected status
            submission_id = int(params[0])
            data = await state.get_data()
            new_status = data.get(f'temp_status_{submission_id}')

            if new_status:
                # Update status in the database
                await get_submission_and_update_status(submission_id, new_status)

                # Update message
                message = await format_submission_notification(submission_id)
                keyboard = await create_submission_keyboard(submission_id)

                await callback_query.message.edit_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )

                # Clear temporary storage
                await state.update_data(**{f'temp_status_{submission_id}': None})
                await callback_query.answer("Status yangilandi")
            else:
                await callback_query.answer("Iltimos, avval statusni tanlang")

        elif action == 'back_to_main':
            # Return to the main menu
            submission_id = int(params[0])
            keyboard = await create_submission_keyboard(submission_id)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

            # Clear temporary storage
            await state.update_data(**{f'temp_status_{submission_id}': None})

    except Exception as e:
        logger.error(f"Failed to handle status callback: {e}")
        await callback_query.answer("Status yangilashda xatolik yuz berdi")


@sync_to_async
def get_submission_status(submission_id: int) -> str:
    """
    Get the current submission status.
    
    Args:
        submission_id: Submission ID
        
    Returns:
        str: Current submission status
    """
    submission = SurveySubmission.objects.get(id=submission_id)
    return submission.status.name  # Use name instead of the status object


async def create_submission_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """
    Create a keyboard with buttons for the submission.
    
    Args:
        submission_id: Submission ID
        
    Returns:
        InlineKeyboardMarkup: Keyboard object
    """
    # Get base URL and current status
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    admin_url = f"{base_url}/admin/app/surveysubmission/{submission_id}/change/"
    current_status = await get_submission_status(submission_id)

    # Create a keyboard with two buttons
    keyboard = [
        [
            InlineKeyboardButton(text=f"Status: {current_status}", callback_data=f"show_status:{submission_id}"),
            InlineKeyboardButton(text="Admin panelda ko'rish", url=admin_url)
        ],
        [
            InlineKeyboardButton(text="Izoh o'zgartirish", callback_data=f"edit_comment:{submission_id}")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@sync_to_async
def get_all_statuses():
    """Get all statuses from the database."""
    return list(SubmissionStatus.objects.values_list('code', 'name'))


async def create_status_selection_keyboard(submission_id: int, state) -> InlineKeyboardMarkup:
    """
    Create a keyboard for status selection.
    
    Args:
        submission_id: Submission ID
        state: FSM state for getting the selected status
        
    Returns:
        InlineKeyboardMarkup: Keyboard object with statuses
    """
    # Get the selected status from the state
    data = await state.get_data()
    selected_status = data.get(f'temp_status_{submission_id}')

    # Get all statuses asynchronously
    statuses = await get_all_statuses()
    keyboard = []

    # Add buttons for each status
    for status_code, status_name in statuses:
        # Add marker to the selected status
        label = f"✓ {status_name}" if status_code == selected_status else status_name
        keyboard.append([InlineKeyboardButton(
            text=label,
            callback_data=f"select_status:{submission_id}:{status_code}"
        )])

    # Add 'Done' and 'Back' buttons
    keyboard.append([
        InlineKeyboardButton(text="✅ Готово", callback_data=f"apply_status:{submission_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_main:{submission_id}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
