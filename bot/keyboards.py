"""Keyboards for Telegram bot."""
from datetime import datetime, timedelta
from calendar import monthcalendar
from typing import List, Dict, Any, Set

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_filters_menu(filters: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Create filters menu keyboard."""
    builder = InlineKeyboardBuilder()
    
    # Group filters by type
    date_filters = []
    question_filters = []
    status_filter = None
    
    for f in filters:
        if f['type'] == 'date':
            date_filters.append(f)
        elif f['type'] == 'status':
            status_filter = f
        else:
            question_filters.append(f)
    
    # Add date filters
    if date_filters:
        for f in date_filters:
            builder.row(InlineKeyboardButton(
                text=f"📅 {f['name']}",
                callback_data=f"filter_date_{f['id']}"
            ))
    
    # Add status filter if available
    if status_filter:
        builder.row(InlineKeyboardButton(
            text=f"📊 {status_filter['name']}",
            callback_data=f"filter_status_{status_filter['id']}"
        ))
    
    # Add question filters
    if question_filters:
        for f in question_filters:
            builder.row(InlineKeyboardButton(
                text=f"❓ {f['name']}",
                callback_data=f"filter_question_{f['id']}"
            ))
    
    # Add control buttons
    builder.row(
        InlineKeyboardButton(
            text="📊 Результаты",
            callback_data="page_1"  # Show first page of results
        ),
        InlineKeyboardButton(
            text="🔄 Сбросить",
            callback_data="clear_filters"
        )
    )
    
    return builder.as_markup()


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
    
    # Add navigation row
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"page_{page - 1}"
        ))
        
    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {page}/{total_pages}",
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
