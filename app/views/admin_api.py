import django_filters
from django.db.models import Prefetch, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from app.models import SurveySubmission, Question, SubmissionStatus, Response as SurveyResponse
from app.serializers.admin_api import (
    SurveySubmissionListSerializer, SurveySubmissionDetailSerializer,
    SubmissionStatusSerializer, QuestionFilterSerializer
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


class SubmissionStatusFilter(django_filters.FilterSet):
    """Filter for submission statuses."""

    class Meta:
        model = SubmissionStatus
        fields = {
            'code': ['exact', 'in'],
            'is_default': ['exact'],
            'is_final': ['exact'],
            'active': ['exact']
        }


class SurveySubmissionFilter(django_filters.FilterSet):
    """Filter set for survey submissions."""
    status__code = django_filters.CharFilter(field_name='status__code')
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(method='search_filter')

    class Meta:
        model = SurveySubmission
        fields = ['survey', 'status__code', 'source', 'created_at']

    def search_filter(self, queryset, name, value):
        """Filter submissions by search term in responses or comments."""
        if not value:
            return queryset
        return queryset.filter(
            Q(responses__text_answer__icontains=value) |
            Q(comment__icontains=value)
        ).distinct()


class SurveySubmissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for survey submissions.
    
    list:
    Return a list of all survey submissions.
    
    retrieve:
    Return the given survey submission.
    
    create:
    Create a new survey submission.
    
    update:
    Update survey submission.
    
    partial_update:
    Partial update survey submission.
    
    destroy:
    Delete a survey submission.
    """
    #authentication_classes = [JWTAuthentication]
    #permission_classes = [IsStaffOrAdmin]
    filterset_class = SurveySubmissionFilter
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        OrderingFilter,
        SearchFilter,
    ]
    ordering_fields = ['created_at', 'updated_at', 'id']
    ordering = ['-created_at']
    search_fields = ['responses__text_answer', 'comment']
    pagination_class = CustomPagination

    # Cache for question filters - will be created once at server startup
    _cached_question_filters = None

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return SurveySubmissionListSerializer
        return SurveySubmissionDetailSerializer

    def get_queryset(self):
        """
        Optimize the queryset by prefetching related responses.
        """
        queryset = SurveySubmission.objects.select_related('status').prefetch_related(
            Prefetch('responses',
                     queryset=SurveyResponse.objects.select_related('question', 'question__field_type')
                     .prefetch_related('selected_options')
                     )
        )

        # Apply additional dynamic filters based on question fields
        for param, value in self.request.query_params.items():
            if param.startswith('question_'):
                try:
                    # Extract question ID from parameter name
                    question_id = int(param.split('_')[1])

                    # Add filter for this question
                    queryset = queryset.filter(
                        responses__question_id=question_id,
                        responses__text_answer__icontains=value
                    ).distinct()
                except (ValueError, IndexError):
                    # Invalid parameter format, ignore it
                    pass

            # Handle option filters (for choice questions)
            elif param.startswith('option_'):
                try:
                    # Extract option ID from parameter name
                    option_id = int(param.split('_')[1])

                    # Add filter for this option
                    queryset = queryset.filter(
                        responses__selected_options__id=option_id
                    ).distinct()
                except (ValueError, IndexError):
                    # Invalid parameter format, ignore it
                    pass

        return queryset

    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    @action(detail=False, methods=['get'])
    def available_filters(self, request):
        """
        Return available filters for submissions.
        Uses caching to prevent recreating filters on each request.
        """
        # Use cached filters if they already exist
        if self.__class__._cached_question_filters is None:
            # Cache is empty - fetch questions
            questions = Question.objects.select_related('field_type').prefetch_related(
                'options'
            )
            self.__class__._cached_question_filters = questions

        # Serialize the filters
        serializer = QuestionFilterSerializer(
            self.__class__._cached_question_filters,
            many=True
        )

        return Response({
            'questions': serializer.data,
            'statuses': SubmissionStatusSerializer(
                SubmissionStatus.objects.all(), many=True
            ).data,
            'sources': dict(SurveySubmission.Source.choices)
        })


class SubmissionStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for submission statuses."""
    #authentication_classes = [JWTAuthentication]
    #permission_classes = [IsStaffOrAdmin]
    serializer_class = SubmissionStatusSerializer
    queryset = SubmissionStatus.objects.all()
    filterset_class = SubmissionStatusFilter
    ordering_fields = ['order', 'name']
    ordering = ['order']
