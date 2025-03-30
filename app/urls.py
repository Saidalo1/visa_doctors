from django.urls import path

from app.views import (
    AboutPreviewAPIView, AboutDetailAPIView,
    VisaTypeListAPIView, VisaTypeDetailAPIView,
    ResultCategoryPreviewAPIView, ResultCategoryDetailAPIView,
    UniversityLogoListAPIView, QuestionListAPIView, SurveySubmissionCreateAPIView,
    ContactInfoAPIView, VisaStatusCheckAPIView
)

urlpatterns = [
    # About URLs
    path('about/preview/', AboutPreviewAPIView.as_view(), name='about-preview'),
    path('about/detail/', AboutDetailAPIView.as_view(), name='about-detail'),

    # Visa URLs
    path('visas/check-status/', VisaStatusCheckAPIView.as_view(), name='visa-status-check'),
    path('visas/', VisaTypeListAPIView.as_view(), name='visa-list'),
    path('visas/<slug:slug>/', VisaTypeDetailAPIView.as_view(), name='visa-detail'),

    # Result URLs
    path('results/preview/', ResultCategoryPreviewAPIView.as_view(), name='result-preview'),
    path('results/detail/', ResultCategoryDetailAPIView.as_view(), name='result-detail'),

    # University URLs
    path('universities/logos/', UniversityLogoListAPIView.as_view(), name='university-logos'),
    
    # Contact URLs
    path('contacts/', ContactInfoAPIView.as_view(), name='contacts'),

    # Demand URLs
    path('questions/', QuestionListAPIView.as_view(), name='question-list'),
    path('submit/', SurveySubmissionCreateAPIView.as_view(), name='survey-submit')
]
