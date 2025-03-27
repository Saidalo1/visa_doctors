"""Command and message handlers for Telegram bot."""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import tempfile
from datetime import datetime

from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.contrib.admin.sites import site
from django.utils import timezone

from app.admin import SurveySubmissionAdmin
from app.models import Response, SurveySubmission, Question
from bot.filters import SurveyFilter
from bot.keyboards import (
    get_filters_menu,
    get_calendar_keyboard,
    get_results_keyboard
)
from bot.states import FilterStates

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create rotating file handler
file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, 'bot.log'),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3,  # Keep 3 backup files
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add formatter to file handler
file_handler.setFormatter(formatter)

# Remove any existing handlers and add file handler
logger.handlers = []
logger.addHandler(file_handler)

# Add minimal console output for critical errors only
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.CRITICAL)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Constants
RESULTS_PER_PAGE = 5


async def cmd_start(message: types.Message, state: FSMContext):
    """
    Handle /start command.
    Show welcome message and main menu.
    """
    # Create new empty filter manager
    filter_manager = SurveyFilter()
    # Reset state
    await state.clear()
    
    # Get available filters
    filters = await filter_manager.get_available_filters()
    
    # Store initial state
    await state.update_data(
        filter_state=filter_manager.get_state(),
        available_filters=filters  # Store available filters
    )
    
    await message.answer(
        "👋 Добро пожаловать в систему фильтрации заявок!",
        reply_markup=get_filters_menu(filters)
    )


async def show_filters(message: types.Message, state: FSMContext):
    """Show available filters menu."""
    # Get filter state from storage
    data = await state.get_data()
    filter_state = data.get('filter_state', None)
    
    # Create filter manager with state
    filter_manager = SurveyFilter(filter_state)
    filters = await filter_manager.get_available_filters()
    active_filters = await filter_manager.get_active_filters()

    # Store filters in state
    await state.update_data(
        available_filters=filters,
        filter_state=filter_manager.get_state()
    )

    # Format message with active filters
    message_text = "📊 Выберите фильтр из списка:"
    if active_filters:
        message_text += "\n\n📌 Активные фильтры:\n"
        for f in active_filters:
            message_text += f"• {f['name']}: {f['value']}\n"

    await message.answer(
        message_text,
        reply_markup=get_filters_menu(filters)
    )


async def process_filter_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process filter selection from inline keyboard."""
    data = await state.get_data()
    filters = data.get('available_filters', [])
    filter_state = data.get('filter_state', None)
    filter_manager = SurveyFilter(filter_state)
    
    # Parse callback data
    callback_data = callback_query.data
    
    # Handle ignore callback
    if callback_data == "ignore":
        await callback_query.answer()
        return
        
    # Handle filter selection
    if callback_data.startswith("filter_"):
        parts = callback_data.split("_", 2)  # Split into 3 parts max
        if len(parts) != 3:
            await callback_query.answer("❌ Ошибка формата данных")
            return
            
        filter_type = parts[1]
        filter_id = parts[2]
        
        # Find selected filter
        selected_filter = None
        for f in filters:
            if str(f['id']) == str(filter_id):  # Convert both to strings for comparison
                selected_filter = f
                break
                
        if not selected_filter:
            await callback_query.answer("❌ Фильтр не найден")
            return
            
        # Store selected filter
        await state.update_data(selected_filter=selected_filter)
        
        if filter_type == 'date':
            # Show calendar for date selection
            now = datetime.now()
            await callback_query.message.edit_text(
                "📅 Выберите начальную дату диапазона:",
                reply_markup=get_calendar_keyboard(
                    now.year,
                    now.month,
                    filter_manager.selected_dates
                )
            )
        elif filter_type == 'status':
            # Show status selection keyboard
            choices = selected_filter['choices']
            keyboard = InlineKeyboardBuilder()
            for value, label in choices.items():
                keyboard.row(InlineKeyboardButton(
                    text=label,
                    callback_data=f"status_{value}"
                ))
            keyboard.row(InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_filters"
            ))
            await callback_query.message.edit_text(
                "📊 Выберите статус:",
                reply_markup=keyboard.as_markup()
            )
        else:
            first_question = await Question.objects.filter(id=filter_id).afirst()
            # Ask for text input
            await callback_query.message.edit_text(
                # f"✍️ Введите значение для поиска '{selected_filter['name']}':"
                f"✍️ {first_question.title}:"
            )
            await state.set_state(FilterStates.entering_value)
            
        await callback_query.answer()


@sync_to_async
def get_name_responses(submission_ids):
    """Get name responses for submissions efficiently using a single optimized query."""
    return list(Response.objects.filter(
        submission_id__in=submission_ids,
        question__field_type__field_key__iexact='name'
    ).values(
        'submission_id',
        'text_answer',
        'selected_options__text'
    ).distinct())


@sync_to_async
def check_submissions_empty(queryset):
    """Check if queryset is empty in synchronous context."""
    return not queryset.exists()


@sync_to_async
def convert_queryset_to_list(queryset):
    """Convert queryset to list in synchronous context."""
    return list(queryset)


async def show_results(message: types.Message | types.Message, state: FSMContext, edit_message: bool = False):
    """Show filtered results with pagination."""
    data = await state.get_data()
    filter_state = data.get('filter_state', None)
    filter_manager = SurveyFilter(filter_state)
    page = data.get('current_page', 1)

    # Get filtered submissions with all necessary related data
    submissions = await filter_manager.get_filtered_submissions()
    
    # Check if submissions are empty in synchronous context
    if await check_submissions_empty(submissions):
        message_text = (
            "🔍 Ничего не найдено\n\n"
            "📊 Выберите фильтр из списка:"
        )
        active_filters = await filter_manager.get_active_filters()
        if active_filters:
            message_text += "\n\n📌 Активные фильтры:\n"
            for f in active_filters:
                message_text += f"• {f['name']}: {f['value']}\n"
        
        if edit_message and isinstance(message, types.Message):
            await message.edit_text(
                message_text,
                reply_markup=get_filters_menu(await filter_manager.get_available_filters())
            )
        else:
            await message.answer(
                message_text,
                reply_markup=get_filters_menu(await filter_manager.get_available_filters())
            )
        return

    # Convert queryset to list for pagination in synchronous context
    submissions_list = await convert_queryset_to_list(submissions)
    total = len(submissions_list)
    total_pages = (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE

    # Get paginated results
    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    paginated_submissions = submissions_list[start:end]

    # Get name responses for paginated submissions
    name_responses = await get_name_responses([sub.id for sub in paginated_submissions])

    # Create lookup dict for names
    submission_names = {}
    for resp in name_responses:
        sub_id = resp['submission_id']
        if sub_id not in submission_names:  # Take first non-empty value
            submission_names[sub_id] = resp['text_answer'] or resp['selected_options__text'] or "Нет данных"

    # Format results message
    results = []
    for sub in paginated_submissions:
        name = submission_names.get(sub.id, "Нет данных")
        # Make naive datetime timezone-aware
        created_at = timezone.make_aware(sub.created_at) if timezone.is_naive(sub.created_at) else sub.created_at
        results.append(
            f"📝 Заявка #{sub.id}\n"
            f"👤 Имя: {name}\n"
            f"📅 Создана: {timezone.localtime(created_at).strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Статус: {sub.get_status_display()}\n"
        )

    # Add active filters to message
    message_text = f"🔍 Найдено заявок: {total}\n"
    active_filters = await filter_manager.get_active_filters()
    if active_filters:
        message_text += "\n📌 Активные фильтры:\n"
        for f in active_filters:
            message_text += f"• {f['name']}: {f['value']}\n"
    
    message_text += "\n" + "\n---\n".join(results)

    if edit_message and isinstance(message, types.Message):
        await message.edit_text(
            message_text,
            reply_markup=get_results_keyboard(page, total_pages)
        )
    else:
        await message.answer(
            message_text,
            reply_markup=get_results_keyboard(page, total_pages)
        )


@sync_to_async
def perform_export(queryset):
    """Perform export in synchronous context."""
    try:
        logger.info("Starting export process...")
        logger.info(f"Queryset type: {type(queryset)}")
        
        admin = SurveySubmissionAdmin(SurveySubmission, site)
        logger.info("Created admin instance")
        
        formats = admin.get_export_formats()
        logger.info(f"Available formats: {formats}")
        
        file_format = formats[0]()  # Use first available format (usually xlsx)
        logger.info(f"Selected format: {file_format}")
        
        # Get export data
        logger.info("Getting export data...")
        export_data = admin.get_data_for_export(None, queryset)
        logger.info(f"Export data type: {type(export_data)}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            filename = temp_file.name
            logger.info(f"Creating temporary file: {filename}")
            
            # Convert export data to bytes if needed
            export_bytes = file_format.export_data(export_data)
            if isinstance(export_bytes, str):
                export_bytes = export_bytes.encode('utf-8')
                
            temp_file.write(export_bytes)
            logger.info("Data written successfully")
            
        logger.info("Export completed successfully")
        return filename
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        raise


async def export_results(callback_query: types.CallbackQuery, state: FSMContext):
    """Export filtered results to Excel."""
    try:
        data = await state.get_data()
        filter_state = data.get('filter_state', None)
        filter_manager = SurveyFilter(filter_state)

        # Get filtered queryset
        queryset = await filter_manager.get_filtered_submissions()

        if queryset:
            # Perform export in synchronous context
            temp_filename = await perform_export(queryset)

            try:
                # Send file
                await callback_query.message.answer_document(
                    FSInputFile(temp_filename)
                )
                await callback_query.answer("✅ Экспорт выполнен")
            finally:
                # Delete temporary file
                os.unlink(temp_filename)
        else:
            await callback_query.answer("❌ Нет данных для экспорта")

    except Exception as e:
        logger.error(f"Export error: {e}")
        await callback_query.answer("❌ Ошибка при экспорте")


async def clear_filters(message: types.Message | types.CallbackQuery, state: FSMContext):
    """Clear all active filters."""
    try:
        # Create new empty filter manager and get available filters
        filter_manager = SurveyFilter()
        filters = await filter_manager.get_available_filters()
        
        # Reset state and store initial data
        await state.clear()
        await state.update_data(
            filter_state=filter_manager.get_state(),
            available_filters=filters
        )
        
        message_text = (
            "🔄 Все фильтры сброшены\n\n"
            "📊 Выберите фильтр из списка:"
        )
        
        if isinstance(message, types.CallbackQuery):
            await message.message.edit_text(
                message_text,
                reply_markup=get_filters_menu(filters)
            )
            await message.answer()
        else:
            await message.answer(
                message_text,
                reply_markup=get_filters_menu(filters)
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Ignore this error - message is already in desired state
            if isinstance(message, types.CallbackQuery):
                await message.answer("✅ Фильтры уже сброшены")
            return
        raise


async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process callback queries from inline keyboards."""
    if callback_query.data.startswith('filter_'):
        await process_filter_callback(callback_query, state)
    elif callback_query.data.startswith(('date_', 'month_', 'back_to_filters', 'ignore')):
        await process_calendar_callback(callback_query, state)
    elif callback_query.data.startswith('status_'):
        # Handle status selection
        data = await state.get_data()
        filter_state = data.get('filter_state', None)
        filter_manager = SurveyFilter(filter_state)
        
        # Get selected status
        status = callback_query.data.split('_', 1)[1]  # Split only once to get full status
        
        # Set status filter
        await filter_manager.set_status_filter(status)
        
        # Store updated filter state
        await state.update_data(filter_state=filter_manager.get_state())
        
        # Show filters menu with active filters
        filters = await filter_manager.get_available_filters()
        active_filters = await filter_manager.get_active_filters()
        
        message_text = "📊 Выберите фильтр из списка:"
        if active_filters:
            message_text += "\n\n📌 Активные фильтры:\n"
            for f in active_filters:
                message_text += f"• {f['name']}: {f['value']}\n"
                
        await callback_query.message.edit_text(
            message_text,
            reply_markup=get_filters_menu(filters)
        )
    elif callback_query.data.startswith('page_'):
        # Handle pagination
        page = int(callback_query.data.split('_')[1])
        await state.update_data(current_page=page)
        await show_results(callback_query.message, state, edit_message=True)
    elif callback_query.data == 'export_excel':
        # Handle export
        await export_results(callback_query, state)
    elif callback_query.data == 'clear_filters':
        # Handle clear filters
        await clear_filters(callback_query, state)

    await callback_query.answer()


async def process_calendar_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process calendar navigation and date selection."""
    callback_data = callback_query.data
    data = await state.get_data()
    filter_state = data.get('filter_state', None)
    filter_manager = SurveyFilter(filter_state)
    
    logger.debug(f"Calendar callback: {callback_data}")
    logger.debug(f"Current date_filters: {filter_manager.date_filters}")
    logger.debug(f"Current selected_dates: {filter_manager.selected_dates}")
    
    if callback_data == "ignore":
        logger.debug("Ignoring calendar callback")
        await callback_query.answer()
        return
        
    if callback_data == "back_to_filters":
        logger.debug("Going back to filters")
        # Show filters menu again
        filters = await filter_manager.get_available_filters()
        active_filters = await filter_manager.get_active_filters()

        # Format message with active filters
        message_text = "📊 Выберите фильтр из списка:"
        if active_filters:
            message_text += "\n\n📌 Активные фильтры:\n"
            for f in active_filters:
                message_text += f"• {f['name']}: {f['value']}\n"

        await callback_query.message.edit_text(
            message_text,
            reply_markup=get_filters_menu(filters)
        )
        await callback_query.answer()
        return
        
    if callback_data.startswith("month_"):
        # Handle month navigation
        _, year, month = callback_data.split('_')
        logger.debug(f"Navigating to month: {year}-{month}")
        
        # Get date range status and selected dates
        date_range_status = "начальную" if not filter_manager.selected_dates else "конечную"
        selected_dates = list(filter_manager.selected_dates)
        
        message_text = f"📅 Выберите {date_range_status} дату диапазона:"
        if selected_dates:
            start_date = datetime.strptime(selected_dates[0], "%Y-%m-%d")
            message_text += f"\n\n📌 Выбранные даты:\n• Начало: {start_date.strftime('%d.%m.%Y')}"
            if len(selected_dates) > 1:
                end_date = datetime.strptime(selected_dates[1], "%Y-%m-%d")
                message_text += f"\n• Конец: {end_date.strftime('%d.%m.%Y')}"
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=get_calendar_keyboard(
                int(year),
                int(month),
                filter_manager.selected_dates
            )
        )
        await callback_query.answer()
        return
        
    if callback_data.startswith("date_"):
        # Handle date selection
        date_str = callback_data[5:]  # Remove "date_" prefix
        logger.debug(f"Selected date: {date_str}")
        
        try:
            # Parse date
            selected_filter = data.get('selected_filter')
            if not selected_filter:
                logger.error("No filter selected")
                await callback_query.answer("❌ Фильтр не выбран")
                return
                
            logger.debug(f"Current filter: {selected_filter}")
            
            # Toggle date selection
            if date_str in filter_manager.selected_dates:
                logger.debug(f"Removing date: {date_str}")
                filter_manager.selected_dates.remove(date_str)
                # Remove from date filters
                field = selected_filter['id']
                if f"{field}__gte" in filter_manager.date_filters and filter_manager.date_filters[f"{field}__gte"] == date_str:
                    del filter_manager.date_filters[f"{field}__gte"]
                if f"{field}__lte" in filter_manager.date_filters and filter_manager.date_filters[f"{field}__lte"] == date_str:
                    del filter_manager.date_filters[f"{field}__lte"]
            else:
                # Add new date filter
                if len(filter_manager.selected_dates) == 0:
                    logger.debug("Adding first date")
                    # First date - set as start date
                    await filter_manager.add_date_filter(
                        field=selected_filter['id'],
                        start_date=date_str
                    )
                    logger.debug(f"After adding first date - date_filters: {filter_manager.date_filters}")
                    logger.debug(f"After adding first date - selected_dates: {filter_manager.selected_dates}")
                    
                    # Show calendar for end date selection
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    message_text = (
                        "📅 Выберите конечную дату диапазона:\n\n"
                        f"📌 Выбранные даты:\n"
                        f"• Начало: {date.strftime('%d.%m.%Y')}"
                    )
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_calendar_keyboard(
                            date.year,
                            date.month,
                            filter_manager.selected_dates
                        )
                    )
                elif len(filter_manager.selected_dates) == 1:
                    logger.debug("Adding second date")
                    # Second date - set as end date if later than start date
                    start_date = min(list(filter_manager.selected_dates) + [date_str])
                    end_date = max(list(filter_manager.selected_dates) + [date_str])
                    logger.debug(f"Calculated start_date: {start_date}, end_date: {end_date}")
                    
                    # Clear previous filters
                    filter_manager.date_filters.clear()
                    filter_manager.selected_dates.clear()
                    # Add new range
                    await filter_manager.add_date_filter(
                        field=selected_filter['id'],
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    logger.debug(f"After adding date range - date_filters: {filter_manager.date_filters}")
                    logger.debug(f"After adding date range - selected_dates: {filter_manager.selected_dates}")
                    
                    # Store updated filter state BEFORE showing filters menu
                    updated_state = filter_manager.get_state()
                    await state.update_data(filter_state=updated_state)
                    logger.debug(f"Stored updated state after second date: {updated_state}")
                    
                    # Show filters menu after selecting date range
                    filters = await filter_manager.get_available_filters()
                    active_filters = await filter_manager.get_active_filters()
                    
                    message_text = "📊 Выберите фильтр из списка:"
                    if active_filters:
                        message_text += "\n\n📌 Активные фильтры:\n"
                        for f in active_filters:
                            message_text += f"• {f['name']}: {f['value']}\n"
                            
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_filters_menu(filters)
                    )
                    await callback_query.answer("✅ Диапазон дат выбран")
                    return
                else:
                    logger.debug("Resetting date selection")
                    # Reset selection for new range
                    filter_manager.selected_dates.clear()
                    filter_manager.date_filters.clear()
                    await filter_manager.add_date_filter(
                        field=selected_filter['id'],
                        start_date=date_str
                    )
                    
                    # Show calendar for end date selection
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    message_text = (
                        "📅 Выберите конечную дату диапазона:\n\n"
                        f"📌 Выбранные даты:\n"
                        f"• Начало: {date.strftime('%d.%m.%Y')}"
                    )
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_calendar_keyboard(
                            date.year,
                            date.month,
                            filter_manager.selected_dates
                        )
                    )
            
            # Store updated filter state
            await state.update_data(filter_state=filter_manager.get_state())
            logger.debug(f"Stored filter state: {filter_manager.get_state()}")
            
        except ValueError as e:
            logger.error(f"Error processing date: {e}")
            await callback_query.answer("❌ Ошибка при выборе даты")
            return
            
        await callback_query.answer()


async def process_value_input(message: types.Message, state: FSMContext):
    """Process value input and update filters."""
    data = await state.get_data()
    selected_filter = data.get('selected_filter')
    
    logger.debug(f"Processing value input: {message.text}")
    logger.debug(f"Selected filter: {selected_filter}")
    
    if not selected_filter or 'question_id' not in selected_filter:
        logger.error("Invalid filter selected")
        # Show filters menu with error
        filter_manager = SurveyFilter()
        filters = await filter_manager.get_available_filters()
        await message.answer(
            "❌ Ошибка: фильтр не выбран или неверный тип фильтра\n\n"
            "📊 Выберите фильтр из списка:",
            reply_markup=get_filters_menu(filters)
        )
        await state.set_state(None)
        return
        
    filter_state = data.get('filter_state', None)
    logger.debug(f"Current filter state: {filter_state}")
    
    filter_manager = SurveyFilter(filter_state)
    logger.debug(f"Before adding response - date_filters: {filter_manager.date_filters}")
    logger.debug(f"Before adding response - selected_dates: {filter_manager.selected_dates}")

    # Add response filter
    await filter_manager.add_response_filter(
        question_id=selected_filter['question_id'],
        value=message.text
    )

    logger.debug(f"After adding response - date_filters: {filter_manager.date_filters}")
    logger.debug(f"After adding response - selected_dates: {filter_manager.selected_dates}")

    # Store updated filter state
    await state.update_data(filter_state=filter_manager.get_state())
    # Reset state
    await state.set_state(None)

    # Show filters menu with active filters
    filters = await filter_manager.get_available_filters()
    active_filters = await filter_manager.get_active_filters()
    logger.debug(f"Active filters: {active_filters}")

    # Format message with active filters
    message_text = "📊 Выберите фильтр из списка:"
    if active_filters:
        message_text += "\n\n📌 Активные фильтры:\n"
        for f in active_filters:
            message_text += f"• {f['name']}: {f['value']}\n"

    await message.answer(
        message_text,
        reply_markup=get_filters_menu(filters)
    )
