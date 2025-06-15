from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django_filters import rest_framework as filters

from app.models import SurveySubmission, Question, Survey, SubmissionStatus, AnswerOption


def create_api_question_filters(question):
    """
    Generates a dictionary of filters for a given question, suitable for DRF.
    Each key is a parameter name, and each value is a filter instance.
    """
    drf_filters = {}

    # 1. Main filter for the question
    main_param_name = f'question_{question.pk}'
    drf_filters[main_param_name] = filters.CharFilter(method='filter_by_question_answer')

    # 2. Separate filters for option families (if applicable)
    if question.input_type in ["single_choice", "multiple_choice"]:
        root_options = question.options.filter(parent__isnull=True).order_by("order", "text")
        for root_option in root_options:
            if root_option.get_descendants().exists():
                family_param_name = f'question_option_{question.pk}_{root_option.pk}'
                drf_filters[family_param_name] = filters.CharFilter(method='filter_by_question_answer')

    return drf_filters


class SurveySubmissionAPIFilter(filters.FilterSet):
    """A dynamic FilterSet for SurveySubmissions that mimics the admin's behavior."""
    created_at = filters.DateFromToRangeFilter()
    # Static filters
    survey = filters.ModelChoiceFilter(queryset=Survey.objects.all())
    status = filters.ModelChoiceFilter(queryset=SubmissionStatus.objects.all(), to_field_name='code')
    source = filters.ChoiceFilter(choices=SurveySubmission.Source.choices)

    class Meta:
        model = SurveySubmission
        # Define only static fields here. Dynamic fields are added in __init__.
        fields = ['survey', 'status', 'source', 'created_at']

    def __init__(self, *args, **kwargs):
        request = kwargs.get('request')
        super().__init__(*args, **kwargs)

        if not request:
            return

        # Determine the survey to filter by
        survey_id = request.query_params.get('survey')
        survey = None
        if survey_id:
            survey = Survey.objects.filter(id=survey_id).first()
        else:
            survey = Survey.objects.filter(is_default=True, is_active=True).first()

        if not survey:
            return

        # Dynamically create filters for each question in the selected survey
        questions = Question.objects.filter(survey=survey).order_by('order')
        for question in questions:
            question_filters = create_api_question_filters(question)
            for param_name, filter_instance in question_filters.items():
                self.filters[param_name] = filter_instance

    def filter_by_question_answer(self, queryset, name, value):
        """
        A single method to handle filtering for all dynamic question filters.
        It parses the parameter name to get question/option IDs and applies the filter.
        The `value` is expected in the format `type:data`, e.g., `option:123` or `text:some_answer`.
        """
        if not value:
            return queryset

        # Parse the value
        try:
            filter_type, filter_value = value.split(':', 1)
        except ValueError:
            return queryset # Invalid format

        # Parse the parameter name `name`
        parts = name.split('_')
        question_id = None

        # e.g., 'question_123' or 'question_option_123_456'
        if len(parts) >= 2 and parts[0] == 'question':
            try:
                question_id = int(parts[1])
            except ValueError:
                return queryset

        if not question_id:
            return queryset

        # Apply filter based on type
        q_filter = Q()
        if filter_type == 'text':
            q_filter = Q(responses__question_id=question_id, responses__text_answer=filter_value)
        elif filter_type == 'option':
            try:
                option_id = int(filter_value)
                option = AnswerOption.objects.get(pk=option_id)
                desc_ids = list(option.get_descendants(include_self=True).values_list('id', flat=True))
                q_filter = Q(responses__question_id=question_id, responses__selected_options__id__in=desc_ids)
            except (ValueError, AnswerOption.DoesNotExist):
                return queryset

        return queryset.filter(q_filter).distinct()
