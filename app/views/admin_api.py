from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters import FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.filters import SurveySubmissionAPIFilter
from app.models import SurveySubmission, Question, SubmissionStatus, Response as SurveyResponse, Survey
from app.serializers.admin_api import (
    SurveySubmissionListSerializer, SurveySubmissionDetailSerializer,
    QuestionFilterSerializer, SubmissionStatusSerializer
)
from shared.django import CustomPagination


class IsStaffOrAdmin(IsAuthenticated):
    """
    Permission to allow access only to admin or staff users.
    """

    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view) and
            (request.user.is_staff or request.user.is_superuser)
        )


class SurveySubmissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for survey submissions that mimics the behavior of SurveySubmissionAdmin.
    """
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated, IsStaffOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SurveySubmissionAPIFilter
    search_fields = ['responses__text_answer', 'comment']
    ordering_fields = ['created_at', 'id']
    ordering = ['-created_at']
    pagination_class = CustomPagination

    _cached_question_filters = None  # Used by available_filters()

    def get_serializer_class(self):
        if self.action == 'list':
            return SurveySubmissionListSerializer
        return SurveySubmissionDetailSerializer

    def get_queryset(self):
        # Determine active survey
        self.active_survey = None  # Initialize
        survey_id_param = self.request.query_params.get('survey')

        if survey_id_param:
            try:
                survey_id = int(survey_id_param)
                self.active_survey = Survey.objects.filter(id=survey_id, is_active=True).first()
            except ValueError:
                # Invalid survey_id format, active_survey remains None
                pass
        
        if not self.active_survey:  # If no survey_id provided or survey not found/active
            # Try to get the default survey
            default_survey = Survey.objects.filter(is_default=True, is_active=True).first()
            if default_survey:
                self.active_survey = default_survey
            else:
                # Fallback to the first active survey if no default is set
                first_active_survey = Survey.objects.filter(is_active=True).order_by('id').first()
                if first_active_survey:
                    self.active_survey = first_active_survey

        # Base queryset
        queryset = SurveySubmission.objects.select_related('status', 'survey').prefetch_related(
            Prefetch('responses',
                     queryset=SurveyResponse.objects.select_related('question', 'question__field_type')
                     .prefetch_related('selected_options'))
        )

        # Filter by active survey if one is determined
        if self.active_survey:
            queryset = queryset.filter(survey=self.active_survey)

        # Apply dynamic filtering based on query params like question_ or option_
        # This should apply to the already survey-filtered queryset if active_survey is set
        for param, value in self.request.query_params.items():
            if param.startswith('question_') and self.active_survey:
                try:
                    question_id = int(param.split('_')[1])
                    # Ensure this question_id belongs to the active_survey to prevent cross-survey filtering
                    if self.active_survey.questions.filter(id=question_id).exists():
                        queryset = queryset.filter(
                            responses__question_id=question_id,
                            responses__text_answer__icontains=value
                        ).distinct()
                except (ValueError, IndexError):
                    pass
            elif param.startswith('option_') and self.active_survey:
                try:
                    option_id = int(param.split('_')[1])
                    # Ensure this option_id belongs to a question in the active_survey
                    if Question.objects.filter(survey=self.active_survey, options__id=option_id).exists():
                        queryset = queryset.filter(
                            responses__selected_options__id=option_id
                        ).distinct()
                except (ValueError, IndexError):
                    pass

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        all_questions_for_active_survey = []
        title_question = None

        # self.active_survey should have been set by get_queryset by the time this is called
        if hasattr(self, 'active_survey') and self.active_survey:
            all_questions_for_active_survey = Question.objects.filter(survey=self.active_survey).order_by('order')
            
            if self.action == 'list':
                # Find the question marked as 'is_title' for the active survey
                try:
                    title_question = all_questions_for_active_survey.get(is_title=True)
                except Question.DoesNotExist:
                    title_question = None # Or log a warning if a title question is expected
        
        context['questions'] = all_questions_for_active_survey # All questions for the active survey
        context['title_question'] = title_question # Specific question to be used as title in list view
        
        # Optionally pass active_survey_id if needed elsewhere
        # context['active_survey_id'] = self.active_survey.id if hasattr(self, 'active_survey') and self.active_survey else None
        return context

    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    @action(detail=False, methods=['get'])
    def available_filters(self, request):
        """
        Return available filters for submissions.
        Uses caching to prevent recreating filters on each request.
        """
        if self.__class__._cached_question_filters is None:
            questions = Question.objects.select_related('field_type').prefetch_related('options')
            self.__class__._cached_question_filters = questions

        serializer = QuestionFilterSerializer(self.__class__._cached_question_filters, many=True)

        return Response({
            'questions': serializer.data,
            'statuses': SubmissionStatusSerializer(SubmissionStatus.objects.all(), many=True).data,
            'sources': dict(SurveySubmission.Source.choices)
        })


class SubmissionStatusFilter(FilterSet):
    """Filter for submission statuses."""

    class Meta:
        model = SubmissionStatus
        fields = {
            'code': ['exact', 'in'],
            'is_default': ['exact'],
            'is_final': ['exact'],
            'active': ['exact']
        }


class SubmissionStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for submission statuses."""
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsStaffOrAdmin]
    serializer_class = SubmissionStatusSerializer
    queryset = SubmissionStatus.objects.all()
    filterset_class = SubmissionStatusFilter
    ordering_fields = ['order', 'name']
    ordering = ['order']
