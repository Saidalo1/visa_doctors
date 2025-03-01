from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from app.models import Question, AnswerOption, SurveySubmission, Response


class AnswerOptionSerializer(ModelSerializer):
    """Serializer for AnswerOption model."""
    children = SerializerMethodField()

    class Meta:
        model = AnswerOption
        fields = 'id', 'text', 'is_selectable', 'has_custom_input', 'children'

    def get_children(self, obj):
        """Get children of answer option."""
        return AnswerOptionSerializer(obj.get_children(), many=True).data


class QuestionSerializer(ModelSerializer):
    """Serializer for Question model."""
    options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = 'id', 'title', 'input_type', 'options'


class ResponseSerializer(ModelSerializer):
    """Serializer for Response model."""
    selected_options = PrimaryKeyRelatedField(queryset=AnswerOption.objects.all(), many=True, required=False)

    class Meta:
        model = Response
        fields = 'question', 'selected_options', 'text_answer'

    def validate(self, data):
        """Validate response data based on question type and selected options."""
        question = data.get('question')
        selected_options = data.get('selected_options', [])
        text_answer = data.get('text_answer')

        if not question:
            raise ValidationError('Question is required')

        # Check if there is at least one selected option with has_custom_input=True
        has_custom_input_option = any(option.has_custom_input for option in selected_options)

        # If there is an option with has_custom_input=True, text_answer is required
        if has_custom_input_option and not text_answer:
            raise ValidationError('Text answer is required for the selected option')

        # If there is no option with has_custom_input=True, text_answer must not be filled in
        if not has_custom_input_option and text_answer:
            raise ValidationError('Text answer is not allowed for the selected options')

        return data

    def create(self, validated_data):
        """Create response with selected options and text answer."""
        selected_options = validated_data.pop('selected_options', [])
        response = Response.objects.create(**validated_data)
        response.selected_options.set(selected_options)
        return response


class SurveySubmissionSerializer(ModelSerializer):
    """Serializer for SurveySubmission model."""
    responses = ResponseSerializer(many=True)

    class Meta:
        model = SurveySubmission
        fields = 'id', 'responses'

    def create(self, validated_data):
        """Create survey submission with responses."""
        responses_data = validated_data.pop('responses')
        submission = SurveySubmission.objects.create(**validated_data)

        for response_data in responses_data:
            Response.objects.create(submission=submission, **response_data)

        return submission
