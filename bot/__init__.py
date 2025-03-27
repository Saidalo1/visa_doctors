"""Telegram bot initialization and setup."""
import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.enums.chat_type import ChatType
from aiogram.fsm.storage.redis import RedisStorage
from django.conf import settings

from bot.handlers import (
    cmd_start,
    show_filters,
    process_value_input,
    show_results,
    clear_filters,
    process_filter_callback,
    process_calendar_callback
)
from bot.states import FilterStates

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Show all logs during development

# Create logs directory if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create rotating file handler for root logger
root_file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, 'app.log'),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3,  # Keep 3 backup files
    encoding='utf-8'
)
root_file_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add formatter to handler
root_file_handler.setFormatter(formatter)

# Add console handler for development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Remove any existing handlers and add new ones
root_logger.handlers = []
root_logger.addHandler(root_file_handler)
root_logger.addHandler(console_handler)

# Disable logging for specific loggers
logging.getLogger('aiogram').setLevel(logging.ERROR)
logging.getLogger('django').setLevel(logging.ERROR)
logging.getLogger('django.db.backends').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VisaDoctorsBot:
    """Telegram bot for filtering survey submissions."""

    def __init__(self):
        """Initialize bot instance."""
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.storage: Optional[RedisStorage] = None

    def setup(self) -> None:
        """Initialize bot, dispatcher and register handlers."""
        # Initialize bot and dispatcher
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.storage = RedisStorage.from_url(settings.REDIS_URL)
        self.dp = Dispatcher(storage=self.storage)

        # Register message handlers for private chats only
        self.dp.message.register(cmd_start, Command('start'), F.chat.type == ChatType.PRIVATE)
        self.dp.message.register(process_value_input, FilterStates.entering_value, F.chat.type == ChatType.PRIVATE)
        
        # Register callback handlers with specific filters
        self.dp.callback_query.register(
            process_filter_callback,
            F.message.chat.type == ChatType.PRIVATE,
            lambda c: c.data and (
                c.data.startswith(('filter_', 'option_', 'parent_', 'status_')) or 
                c.data in ('apply_filter', 'back_to_filters', 'show_results', 'clear_filters')
            )
        )
        
        self.dp.callback_query.register(
            process_calendar_callback,
            F.message.chat.type == ChatType.PRIVATE,
            lambda c: c.data and (
                c.data.startswith(('date_', 'month-', 'select_month-')) or 
                c.data == 'back_to_filters'
            )
        )

    async def start(self) -> None:
        """Start polling."""
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error while polling: {e}", exc_info=True)
            raise
        finally:
            await self.bot.session.close()
            if self.storage:
                await self.storage.close()

    def run(self) -> None:
        """Setup and run bot."""
        try:
            self.setup()
            asyncio.run(self.start())
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)
            raise


# Create bot instance
bot = VisaDoctorsBot() 