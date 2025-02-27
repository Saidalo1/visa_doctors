"""Views for survey app."""
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView, CreateAPIView

from app.models import Question, SurveySubmission
from app.serializers.survey import QuestionSerializer, SurveySubmissionSerializer
from shared.django import SURVEY


@extend_schema_view(
    get=extend_schema(
        summary="Get questions list",
        description="Returns list of questions with answer options in tree structure",
        tags=[SURVEY]
    )
)
class QuestionListAPIView(ListAPIView):
    """API view for Question model list."""
    queryset = Question.objects.prefetch_related('options', 'options__children')
    serializer_class = QuestionSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Submit survey answers",
        description="Submit answers for survey questions",
        tags=[SURVEY]
    )
)
class SurveySubmissionCreateAPIView(CreateAPIView):
    """API view for creating SurveySubmission."""
    serializer_class = SurveySubmissionSerializer
