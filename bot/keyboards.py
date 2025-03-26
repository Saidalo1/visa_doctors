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
    
    for f in filters:
        if f['type'] == 'date':
            date_filters.append(f)
        else:
            question_filters.append(f)
    
    # Add date filters
    if date_filters:
        for f in date_filters:
            builder.row(InlineKeyboardButton(
                text=f"📅 {f['name']}",
                callback_data=f"filter_date_{f['id']}"
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
    """Create calendar keyboard for date selection."""
    builder = InlineKeyboardBuilder()
    
    # Get calendar for the month
    cal = monthcalendar(year, month)
    current_date = datetime(year, month, 1)
    today = datetime.now().date()
    
    # Russian month names
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    
    # Add month/year header
    builder.row(InlineKeyboardButton(
        text=f"📅 {month_names[month-1]} {year}",
        callback_data="ignore"
    ))
    
    # Add weekday headers
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    builder.row(*[InlineKeyboardButton(
        text=day,
        callback_data="ignore"
    ) for day in weekdays])
    
    # Add days
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(
                    text=" ",
                    callback_data="ignore"
                ))
            else:
                date = datetime(year, month, day).date()
                date_str = date.strftime('%Y-%m-%d')
                
                # Format button text
                if selected_dates and date_str in selected_dates:
                    text = f"✓{day}"  # Selected date
                else:
                    text = str(day)
                    
                row.append(InlineKeyboardButton(
                    text=text,
                    callback_data=f"date_{date_str}"
                ))
        builder.row(*row)
    
    # Add navigation buttons
    prev_month = current_date - timedelta(days=1)
    next_month = datetime(year, month % 12 + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️",
            callback_data=f"month_{prev_month.year}_{prev_month.month}"
        ),
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="back_to_filters"
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=f"month_{next_month.year}_{next_month.month}"
        )
    )
    
    return builder.as_markup()


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
