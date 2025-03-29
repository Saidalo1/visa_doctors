"""Telegram notification functionality."""
import asyncio
import logging
import threading
from asgiref.sync import sync_to_async
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from django.conf import settings
from django.utils import timezone

from app.models import SurveySubmission, Response

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

        # Create inline keyboard with buttons if submission_id is provided
        keyboard = None
        if submission_id:
            keyboard = await create_submission_keyboard(submission_id)

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        await bot.session.close()
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


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
            "*📋 YANGI ARIZA*",
            separator,
            f"*Ariza ID:* #{submission_id}",
            f"*Vaqt:* {current_time}",
            f"*Holati:* {submission.get_status_display()}",
            "",
            "*Ma'lumotlar:*",
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
                message_lines.append(f"""  • *{field_key}:* {response.text_answer or "Ko'rsatilmagan"}""")
                continue

            # Список выбранных опций (если это чекбоксы, селекты и т.д.)
            selected_options = list(response.selected_options.all())

            if selected_options:
                # Сортируем: сначала с родителем, потом одиночные
                sorted_options = sorted(selected_options, key=lambda opt: opt.parent is None)

                if len(sorted_options) > 1:
                    message_lines.append(f"  • *{field_key}:*")
                    for option in sorted_options:
                        # Если у опции есть has_custom_input и пользовательский ввод
                        if option.has_custom_input and response.text_answer:
                            if option.parent:
                                message_lines.append(f"    ◦ {option.parent.text} → {response.text_answer}")
                            else:
                                message_lines.append(f"    ◦ {response.text_answer}")
                        else:
                            if option.parent:
                                message_lines.append(f"    ◦ {option.parent.text} → {option.text}")
                            else:
                                message_lines.append(f"    ◦ {option.text}")
                else:
                    option = sorted_options[0]
                    # Если у опции есть has_custom_input и пользовательский ввод
                    if option.has_custom_input and response.text_answer:
                        if option.parent:
                            message_lines.append(f"  • *{field_key}:* {option.parent.text} → {response.text_answer}")
                        else:
                            message_lines.append(f"  • *{field_key}:* {response.text_answer}")
                    else:
                        if option.parent:
                            message_lines.append(f"  • *{field_key}:* {option.parent.text} → {option.text}")
                        else:
                            message_lines.append(f"  • *{field_key}:* {option.text}")

            # Если пользователь ничего не выбрал
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


async def notify_new_submission(submission_id: int) -> None:
    """
    Send notification about new submission.
    This function runs asynchronously and can be called from Django signals.
    
    Args:
        submission_id: ID of the submission
    """
    try:
        message = await format_submission_notification(submission_id)
        await send_telegram_message(message, submission_id)
        logger.info(f"Telegram notification sent for submission #{submission_id}")
    except Exception as e:
        logger.error(f"Failed to send submission notification: {e}")


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
def get_submission_and_update_status(submission_id: int, new_status: str) -> 'SurveySubmission':
    """
    Получает объект заявки и обновляет его статус.
    
    Args:
        submission_id: ID заявки
        new_status: Новый статус
        
    Returns:
        SurveySubmission: Обновленный объект заявки
    """
    submission = SurveySubmission.objects.get(id=submission_id)
    submission.status = new_status
    submission.save(update_fields=['status'])
    return submission


async def handle_status_callback(callback_query: CallbackQuery, state) -> None:
    """
    Обработчик callback-запроса для изменения статуса заявки.
    
    Args:
        callback_query: Объект callback query от Telegram
        state: Состояние FSM
    """
    try:
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
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
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
    return submission.get_status_display()


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
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
    
    # Получаем все статусы
    keyboard = []
    
    # Добавляем кнопки для каждого статуса
    for status_value, status_label in SurveySubmission.Status.choices:
        # Добавляем маркер к выбранному статусу
        label = f"✓ {str(status_label)}" if status_value == selected_status else str(status_label)
        keyboard.append([InlineKeyboardButton(
            text=label,
            callback_data=f"select_status:{submission_id}:{status_value}"
        )])
    
    # Добавляем кнопки "Готово" и "Назад"
    keyboard.append([
        InlineKeyboardButton(text="✅ Готово", callback_data=f"apply_status:{submission_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_main:{submission_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
