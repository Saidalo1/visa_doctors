from django.apps import AppConfig as DefaultAppConfig
from django.utils.translation import gettext_lazy as _

class AppConfig(DefaultAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = _('Application')
