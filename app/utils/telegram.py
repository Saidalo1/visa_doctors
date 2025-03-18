"""Telegram notification functionality."""
import asyncio
import logging
import threading

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
    Формирует сообщение о новой заявке, используя field_key вместо question.title,
    с декоративными элементами и улучшенным оформлением.
    """
    from app.models import SurveySubmission, Response

    try:
        submission = SurveySubmission.objects.get(id=submission_id)
        current_time = timezone.now().strftime("%d.%m.%Y %H:%M:%S")

        # Разделительная линия
        separator = "━━━━━━━━━━━━━━━━━━━━"

        # Шапка сообщения
        message_lines = [
            "*📋 YANGI ARIZA*",
            separator,
            f"*Ariza ID:* #{submission_id}",
            f"*Vaqt:* {current_time}",
            f"*Holati:* {submission.get_status_display()}",
            "",
            "*Ma'lumotlar:*",
            separator
        ]

        # Получаем ответы по заявке и сортируем по ID вопроса
        responses = (
            Response.objects
            .filter(submission_id=submission_id)
            .select_related('question')
            .prefetch_related('selected_options', 'selected_options__parent')
            .order_by('question_id')
        )

        # Перебираем все ответы
        for response in responses:
            # Используем field_key (если нет, подстраховываемся question.title)
            field_key = response.question.field_type.field_key or response.question.field_type.title or "Unknown field"

            # Список выбранных опций (если это чекбоксы, селекты и т.д.)
            selected_options = list(response.selected_options.all())

            if selected_options:
                # Сортируем: сначала с родителем, потом одиночные
                sorted_options = sorted(selected_options, key=lambda opt: opt.parent is None)

                if len(sorted_options) > 1:
                    message_lines.append(f"  • *{field_key}:*")
                    for option in sorted_options:
                        if option.parent:
                            message_lines.append(f"    ◦ {option.parent.text} → {option.text}")
                        else:
                            message_lines.append(f"    ◦ {option.text}")
                else:
                    option = sorted_options[0]
                    if option.parent:
                        message_lines.append(f"  • *{field_key}:* {option.parent.text} → {option.text}")
                    else:
                        message_lines.append(f"  • *{field_key}:* {option.text}")



            # Если это обычный текстовый ответ
            elif response.text_answer:
                message_lines.append(f"  • *{field_key}:* {response.text_answer}")

            # Если пользователь ничего не ввёл
            else:
                message_lines.append(f"  • *{field_key}:* Ko'rsatilmagan")

        # Добавим нижнюю разделительную линию
        message_lines.append(separator)

        # Закрывающее сообщение
        message_lines.append("")
        message_lines.append("_Batafsil ma'lumot uchun admin panelni tekshiring._")

        return "\n".join(message_lines)

    except Exception as e:
        logger.error(f"Error formatting submission notification: {e}")
        return (
            f"*🔔 YANGI ARIZA #{submission_id}*\n\n"
            "Yangi ariza kelib tushdi. "
            "Batafsil ma'lumot uchun admin panelni tekshiring."
        )


def notify_new_submission_async(submission_id: int) -> None:
    """
    Асинхронно отправляет уведомление о новой заявке в Telegram.
    Запускает процесс в отдельном потоке, не блокируя основной поток обработки запроса.
    
    Args:
        submission_id: ID заявки
    """
    thread = threading.Thread(
        target=notify_new_submission,
        args=(submission_id,),
        daemon=True  # Поток завершится, когда основной процесс завершится
    )
    thread.start()
    logger.info(f"Started background notification thread for submission #{submission_id}")


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
