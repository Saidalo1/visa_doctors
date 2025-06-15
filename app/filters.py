from django.db.models import Q
from django_filters import rest_framework as filters

from app.models import SurveySubmission, Question, Survey, SubmissionStatus, AnswerOption


class SurveySubmissionAPIFilter(filters.FilterSet):
    """A dynamic FilterSet for SurveySubmissions that mimics the admin's behavior."""
    created_at = filters.DateFromToRangeFilter()
    survey = filters.ModelChoiceFilter(queryset=Survey.objects.all())
    status = filters.ModelMultipleChoiceFilter(queryset=SubmissionStatus.objects.all())
    source = filters.MultipleChoiceFilter(choices=SurveySubmission.Source.choices)

    class Meta:
        model = SurveySubmission
        fields = ['survey', 'status', 'source', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get('request')
        if not request:
            return

        # Determine the survey to generate filters for
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
            # Main filter for the question
            filter_name = f'question_{question.pk}'
            self.filters[filter_name] = filters.CharFilter(
                field_name=filter_name, method='filter_by_question_answer'
            )
            self.filters[filter_name].parent = self

            # Add filters for option families if applicable
            if question.input_type in ["single_choice", "multiple_choice"]:
                for root_option in question.options.filter(parent__isnull=True):
                    if root_option.get_descendants().exists():
                        family_filter_name = f'question_option_{question.pk}_{root_option.pk}'
                        self.filters[family_filter_name] = filters.CharFilter(
                            field_name=family_filter_name, method='filter_by_question_answer'
                        )
                        self.filters[family_filter_name].parent = self

    def filter_by_question_answer(self, queryset, name, value):
        """
        A single method to handle filtering for all dynamic question filters.
        It parses the parameter name to get question/option IDs and applies the filter.
        The `value` is expected in the format `type:data`, e.g., `option:123` or `text:some_answer`.
        """
        # Ignore filter if value is empty or not in the expected 'type:value' format.
        if not value or ':' not in value:
            return queryset

        try:
            filter_type, filter_value = value.split(':', 1)
        except ValueError:
            return queryset

        # Ignore filter if the value part is empty (e.g., 'text:')
        if not filter_value:
            return queryset

        try:
            parts = name.split('_')
            question_id = int(parts[1])

            q_filter = Q()
            if filter_type == 'text':
                q_filter = Q(responses__question_id=question_id, responses__text_answer__icontains=filter_value)
            elif filter_type == 'option':
                option_id = int(filter_value)
                option = AnswerOption.objects.get(pk=option_id)
                desc_ids = list(option.get_descendants(include_self=True).values_list('id', flat=True))
                q_filter = Q(responses__question_id=question_id, responses__selected_options__id__in=desc_ids)

            if q_filter:
                return queryset.filter(q_filter).distinct()

        except (ValueError, IndexError, AnswerOption.DoesNotExist):
            # If any parsing or database error occurs, ignore this filter and continue.
            return queryset

        return queryset
