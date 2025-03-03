"""Views for survey app."""
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView, CreateAPIView

from app.models import Question, AnswerOption
from app.serializers.survey import QuestionSerializer, SurveySubmissionSerializer
from shared.django import SURVEY, RecaptchaPermission


@extend_schema_view(
    get=extend_schema(
        summary="Get questions list",
        description="""
**Returns list of questions with answer options in tree structure.**

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
    queryset = Question.objects.prefetch_related(
        Prefetch('options', queryset=AnswerOption.objects.filter(level=0, parent__isnull=True)),
        'options__children'
    )
    serializer_class = QuestionSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Submit survey answers",
        description="""
**Submit answers for all survey questions at once.**

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

**All questions must be answered in a single request.**

**Possible errors:**
- Missing answers for some questions
- Invalid answer type for question
- Multiple options selected for single choice
- Non-selectable options selected
- Missing text answer for custom input option
""",
        tags=[SURVEY]
    )
)
class SurveySubmissionCreateAPIView(CreateAPIView):
    """API view for creating SurveySubmission."""
    serializer_class = SurveySubmissionSerializer
    # permission_classes = [RecaptchaPermission]
