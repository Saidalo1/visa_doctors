"""Views for survey app."""
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
import django_filters 
from rest_framework.generics import ListAPIView, CreateAPIView

from app.models import Question, AnswerOption, Survey
from app.serializers.survey import QuestionSerializer, SurveySubmissionSerializer, SurveySerializer
from shared.django.filters import QuestionFilter
from shared.django import SURVEY, RecaptchaPermission


@extend_schema_view(
    get=extend_schema(
        summary="Get survey list",
        description="""
**Returns list of available surveys.**

**Fields description:**
- `id`: Survey ID
- `title`: Survey title
- `description`: Survey description
- `slug`: URL-friendly name for the survey (used in frontend URLs)
- `is_active`: Whether this survey is active
- `is_default`: Whether this survey is used when no specific survey is selected
""",
        tags=[SURVEY]
    )
)
class SurveyListAPIView(ListAPIView):
    """API view for Survey model list."""
    queryset = Survey.objects.filter(is_active=True)
    serializer_class = SurveySerializer


@extend_schema_view(
    get=extend_schema(
        summary="Get questions list",
        description="""
**Returns list of questions with answer options in tree structure.**

**Query Parameters:**
- `survey`: (Optional) Survey ID to get questions for a specific survey.
  If not provided, returns questions for the default survey.

**Fields description:**
- `input_type`: Type of question (`text`, `single_choice`, `multiple_choice`)
- `options`: Available options for choice questions (empty for text questions)
- `is_selectable`: Whether this option can be selected in response
- `has_custom_input`: Whether this option requires additional text input
- `children`: Nested options (if any)
""",
        tags=[SURVEY]
    )
)
class QuestionListAPIView(ListAPIView):
    """API view for Question model list."""
    serializer_class = QuestionSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = QuestionFilter
    
    def get_queryset(self):
        # Get survey_id from query parameters
        survey_id = self.request.query_params.get('survey_id')
        
        # Base queryset with prefetching
        queryset = Question.objects.prefetch_related(
            Prefetch('options', queryset=AnswerOption.objects.filter(level=0, parent__isnull=True)),
            'options__children'
        )
        
        # Filter by survey if provided
        if survey_id:
            try:
                # Filter questions by the specified survey
                return queryset.filter(survey_id=survey_id)
            except (ValueError, TypeError):
                # Invalid survey_id format, return empty queryset
                return Question.objects.none()
        else:
            # Try to get default survey
            try:
                default_survey = Survey.objects.get(is_default=True, is_active=True)
                return queryset.filter(survey=default_survey)
            except Survey.DoesNotExist:
                # If no default survey exists, return all questions
                return queryset


@extend_schema_view(
    post=extend_schema(
        summary="Submit survey answers",
        description="""
**Submit answers for all survey questions at once.**

**Request Parameters:**
- `survey_id`: (Optional) ID of the survey to submit answers for.
  If not provided, the default survey will be used.

**Rules for submitting answers:**
1. **For text questions:**
   - Provide only `text_answer`
   - Leave `selected_options` empty

2. **For single choice questions:**
   - Select exactly one option in `selected_options`
   - Provide `text_answer` only if option has `has_custom_input=true`

3. **For multiple choice questions:**
   - Select one or more options in `selected_options`
   - Provide `text_answer` only if any selected option has `has_custom_input=true`

**All required questions from the specified survey must be answered in a single request.**

**Possible errors:**
- Missing answers for some required questions
- Invalid answer type for question
- Multiple options selected for single choice
- Non-selectable options selected
- Missing text answer for custom input option
- Survey does not exist or is not active
""",
        tags=[SURVEY]
    )
)
class SurveySubmissionCreateAPIView(CreateAPIView):
    """API view for creating SurveySubmission."""
    serializer_class = SurveySubmissionSerializer
    permission_classes = [RecaptchaPermission]
