from django.urls import path

from app.views import (
    AboutPreviewAPIView, AboutDetailAPIView,
    VisaTypeListAPIView, VisaTypeDetailAPIView,
    ResultCategoryPreviewAPIView, ResultCategoryDetailAPIView,
    UniversityLogoListAPIView, QuestionListAPIView, SurveySubmissionCreateAPIView
)

urlpatterns = [
    # About URLs
    path('about/<slug:slug>/preview/', AboutPreviewAPIView.as_view(), name='about-preview'),
    path('about/<slug:slug>/detail/', AboutDetailAPIView.as_view(), name='about-detail'),

    # Visa URLs
    path('visas/', VisaTypeListAPIView.as_view(), name='visa-list'),
    path('visas/<slug:slug>/', VisaTypeDetailAPIView.as_view(), name='visa-detail'),

    # Result URLs
    path('results/<int:pk>/preview/', ResultCategoryPreviewAPIView.as_view(), name='result-preview'),
    path('results/<int:pk>/detail/', ResultCategoryDetailAPIView.as_view(), name='result-detail'),

    # University URLs
    path('universities/logos/', UniversityLogoListAPIView.as_view(), name='university-logos'),

    # Demand URLs
    path('questions/', QuestionListAPIView.as_view(), name='question-list'),
    path('submit/', SurveySubmissionCreateAPIView.as_view(), name='survey-submit'),

]
