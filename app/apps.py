from django.apps import AppConfig as DefaultAppConfig
from django.utils.translation import gettext_lazy as _

class AppConfig(DefaultAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = _('Application')
    
    def ready(self):
        """Import signal handlers and apply patches when app is ready."""
        import app.signals  # noqa
        
        # Apply admin patches
        from app.utils.admin_patches import patch_sortable_admin
        patch_applied = patch_sortable_admin()
        
        if patch_applied:
            print("Successfully applied patch for SortableAdminMixin._update_order")
