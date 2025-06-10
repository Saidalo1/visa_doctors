"""Keyboards for Telegram bot."""
from datetime import datetime, timedelta
from calendar import monthcalendar
from typing import List, Dict, Any, Set, Optional

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_surveys_keyboard(surveys: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Get surveys keyboard."""
    keyboard = InlineKeyboardBuilder()
    for survey in surveys:
        keyboard.row(
            InlineKeyboardButton(
                text=survey['title'],
                callback_data=f"survey_{survey['id']}"
            )
        )
    return keyboard.as_markup()


def get_filters_menu(
    filters: List[Dict],
    current_filter: Optional[str] = None,
    current_parent: Optional[str] = None,
    selected_values: Optional[Set[str]] = None
) -> InlineKeyboardMarkup:
    """Get filters menu keyboard."""
    keyboard = InlineKeyboardBuilder()
    selected_values = selected_values or set()
    
    if current_filter and current_parent:
        # Show options for selected parent
        selected_filter = next(
            (f for f in filters if str(f['id']) == current_filter),
            None
        )
        if selected_filter and selected_filter['choices'].get(current_parent):
            parent_data = selected_filter['choices'][current_parent]
            
            # Add parent button first
            check = "⚪️" if set(parent_data['children'].keys()).issubset(selected_values) else ""
            keyboard.row(InlineKeyboardButton(
                text=f"{check} {parent_data['text']}",
                callback_data=f"parent_{current_parent}"
            ))
            
            # Add child options
            for option_id, option_text in parent_data['children'].items():
                check = "⚪️" if option_id in selected_values else ""
                keyboard.row(InlineKeyboardButton(
                    text=f"{check} {option_text}",
                    callback_data=f"option_{option_id}"
                ))
            
            # Add control buttons
            keyboard.row(
                InlineKeyboardButton(
                    text="✅ Готово",
                    callback_data="apply_filter"
                ),
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_filters"
                )
            )
    elif current_filter:
        # Show root options (parents)
        selected_filter = next(
            (f for f in filters if str(f['id']) == current_filter),
            None
        )
        if selected_filter:
            for option_id, option_data in selected_filter['choices'].items():
                # Add arrow for options with children
                prefix = "➡️" if option_data.get('has_children') else ""
                # Check if any children are selected
                has_selected = any(
                    child_id in selected_values 
                    for child_id in option_data['children'].keys()
                ) if option_data.get('has_children') else option_id in selected_values
                check = "⚪️" if has_selected else ""
                text = f"{check} {prefix} {option_data['text']}" if prefix else f"{check} {option_data['text']}"
                keyboard.row(InlineKeyboardButton(
                    text=text,
                    callback_data=f"parent_{option_id}" if option_data.get('has_children') else f"option_{option_id}"
                ))
            
            keyboard.row(
                InlineKeyboardButton(
                    text="✅ Готово",
                    callback_data="apply_filter"
                ),
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_filters"
                )
            )
    else:
        # Show main filters menu
        for filter_item in filters:
            filter_type = filter_item['type']
            filter_id = str(filter_item['id'])
            
            # Add icons based on filter type
            icon = {
                'date': '📅',
                'status': '📊',
                'choice': '📝',
                'text': '✍️'
            }.get(filter_type, '🔍')
            
            keyboard.row(InlineKeyboardButton(
                text=f"{icon} {filter_item['name']}",
                callback_data=f"filter_{filter_type}_{filter_id}"
            ))
            
        # Add control buttons if there are active filters
        keyboard.row(
            InlineKeyboardButton(
                text="🔍 Показать результаты",
                callback_data="show_results"
            ),
            InlineKeyboardButton(
                text="🔄 Сбросить фильтры",
                callback_data="clear_filters"
            )
        )

        # Add back to surveys button
        keyboard.row(InlineKeyboardButton(
            text="🔙 Назад к выбору опроса",
            callback_data="back_to_surveys"
        ))
    
    return keyboard.as_markup()


def get_calendar_keyboard(year: int, month: int, selected_dates: Set[str] = None) -> InlineKeyboardMarkup:
    """
    Create calendar keyboard for date selection.
    
    Args:
        year: Year to display
        month: Month to display (1-12)
        selected_dates: Set of selected dates in YYYY-MM-DD format
        
    Returns:
        InlineKeyboardMarkup with calendar
    """
    keyboard = InlineKeyboardBuilder()
    
    # Get calendar for current month
    cal = monthcalendar(year, month)
    
    # Add month and year as clickable button
    month_name = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'][month - 1]
    keyboard.row(InlineKeyboardButton(
        text=f"📅 {month_name} {year}",
        callback_data=f"select_month-{year}-{month:02d}"  # Using hyphen as separator
    ))
    
    # Add weekday headers
    weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    keyboard.row(*[
        InlineKeyboardButton(
            text=day,
            callback_data="ignore"
        ) for day in weekday_names
    ])
    
    # Add calendar days
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                # Empty day
                row.append(InlineKeyboardButton(
                    text=" ",
                    callback_data="ignore"
                ))
            else:
                # Format date string
                date_str = f"{year}-{month:02d}-{day:02d}"
                # Check if date is selected
                is_selected = selected_dates and date_str in selected_dates
                
                row.append(InlineKeyboardButton(
                    text=f"✓{day}" if is_selected else str(day),
                    callback_data=f"date_{date_str}"
                ))
        keyboard.row(*row)
    
    # Add navigation buttons
    nav_row = []
    
    # Previous month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    nav_row.append(InlineKeyboardButton(
        text="◀️",
        callback_data=f"month-{prev_year}-{prev_month:02d}"  # Using hyphen as separator
    ))
    
    # Back to filters
    nav_row.append(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="back_to_filters"
    ))
    
    # Next month
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    nav_row.append(InlineKeyboardButton(
        text="▶️",
        callback_data=f"month-{next_year}-{next_month:02d}"  # Using hyphen as separator
    ))
    
    keyboard.row(*nav_row)
    
    return keyboard.as_markup()


def get_results_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create results navigation keyboard."""
    builder = InlineKeyboardBuilder()
    
    # Add navigation row if there are multiple pages
    if total_pages > 1:
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️",
                callback_data=f"page_{page - 1}"
            ))
            
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="ignore"
        ))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="➡️",
                callback_data=f"page_{page + 1}"
            ))
            
        builder.row(*nav_buttons)
    
    # Add control buttons
    builder.row(
        InlineKeyboardButton(
            text="🔍 Фильтры",
            callback_data="back_to_filters"
        ),
        InlineKeyboardButton(
            text="🔄 Сбросить",
            callback_data="clear_filters"
        )
    )
    
    # Add export button
    builder.row(InlineKeyboardButton(
        text="📥 Экспорт в Excel",
        callback_data="export_excel"
    ))
    
    return builder.as_markup()
