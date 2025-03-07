"""Command to invalidate cache."""
from django.core.management.base import BaseCommand
from app.utils.cache import invalidate_app_models


class Command(BaseCommand):
    """Command to invalidate cache for all app models."""
    
    help = 'Invalidate cache for all app models'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--app',
            type=str,
            help='App label to invalidate cache for',
            default='app'
        )
    
    def handle(self, *args, **options):
        """Command handler."""
        app_label = options.get('app')
        
        try:
            invalidate_app_models(app_label)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully invalidated cache for all models in app: {app_label}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error invalidating cache: {str(e)}')
            )
