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
from django.conf import settings
from django.utils import timezone

from app.models import SurveySubmission, Response, SubmissionStatus
from bot.states import FilterStates
from app.utils.db_reconnect import with_db_reconnect, with_db_reconnect_async

logger = logging.getLogger(__name__)


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


async def send_telegram_message(message: str, submission_id: int = None) -> bool:
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
    try:
        bot = Bot(token=token)

        # Create inline keyboard with buttons if submission_id is provided
        keyboard = None
        if submission_id:
            keyboard = await create_submission_keyboard(submission_id)

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True  # Отключаем превью ссылок
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
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
    Получает данные заявки из базы данных.
    
    Args:
        submission_id: ID заявки
        
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
    Формирует сообщение о новой заявке, используя field_key вместо question.title,
    с декоративными элементами и улучшенным оформлением.
    """
    try:
        submission, responses = await get_submission_data(submission_id)
        current_time = timezone.now().strftime("%d.%m.%Y %H:%M:%S")

        # Разделительная линия
        separator = "━━━━━━━━━━━━━━━━━━━━"

        # Шапка сообщения
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

        # Перебираем все ответы
        for response in responses:
            # Используем field_key (если нет, подстраховываемся question.title)
            field_key = (response.question.field_type.field_key 
                        if response.question.field_type 
                        else response.question.title)

            # Если это текстовый вопрос
            if response.question.input_type == 'text':
                safe_key = html.escape(field_key)
                safe_value = html.escape(response.text_answer or "Ko'rsatilmagan")
                message_lines.append(f"""  • <b>{safe_key}:</b> {safe_value}""")
                continue

            # Список выбранных опций (если это чекбоксы, селекты и т.д.)
            selected_options = list(response.selected_options.all())

            if selected_options:
                # Сортируем: сначала с родителем, потом одиночные
                sorted_options = sorted(selected_options, key=lambda opt: opt.parent is None)

                if len(sorted_options) > 1:
                    safe_key = html.escape(field_key)
                    message_lines.append(f"  • <b>{safe_key}:</b>")
                    for option in sorted_options:
                        # Если у опции есть has_custom_input и пользовательский ввод
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
                    # Если у опции есть has_custom_input и пользовательский ввод
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

            # Если пользователь ничего не выбрал
            else:
                safe_key = html.escape(field_key)
                message_lines.append(f"  • <b>{safe_key}:</b> Ko'rsatilmagan")

        # Добавляем комментарий, если он есть
        if submission.comment:
            message_lines.extend([
                "",
                "<b>💬 Izoh:</b>",
                separator,
                html.escape(submission.comment)
            ])

        # Добавим нижнюю разделительную линию
        message_lines.append(separator)

        # Закрывающее сообщение
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
    Асинхронно отправляет уведомление о новой заявке в Telegram.
    Запускает процесс в отдельном потоке, не блокируя основной поток обработки запроса.
    
    Args:
        submission_id: ID заявки
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
        daemon=True  # Поток завершится, когда основной процесс завершится
    )
    thread.start()
    logger.info(f"Started background notification thread for submission #{submission_id}")


@sync_to_async
def get_submission_by_id(submission_id: int) -> 'SurveySubmission':
    """Get submission by ID."""
    return SurveySubmission.objects.get(id=submission_id)


@sync_to_async
@with_db_reconnect(max_attempts=3, backoff_time=0.5)
def get_submission_and_update_status(submission_id: int, new_status: str = None, comment: str = None) -> 'SurveySubmission':
    """
    Получает объект заявки и обновляет его статус или комментарий.
    
    Args:
        submission_id: ID заявки
        new_status: Код нового статуса (опционально)
        comment: Новый комментарий (опционально)
        
    Returns:
        SurveySubmission: Обновленный объект заявки
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
            # Показываем меню выбора статуса
            submission_id = int(params[0])
            keyboard = await create_status_selection_keyboard(submission_id, state)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

        elif action == 'select_status':
            # Сохраняем выбранный статус во временное хранилище и обновляем клавиатуру
            submission_id, new_status = params
            await state.update_data(**{f'temp_status_{submission_id}': new_status})
            keyboard = await create_status_selection_keyboard(submission_id, state)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

        elif action == 'apply_status':
            # Применяем выбранный статус
            submission_id = int(params[0])
            data = await state.get_data()
            new_status = data.get(f'temp_status_{submission_id}')

            if new_status:
                # Обновляем статус в базе данных
                await get_submission_and_update_status(submission_id, new_status)

                # Обновляем сообщение
                message = await format_submission_notification(submission_id)
                keyboard = await create_submission_keyboard(submission_id)

                await callback_query.message.edit_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )

                # Очищаем временное хранилище
                await state.update_data(**{f'temp_status_{submission_id}': None})
                await callback_query.answer("Status yangilandi")
            else:
                await callback_query.answer("Iltimos, avval statusni tanlang")

        elif action == 'back_to_main':
            # Возвращаемся к основному меню
            submission_id = int(params[0])
            keyboard = await create_submission_keyboard(submission_id)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard)

            # Очищаем временное хранилище
            await state.update_data(**{f'temp_status_{submission_id}': None})

    except Exception as e:
        logger.error(f"Failed to handle status callback: {e}")
        await callback_query.answer("Status yangilashda xatolik yuz berdi")


@sync_to_async
def get_submission_status(submission_id: int) -> str:
    """
    Получает текущий статус заявки.
    
    Args:
        submission_id: ID заявки
        
    Returns:
        str: Текущий статус заявки
    """
    submission = SurveySubmission.objects.get(id=submission_id)
    return submission.status.name  # Используем name вместо самого объекта


async def create_submission_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками для заявки.
    
    Args:
        submission_id: ID заявки
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры
    """
    # Получаем базовый URL и текущий статус
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    admin_url = f"{base_url}/admin/app/surveysubmission/{submission_id}/change/"
    current_status = await get_submission_status(submission_id)
    
    # Создаем клавиатуру с двумя кнопками
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
    """Получает все статусы из базы данных."""
    return list(SubmissionStatus.objects.values_list('code', 'name'))

async def create_status_selection_keyboard(submission_id: int, state) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора статуса.
    
    Args:
        submission_id: ID заявки
        state: Состояние FSM для получения выбранного статуса
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры со статусами
    """
    # Получаем выбранный статус из состояния
    data = await state.get_data()
    selected_status = data.get(f'temp_status_{submission_id}')
    
    # Получаем все статусы асинхронно
    statuses = await get_all_statuses()
    keyboard = []
    
    # Добавляем кнопки для каждого статуса
    for status_code, status_name in statuses:
        # Добавляем маркер к выбранному статусу
        label = f"✓ {status_name}" if status_code == selected_status else status_name
        keyboard.append([InlineKeyboardButton(
            text=label,
            callback_data=f"select_status:{submission_id}:{status_code}"
        )])
    
    # Добавляем кнопки "Готово" и "Назад"
    keyboard.append([
        InlineKeyboardButton(text="✅ Готово", callback_data=f"apply_status:{submission_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_main:{submission_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
