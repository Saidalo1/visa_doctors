from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import ModelSerializer

from app.models import Question, AnswerOption, SurveySubmission, Response


class AnswerOptionSerializer(ModelSerializer):
    """Serializer for AnswerOption model."""

    class Meta:
        model = AnswerOption
        fields = 'id', 'text'


class AnswerOptionWithChildrenSerializer(AnswerOptionSerializer):

    @extend_schema_field(AnswerOptionSerializer(many=True))
    def get_children(self, obj):
        """Get children of answer option."""
        return AnswerOptionSerializer(obj.get_children(), many=True).data


class QuestionSerializer(ModelSerializer):
    """Serializer for Question model."""
    options = AnswerOptionWithChildrenSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = 'id', 'title', 'input_type', 'options'


class ResponseSerializer(ModelSerializer):
    """Serializer for Response model."""

    class Meta:
        model = Response
        fields = 'question', 'answer'


class SurveySubmissionSerializer(ModelSerializer):
    """Serializer for SurveySubmission model."""
    responses = ResponseSerializer(many=True)

    class Meta:
        model = SurveySubmission
        fields = 'id', 'status', 'responses'

    def create(self, validated_data):
        """Create survey submission with responses."""
        responses_data = validated_data.pop('responses')
        submission = SurveySubmission.objects.create(**validated_data)

        for response_data in responses_data:
            Response.objects.create(submission=submission, **response_data)

        return submission
