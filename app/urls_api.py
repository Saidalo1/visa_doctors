"""URL configuration for admin mobile API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from app.views.admin_api import SurveySubmissionViewSet, SubmissionStatusViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'submissions', SurveySubmissionViewSet, basename='submission')
router.register(r'statuses', SubmissionStatusViewSet, basename='status')

# URL patterns for API
urlpatterns = [
    # JWT Authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints
    path('', include(router.urls)),
]
