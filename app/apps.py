from django.apps import AppConfig as DefaultAppConfig
from django.utils.translation import gettext_lazy as _

class AppConfig(DefaultAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = _('Application')
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import app.signals  # noqa
