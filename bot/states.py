"""FSM states for Telegram bot."""
from aiogram.fsm.state import StatesGroup, State


class FilterStates(StatesGroup):
    """States for filter selection and configuration."""
    
    # Main states
    selecting_filter = State()  # Выбор фильтра из списка
    entering_value = State()    # Ввод значения для фильтра
    
    # Date filter states
    selecting_date_type = State()  # Выбор типа даты (от/до)
    entering_date = State()        # Ввод даты
    
    # Question filter states
    entering_text = State()        # Ввод текста для поиска
    selecting_option = State()     # Выбор опции из списка 