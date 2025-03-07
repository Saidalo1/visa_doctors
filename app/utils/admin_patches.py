"""Patches for third-party admin modules."""
from functools import wraps
from cacheops import invalidate_model


def patch_sortable_admin():
    """
    Patch adminsortable2's SortableAdminMixin._update_order method to invalidate cache.
    
    This function should be called in the AppConfig.ready() method.
    """
    try:
        from adminsortable2.admin import SortableAdminMixin
        
        # Store the original method
        original_update_order = SortableAdminMixin._update_order
        
        @wraps(original_update_order)
        def patched_update_order(self, updated_items, extra_model_filters):
            """Patched version of _update_order that invalidates cache after bulk_update."""
            result = original_update_order(self, updated_items, extra_model_filters)
            
            # Invalidate the cache for this model
            invalidate_model(self.model)
            
            return result
        
        # Apply the patch
        SortableAdminMixin._update_order = patched_update_order
        
        return True
    except (ImportError, AttributeError):
        return False
