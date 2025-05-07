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
from import_export.formats.base_formats import XLSX

from app.admin import SurveySubmissionAdmin
from app.models import Response, SurveySubmission, Question
from app.resource import SurveySubmissionResource
from bot.filters import SurveyFilter
from bot.keyboards import (
    get_filters_menu,
    get_calendar_keyboard,
    get_results_keyboard
)
from bot.states import FilterStates

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to show all logs

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add console handler for all logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Show all logs
console_handler.setFormatter(formatter)

# Remove any existing handlers
logger.handlers = []
logger.addHandler(console_handler)

# Disable propagation to root logger to avoid duplicate logs
logger.propagate = False

# Constants
RESULTS_PER_PAGE = 5


async def cmd_start(message: types.Message, state: FSMContext):
    """
    Handle /start command.
    Show welcome message and main menu.
    """
    logger.debug("Processing /start command")
    
    # Create new empty filter manager
    filter_manager = SurveyFilter()
    # Reset state
    await state.clear()
    
    # Get available filters
    filters = await filter_manager.get_available_filters()
    logger.debug(f"Available filters: {filters}")
    
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
    try:
        logger.debug(f"Processing filter callback: {callback_query.data}")
        
        data = await state.get_data()
        filters = data.get('available_filters', [])
        filter_state = data.get('filter_state', {})
        current_filter = data.get('current_filter')
        current_parent = data.get('current_parent')
        selected_values = set(data.get('selected_values', []))
        
        logger.debug(f"Current state - filter: {current_filter}, parent: {current_parent}, values: {selected_values}")
        logger.debug(f"Filter state from storage: {filter_state}")
        
        filter_manager = SurveyFilter(filter_state)
        
        # Handle status selection
        if callback_query.data.startswith("status_"):
            logger.debug("Processing status selection")
            status = callback_query.data.split('_', 1)[1]  # Split only once to get full status
            
            # Toggle status selection
            await filter_manager.toggle_status_filter(status)
            
            # Store updated filter state
            updated_state = filter_manager.get_state()
            logger.debug(f"Updating state with: {updated_state}")
            
            # Keep current filter and display status selection menu
            if current_filter == 'status':
                await state.update_data(filter_state=updated_state)
                
                # Get status filter choices
                selected_filter = next(
                    (f for f in filters if f['id'] == 'status'),
                    None
                )
                
                if selected_filter:
                    # Show status selection keyboard with current statuses marked
                    choices = selected_filter['choices']
                    keyboard = InlineKeyboardBuilder()
                    
                    for value, label in choices.items():
                        # Add checkmark for selected status
                        text = f"⚪️ {label}" if value in filter_manager.status_filters else label
                        keyboard.row(InlineKeyboardButton(
                            text=text,
                            callback_data=f"status_{value}"
                        ))
                    
                    # Add control buttons
                    keyboard.row(
                        InlineKeyboardButton(
                            text="✅ Готово",
                            callback_data="back_to_filters"
                        ),
                        InlineKeyboardButton(
                            text="🔙 Назад",
                            callback_data="back_to_filters"
                        )
                    )
                    
                    try:
                        await callback_query.message.edit_text(
                            "📊 Выберите статусы (можно несколько):",
                            reply_markup=keyboard.as_markup()
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" not in str(e):
                            raise
                    
                return
            else:
                # If not in status selection, just update state and return to filters
                await state.update_data(filter_state=updated_state)
                
                # Show filters menu with active filters
                filters = await filter_manager.get_available_filters()
                active_filters = await filter_manager.get_active_filters()
                
                message_text = "📊 Выберите фильтр из списка:"
                if active_filters:
                    message_text += "\n\n📌 Активные фильтры:\n"
                    for f in active_filters:
                        message_text += f"• {f['name']}: {f['value']}\n"
                        
                try:
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_filters_menu(filters)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
                return
                
        # Handle filter selection
        if callback_query.data.startswith("filter_"):
            logger.debug("Processing filter selection")
            parts = callback_query.data.split("_", 2)  # Split into 3 parts max
            
            if len(parts) != 3:
                await callback_query.answer("❌ Ошибка формата данных")
                return
                
            filter_type = parts[1]
            filter_id = parts[2]
            
            logger.debug(f"Filter type: {filter_type}, id: {filter_id}")
            
            # Find selected filter
            selected_filter = next(
                (f for f in filters if str(f['id']) == str(filter_id)),
                None
            )
            
            if not selected_filter:
                await callback_query.answer("❌ Фильтр не найден")
                return
                
            logger.debug(f"Selected filter: {selected_filter}")
            
            # Store current filter and state
            await state.update_data(
                current_filter=filter_id,
                filter_state=filter_state,
                selected_filter=selected_filter,  # Store selected filter
                current_parent=None,
                selected_values=[]
            )
            
            if filter_type == 'status':
                # Show status selection keyboard with current statuses marked
                keyboard = InlineKeyboardBuilder()
                for value, label in selected_filter['choices'].items():
                    # Add checkmark for selected status
                    text = f"⚪️ {label}" if value in filter_manager.status_filters else label
                    keyboard.row(InlineKeyboardButton(
                        text=text,
                        callback_data=f"status_{value}"
                    ))
                
                # Add control buttons
                keyboard.row(
                    InlineKeyboardButton(
                        text="✅ Готово",
                        callback_data="back_to_filters"
                    ),
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="back_to_filters"
                    )
                )
                
                try:
                    await callback_query.message.edit_text(
                        "📊 Выберите статусы (можно несколько):",
                        reply_markup=keyboard.as_markup()
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
                return
                
            if filter_type == 'choice':
                await callback_query.message.edit_text(
                    "Выберите варианты (можно несколько):",
                    reply_markup=get_filters_menu(
                        filters,
                        current_filter=filter_id,
                        selected_values=set()
                    )
                )
            elif filter_type == 'date':
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
            elif filter_type == 'question':
                # Set state for text input
                await state.set_state(FilterStates.entering_value)
                await callback_query.message.edit_text(
                    f"✍️ Введите текст для поиска в поле '{selected_filter['name']}':"
                )
            
            await callback_query.answer()
            
        # Handle clear filters
        if callback_query.data == "clear_filters":
            logger.debug("Processing clear filters")
            # Reset filter state
            new_state = {
                'date_filters': {},
                'response_filters': {},
                'selected_dates': [],
                'status_filters': set()  # Updated to use status_filters instead of status_filter
            }
            await state.update_data(
                filter_state=new_state,
                current_filter=None,
                current_parent=None,
                selected_values=[],
                current_page=1  # Reset page when clearing filters
            )
            
            # Show clean filters menu with new message
            await callback_query.message.answer(
                text="🔍 Выберите фильтры для поиска:",
                reply_markup=get_filters_menu(await filter_manager.get_available_filters())
            )
            # Try to delete old message
            try:
                await callback_query.message.delete()
            except:
                pass
            return
            
        # Handle text filter selection
        if callback_query.data.startswith("filter_text_"):
            filter_id = callback_query.data.split("_")[-1]
            selected_filter = next(
                (f for f in filters if str(f['id']) == filter_id),
                None
            )
            
            if selected_filter:
                # Save current filter and state
                await state.update_data(
                    current_filter=filter_id,
                    filter_state=filter_state
                )
                # Set state to wait for text input
                await state.set_state(FilterStates.entering_value)
                # Create keyboard with back button
                keyboard = InlineKeyboardBuilder()
                keyboard.row(InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_filters"
                ))
                # Ask for input
                await callback_query.message.edit_text(
                    text=f"✍️ Введите значение для фильтра '{selected_filter['name']}':",
                    reply_markup=keyboard.as_markup()
                )
                return
                
        # Handle parent option selection
        if callback_query.data.startswith("parent_"):
            logger.debug("Processing parent option selection")
            option_id = callback_query.data.split('_')[1]
            
            # Find selected filter
            selected_filter = None
            for f in filters:
                if str(f['id']) == current_filter:
                    selected_filter = f
                    break
                    
            if not selected_filter:
                await callback_query.answer("❌ Фильтр не найден")
                return
                
            # If parent is clicked twice, select all children
            if current_parent == option_id:
                # Get all child options
                children = selected_filter['choices'][option_id]['children']
                # Toggle selection of all children
                if set(children.keys()).issubset(selected_values):
                    # If all children are selected, unselect them
                    selected_values.difference_update(children.keys())
                else:
                    # Otherwise, select all children
                    selected_values.update(children.keys())
            else:
                # First click on parent - just show children
                await state.update_data(
                    current_parent=option_id,
                    filter_state=filter_manager.get_state()
                )
            
            # Update state
            await state.update_data(selected_values=list(selected_values))
            
            # Show options menu with parent name
            parent_text = selected_filter['choices'][option_id]['text']
            await callback_query.message.edit_text(
                f"Выберите варианты для {parent_text}:\n(нажмите на {parent_text} еще раз чтобы выбрать все)",
                reply_markup=get_filters_menu(
                    filters,
                    current_filter=current_filter,
                    current_parent=option_id,
                    selected_values=selected_values
                )
            )
            return
            
        # Handle option selection
        if callback_query.data.startswith("option_"):
            logger.debug("Processing option selection")
            option_id = callback_query.data.split('_')[1]
            
            # Find selected filter
            selected_filter = next(
                (f for f in filters if str(f['id']) == current_filter),
                None
            )
            
            if not selected_filter:
                await callback_query.answer("❌ Фильтр не найден")
                return
                
            # Check if option has children
            option_info = None
            for choice_id, choice_info in selected_filter['choices'].items():
                if choice_id == option_id:
                    option_info = choice_info
                    break
                    
            if option_info and option_info.get('has_children', False):
                # If option has children, handle as parent
                await state.update_data(current_parent=option_id)
                await callback_query.message.edit_text(
                    f"Выберите варианты для {option_info['text']}:\n(нажмите на {option_info['text']} еще раз чтобы выбрать все)",
                    reply_markup=get_filters_menu(
                        filters,
                        current_filter=current_filter,
                        current_parent=option_id,
                        selected_values=selected_values
                    )
                )
            else:
                # Toggle selection for option without children
                if option_id in selected_values:
                    selected_values.remove(option_id)
                    logger.debug(f"Removed option {option_id} from selected values")
                else:
                    selected_values.add(option_id)
                    logger.debug(f"Added option {option_id} to selected values")
                
                # Update state with new selected values
                await state.update_data(selected_values=list(selected_values))
                
                # Show updated menu
                try:
                    await callback_query.message.edit_text(
                        "Выберите варианты (можно несколько):",
                        reply_markup=get_filters_menu(
                            filters,
                            current_filter=current_filter,
                            current_parent=current_parent,
                            selected_values=selected_values
                        )
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
            return
            
        # Handle apply filter
        if callback_query.data == "apply_filter":
            logger.debug("Processing apply filter")
            
            if not current_filter:
                await callback_query.answer("❌ Фильтр не выбран")
                return
                
            # If filter has children options
            selected_question = next(
                (f for f in filters if str(f['id']) == current_filter),
                None
            )
            
            if selected_question:
                logger.debug(f"Selected question: {selected_question}")
                
                # Add all selected options to filter
                for option_id in selected_values:
                    logger.debug(f"Adding option filter - question: {current_filter}, value: {option_id}")
                    
                    if selected_question['type'] == 'choice':
                        await filter_manager.add_option_filter(
                            question_id=int(selected_question['question_id']),
                            option_id=option_id
                        )
                
                # Reset current filter and parent
                filter_state = filter_manager.get_state()
                logger.debug(f"Updating state with: {filter_state}")
                await state.update_data(
                    filter_state=filter_state,
                    current_filter=None,
                    current_parent=None,
                    selected_values=[],
                    current_page=1  # Reset page when applying filter
                )
                
                # Show main filters menu with updated filters
                filters = await filter_manager.get_available_filters()
                active_filters = await filter_manager.get_active_filters()
                
                # Format message with active filters
                message_text = "📊 Выберите фильтр из списка:"
                if active_filters:
                    message_text += "\n\n📌 Активные фильтры:\n"
                    for f in active_filters:
                        message_text += f"• {f['name']}: {f['value']}\n"
                        
                # Update message with filters menu
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=get_filters_menu(filters)
                )
                return
            
    except Exception as e:
        logger.error(f"Error in filter callback: {e}", exc_info=True)
        await callback_query.answer("❌ Произошла ошибка")


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
    try:
        logger.debug("Starting show_results")
        data = await state.get_data()
        filter_state = data.get('filter_state', {})
        filter_manager = SurveyFilter(filter_state)
        page = data.get('current_page', 1)
        logger.debug(f"Current page: {page}")

        # Get filtered submissions
        logger.debug("Getting filtered submissions")
        submissions = await filter_manager.get_filtered_submissions()
        
        # Check if submissions are empty
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
            
            try:
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
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    return
                raise
            return

        # Convert queryset to list for pagination
        submissions_list = await convert_queryset_to_list(submissions)
        total = len(submissions_list)
        total_pages = max(1, (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
        logger.debug(f"Total submissions: {total}, Total pages: {total_pages}")

        # Validate that the requested page is valid
        if page > total_pages:
            page = 1  # Reset to first page if current page is invalid
            await state.update_data(current_page=page)
            logger.debug(f"Invalid page requested. Reset to page {page}")

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

        # Use get_results_keyboard for pagination
        keyboard = get_results_keyboard(page, total_pages)
        logger.debug(f"Created keyboard for page {page}/{total_pages}")

        # Send or edit message
        try:
            if edit_message and isinstance(message, types.Message):
                logger.debug("Editing existing message")
                await message.edit_text(
                    message_text,
                    reply_markup=keyboard
                )
            else:
                logger.debug("Sending new message")
                await message.answer(
                    message_text,
                    reply_markup=keyboard
                )
        except TelegramBadRequest as e:
            logger.error(f"Telegram error: {str(e)}")
            if "message is not modified" not in str(e):
                if edit_message and isinstance(message, types.Message):
                    await message.answer(
                        message_text,
                        reply_markup=keyboard
                    )
                    try:
                        await message.delete()
                    except:
                        pass
                else:
                    await message.answer(
                        message_text,
                        reply_markup=keyboard
                    )
            
    except Exception as e:
        logger.error(f"Error showing results: {e}", exc_info=True)
        error_text = "❌ Произошла ошибка при показе результатов"
        if edit_message and isinstance(message, types.Message):
            await message.edit_text(error_text)
        else:
            await message.answer(error_text)


@sync_to_async
def perform_export(queryset):
    """Perform export in synchronous context."""
    try:
        # Используем наш улучшенный SurveySubmissionResource
        resource = SurveySubmissionResource()
        file_format = XLSX()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            filename = temp_file.name
            
            # Экспортируем данные с форматированием
            dataset = resource.export(queryset, file_format=file_format)
            export_bytes = dataset.xlsx
            if isinstance(export_bytes, str):
                export_bytes = export_bytes.encode('utf-8')
                
            temp_file.write(export_bytes)
            
        return filename
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        raise


async def export_results(callback_query: types.CallbackQuery, state: FSMContext):
    """Export filtered results to Excel."""
    try:
        logger.debug("Starting export process")
        data = await state.get_data()
        filter_state = data.get('filter_state', {})
        filter_manager = SurveyFilter(filter_state)

        # Get filtered queryset
        logger.debug("Getting filtered submissions for export")
        queryset = await filter_manager.get_filtered_submissions()

        if queryset:
            # Show processing message
            await callback_query.answer("⏳ Подготовка файла...")
            logger.debug("Starting file preparation")
            
            # Perform export in synchronous context
            try:
                temp_filename = await perform_export(queryset)
                logger.debug(f"File exported successfully to {temp_filename}")

                # Send file
                logger.debug("Sending file to user")
                await callback_query.message.answer_document(
                    FSInputFile(temp_filename, filename="export.xlsx"),
                    caption="✅ Экспорт выполнен успешно"
                )
                logger.debug("File sent successfully")
            except Exception as e:
                logger.error(f"Error during export: {e}", exc_info=True)
                await callback_query.message.answer("❌ Ошибка при экспорте данных")
            finally:
                # Delete temporary file
                try:
                    if 'temp_filename' in locals():
                        os.unlink(temp_filename)
                        logger.debug("Temporary file deleted")
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {e}")
        else:
            logger.debug("No data to export")
            await callback_query.answer("❌ Нет данных для экспорта")

    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        await callback_query.message.answer("❌ Ошибка при экспорте данных")


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
    try:
        logger.debug(f"Processing callback data: {callback_query.data}")
        
        # Handle pagination first
        if callback_query.data.startswith('page_'):
            logger.debug("Processing pagination callback")
            try:
                page = int(callback_query.data.split('_')[1])
                logger.debug(f"Switching to page {page}")
                await state.update_data(current_page=page)
                await show_results(callback_query.message, state, edit_message=True)
                return
            except ValueError as e:
                logger.error(f"Error parsing page number: {e}")
                await callback_query.answer("❌ Ошибка при переключении страницы")
                return
            
        # Handle export next
        elif callback_query.data == 'export_excel':
            logger.debug("Processing export callback")
            await callback_query.answer("⏳ Подготовка файла...")
            await export_results(callback_query, state)
            return
            
        # Handle other callbacks
        elif callback_query.data.startswith('filter_'):
            await process_filter_callback(callback_query, state)
            
        elif callback_query.data.startswith('select_month-'):
            await process_calendar_callback(callback_query, state)
            
        elif callback_query.data.startswith(('date_', 'month-', 'back_to_filters', 'ignore')):
            await process_calendar_callback(callback_query, state)
            
        elif callback_query.data.startswith('status_'):
            await process_filter_callback(callback_query, state)
            
        elif callback_query.data == 'clear_filters':
            await clear_filters(callback_query, state)
            
        elif callback_query.data == 'show_results':
            await show_results(callback_query.message, state, edit_message=True)
            
        elif callback_query.data == 'back_to_filters':
            await process_filter_callback(callback_query, state)
            
        elif callback_query.data.startswith('parent_'):
            await process_filter_callback(callback_query, state)
            
        elif callback_query.data.startswith('option_'):
            await process_filter_callback(callback_query, state)
            
        elif callback_query.data == 'apply_filter':
            await process_filter_callback(callback_query, state)

        # Don't answer callback if it's already been answered
        try:
            await callback_query.answer()
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error processing callback: {e}", exc_info=True)
        await callback_query.answer("❌ Произошла ошибка")


async def process_calendar_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Process calendar selection callbacks."""
    try:
        logger.debug(f"Processing calendar callback: {callback_query.data}")
        
        data = await state.get_data()
        filter_state = data.get('filter_state', {})
        selected_filter = data.get('selected_filter')
        is_selecting_end_date = data.get('is_selecting_end_date', False)
        
        logger.debug(f"Filter state from storage: {filter_state}")
        logger.debug(f"Selected filter: {selected_filter}")
        logger.debug(f"Is selecting end date: {is_selecting_end_date}")
        
        if not selected_filter:
            await callback_query.answer("❌ Фильтр не выбран")
            return
            
        filter_manager = SurveyFilter(filter_state)
        field = selected_filter['id']
        
        # Handle back to filters
        if callback_query.data == "back_to_filters":
            logger.debug("Processing back to filters")
            # Clear current filter and selected values
            await state.update_data(
                current_filter=None,
                current_parent=None,
                selected_values=[],
                selected_filter=None,
                is_selecting_end_date=False
            )
            
            # Show main filters menu
            filters = await filter_manager.get_available_filters()
            active_filters = await filter_manager.get_active_filters()
            
            message_text = "📊 Выберите фильтр:"
            if active_filters:
                message_text += "\n\n📌 Активные фильтры:\n"
                for f in active_filters:
                    message_text += f"• {f['name']}: {f['value']}\n"
            
            try:
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=get_filters_menu(filters)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
            return
            
        # Handle select month (double click)
        if callback_query.data.startswith("select_month-"):
            logger.debug("Processing month selection for entire month")
            year, month = map(int, callback_query.data.split("-")[1:])
            
            # Get first and last day of the month
            import calendar
            _, last_day = calendar.monthrange(year, month)
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"
            
            # Add date filter for entire month
            await filter_manager.add_date_filter(field, start_date, end_date)
            
            # Store updated filter state
            updated_state = filter_manager.get_state()
            logger.debug(f"Updating state with: {updated_state}")
            await state.update_data(
                filter_state=updated_state,
                current_filter=None,
                selected_filter=None,
                is_selecting_end_date=False
            )
            
            # Show main filters menu
            filters = await filter_manager.get_available_filters()
            active_filters = await filter_manager.get_active_filters()
            
            message_text = "📊 Выберите фильтр:"
            if active_filters:
                message_text += "\n\n📌 Активные фильтры:\n"
                for f in active_filters:
                    message_text += f"• {f['name']}: {f['value']}\n"
                    
            try:
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=get_filters_menu(filters)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
            return
            
        # Handle month navigation (single click)
        if callback_query.data.startswith("month-"):
            logger.debug("Processing month selection")
            year, month = map(int, callback_query.data.split("-")[1:])
            
            # Get current field dates
            field_dates = [d for d in filter_manager.selected_dates if d.startswith(f"{field}::")]
            message_text = "📅 Выберите начальную дату:"
            
            if field_dates and is_selecting_end_date:
                start_date = field_dates[0].split("::")[-1]
                message_text = f"📅 Выберите конечную дату (начальная дата: {start_date}):"
            
            # Show calendar for selected month
            try:
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=get_calendar_keyboard(
                        year,
                        month,
                        filter_manager.selected_dates
                    )
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
            return
            
        # Handle date selection
        if callback_query.data.startswith("date_"):
            logger.debug("Processing date selection")
            date_str = callback_query.data.split("_")[1]
            
            # Check if we already have a start date for this field
            field_dates = [d for d in filter_manager.selected_dates if d.startswith(f"{field}::")]
            
            if not field_dates or not is_selecting_end_date:
                # First date selection - set as start date
                await filter_manager.add_date_filter(field, date_str)
                
                # Store updated filter state
                updated_state = filter_manager.get_state()
                logger.debug(f"Updating state with: {updated_state}")
                await state.update_data(
                    filter_state=updated_state,
                    is_selecting_end_date=True
                )
                
                # Show calendar for end date selection
                try:
                    await callback_query.message.edit_text(
                        f"📅 Выберите конечную дату (начальная дата: {date_str}):",
                        reply_markup=get_calendar_keyboard(
                            int(date_str[:4]),  # year
                            int(date_str[5:7]),  # month
                            filter_manager.selected_dates
                        )
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
            else:
                # Second date selection - set as end date
                start_date = field_dates[0].split("::")[-1]
                end_date = date_str
                
                # Update filter with date range
                await filter_manager.add_date_filter(field, start_date, end_date)
                
                # Store updated filter state and return to filters menu
                updated_state = filter_manager.get_state()
                logger.debug(f"Updating state with: {updated_state}")
                await state.update_data(
                    filter_state=updated_state,
                    current_filter=None,
                    selected_filter=None,
                    is_selecting_end_date=False
                )
                
                # Show main filters menu
                filters = await filter_manager.get_available_filters()
                active_filters = await filter_manager.get_active_filters()
                
                message_text = "📊 Выберите фильтр:"
                if active_filters:
                    message_text += "\n\n📌 Активные фильтры:\n"
                    for f in active_filters:
                        message_text += f"• {f['name']}: {f['value']}\n"
                        
                try:
                    await callback_query.message.edit_text(
                        message_text,
                        reply_markup=get_filters_menu(filters)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
            return
            
        # Handle ignore callback
        if callback_query.data == "ignore":
            await callback_query.answer()
            return
            
    except Exception as e:
        logger.error(f"Error in calendar callback: {e}", exc_info=True)
        await callback_query.answer("❌ Произошла ошибка")


async def process_value_input(message: types.Message, state: FSMContext):
    from app.utils.telegram import get_submission_and_update_status, create_submission_keyboard, \
        format_submission_notification
    """Process text input for text filters and comments."""
    try:
        current_state = await state.get_state()
        data = await state.get_data()
        
        # Handle comment input
        if current_state == FilterStates.editing_comment.state:
            submission_id = data.get('editing_submission_id')
            original_message = data.get('original_message_id')
            
            if submission_id and original_message:
                # Update comment in database
                submission = await get_submission_and_update_status(
                    submission_id=submission_id,
                    comment=message.text
                )
                
                # Get updated submission text and keyboard
                message_text = await format_submission_notification(submission_id)
                keyboard = await create_submission_keyboard(submission_id)
                
                # Delete user's message
                await message.delete()
                
                # Update original message with new data
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=original_message,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                await state.clear()
                return
            
        # Handle text filter input
        current_filter = data.get('current_filter')
        filter_state = data.get('filter_state', {})
        
        if not current_filter:
            await message.answer(
                "❌ Ошибка: фильтр не выбран\n\n"
                "🔍 Выберите фильтры для поиска:"
            )
            await state.clear()
            return
            
        # Initialize filter manager with existing state
        filter_manager = SurveyFilter(filter_state)
        
        # Add text filter
        await filter_manager.add_response_filter(
            question_id=int(current_filter),
            value=message.text
        )
        
        # Get updated state
        updated_state = filter_manager.get_state()
        
        # Update state preserving other fields
        await state.update_data(
            filter_state=updated_state,
            current_filter=None,
            current_parent=None,
            selected_values=[]
        )
        
        # Clear FSM state but keep data
        await state.set_state(None)
        
        # Show updated filters menu
        filters = await filter_manager.get_available_filters()
        active_filters = await filter_manager.get_active_filters()
        
        message_text = "📊 Выберите фильтр из списка:"
        if active_filters:
            message_text += "\n\n📌 Активные фильтры:\n"
            for f in active_filters:
                message_text += f"• {f['name']}: {f['value']}\n"
        
        await message.answer(
            text=message_text,
            reply_markup=get_filters_menu(filters)
        )
        
    except Exception as e:
        logger.error(f"Error processing text input: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке значения\n\n"
            "🔍 Выберите фильтры для поиска:"
        )
        await state.clear()
