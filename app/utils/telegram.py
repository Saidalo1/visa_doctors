"""Telegram notification functionality."""
import logging
import asyncio

from django.conf import settings
from django.utils import timezone
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


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
        
    try:
        bot = Bot(token=token)
        
        # Create inline keyboard with admin URL if submission_id is provided
        keyboard = None
        if submission_id:
            # Generate admin URL for the submission
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            admin_url = f"{base_url}/admin/app/surveysubmission/{submission_id}/change/"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Admin panelda ko'rish", url=admin_url)]
            ])
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


def format_submission_notification(submission_id: int) -> str:
    """
    Format a notification message for a new submission.
    
    Args:
        submission_id: ID of the submission
        
    Returns:
        str: Formatted message
    """
    from app.models import SurveySubmission, Response
    
    try:
        # Get submission details
        submission = SurveySubmission.objects.get(id=submission_id)
        
        # Current date and time
        current_time = timezone.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Basic message structure
        message = [
            f"*📋 YANGI ARIZA*",
            f"",
            f"*Ariza ID:* #{submission_id}",
            f"*Vaqt:* {current_time}",
            f"*Holati:* {submission.get_status_display()}",
            f"",
        ]
        
        # Get all response data and organize by question type
        responses = Response.objects.filter(submission_id=submission_id).select_related('question', 'question__field_type')
        
        if responses.exists():
            message.append(f"*Ma'lumot:*")
            
            # Group responses by field type
            responses_by_type = {}
            for response in responses:
                field_type = response.question.field_type.title
                if field_type not in responses_by_type:
                    responses_by_type[field_type] = []
                responses_by_type[field_type].append(response)
            
            # Process each field type group
            for field_type, type_responses in responses_by_type.items():
                message.append(f"\n*{field_type}:*")
                
                for response in type_responses:
                    question_title = response.question.title
                    
                    # Format answer based on question type
                    if response.text_answer:
                        answer = response.text_answer
                    elif response.selected_options.exists():
                        options = [opt.text for opt in response.selected_options.all()]
                        answer = ", ".join(options)
                    else:
                        answer = "Ko'rsatilmagan"
                    
                    # Add to message with truncation to avoid too long messages
                    if len(answer) > 100:
                        answer = answer[:97] + "..."
                    
                    message.append(f"• {question_title}: {answer}")
        
        message.append(f"")
        message.append(f"_Batafsil ma'lumot uchun admin panelni tekshiring._")
        
        return "\n".join(message)
    except Exception as e:
        logger.error(f"Error formatting submission notification: {e}")
        # Fallback to simple message on error
        return f"*🔔 YANGI ARIZA #{submission_id}*\n\nYangi ariza kelib tushdi. Batafsil ma'lumot uchun admin panelni tekshiring."


def notify_new_submission(submission_id: int) -> None:
    """
    Send notification about new submission.
    This function runs synchronously and can be called from Django signals.
    
    Args:
        submission_id: ID of the submission
    """
    message = format_submission_notification(submission_id)
    
    try:
        # Create new event loop for async call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_message(message, submission_id))
        loop.close()
        logger.info(f"Telegram notification sent for submission #{submission_id}")
    except Exception as e:
        logger.error(f"Failed to send submission notification: {e}")
