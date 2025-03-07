"""Middleware for cache operations."""
from django.utils.deprecation import MiddlewareMixin
from app.utils.cache import invalidate_app_models


class CacheInvalidationMiddleware(MiddlewareMixin):
    """
    Middleware to invalidate cache for POST, PUT, PATCH, DELETE requests in admin.
    
    This helps ensure that when changes are made in the admin interface,
    the API views will always show up-to-date data.
    """
    
    def process_response(self, request, response):
        """Process response to invalidate cache for admin changes."""
        # Only invalidate for successful write operations in admin
        if (
            request.path.startswith('/admin/') and 
            request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and
            200 <= response.status_code < 400
        ):
            invalidate_app_models()
            
        return response
