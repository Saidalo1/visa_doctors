"""Management command to run Telegram bot."""
import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from bot import bot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to run Telegram bot."""
    
    help = 'Run Telegram bot for survey submissions filtering'
    
    def handle(self, *args, **options):
        """Run bot."""
        if not all([
            settings.TELEGRAM_BOT_TOKEN,
            settings.TELEGRAM_CHAT_ID,
            settings.TELEGRAM_NOTIFICATIONS_ENABLED
        ]):
            self.stderr.write(
                "Telegram bot is not configured properly. "
                "Check TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and "
                "TELEGRAM_NOTIFICATIONS_ENABLED settings."
            )
            return
            
        try:
            self.stdout.write("Starting Telegram bot...")
            bot.run()
        except KeyboardInterrupt:
            self.stdout.write("Bot stopped by user")
        except Exception as e:
            self.stderr.write(f"Bot crashed: {e}")
            raise 