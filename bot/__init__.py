"""Telegram bot initialization and setup."""
import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
from django.conf import settings

from bot.handlers import (
    cmd_start,
    show_filters,
    process_value_input,
    show_results,
    clear_filters,
    process_callback
)
from bot.states import FilterStates

logger = logging.getLogger(__name__)


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

        # Register message handlers
        self.dp.message.register(cmd_start, Command(commands=['start']))
        # self.dp.message.register(show_filters, F.text == "🔍 Фильтры")
        self.dp.message.register(process_value_input, FilterStates.entering_value)
        # self.dp.message.register(show_results, F.text == "📊 Результаты")
        # self.dp.message.register(clear_filters, F.text == "🔄 Сбросить фильтры")

        # Register callback query handler
        self.dp.callback_query.register(process_callback)

    async def start(self) -> None:
        """Start polling."""
        try:
            logger.info("Starting bot...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error while polling: {e}")
            raise
        finally:
            await self.bot.session.close()

    def run(self) -> None:
        """Setup and run bot."""
        try:
            self.setup()
            asyncio.run(self.start())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopped")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise


# Create bot instance
bot = VisaDoctorsBot() 