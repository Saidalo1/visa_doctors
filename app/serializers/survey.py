from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
from re import match

from app.models import Question, AnswerOption, SurveySubmission, Response, InputFieldType


class InputFieldTypeSerializer(ModelSerializer):
    """Serializer for InputFieldType model."""
    
    class Meta:
        model = InputFieldType
        fields = 'id', 'title', 'regex_pattern', 'error_message'


class AnswerOptionSerializer(ModelSerializer):
    """Serializer for AnswerOption model."""
    children = SerializerMethodField()

    class Meta:
        model = AnswerOption
        fields = 'id', 'text', 'is_selectable', 'has_custom_input', 'children'

    def get_children(self, obj) -> dict:
        """Get children of answer option."""
        return AnswerOptionSerializer(obj.get_children(), many=True).data


class QuestionSerializer(ModelSerializer):
    """Serializer for Question model."""
    options = AnswerOptionSerializer(many=True, read_only=True)
    field_type = InputFieldTypeSerializer(read_only=True)

    class Meta:
        model = Question
        fields = 'id', 'title', 'input_type', 'options', 'field_type'


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

        # Для текстовых вопросов
        if question.input_type == Question.InputType.TEXT:
            if not text_answer:
                raise ValidationError('Text answer is required for text input')
            if selected_options:
                raise ValidationError('Selected options are not allowed for text input')
            
            # Валидация по regex, если у вопроса указан тип поля
            if question.field_type and text_answer:
                pattern = question.field_type.regex_pattern
                error_msg = question.field_type.error_message
                
                if not match(pattern, text_answer):
                    raise ValidationError(error_msg or f'Text answer does not match pattern {pattern}')
                    
            return data

        # Для вопросов с выбором
        if question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE]:
            if not selected_options:
                raise ValidationError('At least one option must be selected')

            # Проверяем принадлежность опций к вопросу
            question_options = set(question.options.values_list('id', flat=True))
            selected_ids = {opt.id for opt in selected_options}
            invalid_options = selected_ids - question_options
            if invalid_options:
                raise ValidationError(f'Options {invalid_options} do not belong to question {question.id}')

            # Для single choice только один вариант
            if question.input_type == Question.InputType.SINGLE_CHOICE and len(selected_options) > 1:
                raise ValidationError('Only one option can be selected for single choice')

            # Проверяем есть ли опция с custom input
            has_custom_input = any(opt.has_custom_input for opt in selected_options)
            if has_custom_input and not text_answer:
                raise ValidationError('Text answer is required for option with custom input')
            if not has_custom_input and text_answer:
                raise ValidationError('Text answer is not allowed without custom input option')

            # Дополнительная валидация текстового ответа по regex при наличии custom input
            if has_custom_input and text_answer and question.field_type:
                pattern = question.field_type.regex_pattern
                error_msg = question.field_type.error_message
                
                if not match(pattern, text_answer):
                    raise ValidationError(error_msg or f'Text answer does not match pattern {pattern}')

        return data


class SurveySubmissionSerializer(ModelSerializer):
    """Serializer for SurveySubmission model."""
    responses = ResponseSerializer(many=True)

    class Meta:
        model = SurveySubmission
        fields = 'id', 'responses'

    @staticmethod
    def validate_responses(responses):
        """Validate that all questions are answered."""
        if not responses:
            raise ValidationError('At least one response is required')

        # Check for duplicate questions
        question_ids = [resp['question'].id for resp in responses]
        if len(question_ids) != len(set(question_ids)):
            raise ValidationError('Duplicate questions found in responses')

        # Ensure all questions are answered
        all_questions = set(Question.objects.values_list('id', flat=True))
        answered_questions = set(question_ids)
        missing_questions = all_questions - answered_questions

        if missing_questions:
            raise ValidationError(f'Missing responses for questions: {missing_questions}')

        return responses

    def create(self, validated_data):
        """Create survey submission with responses."""
        responses_data = validated_data.pop('responses', [])
        submission = SurveySubmission.objects.create(**validated_data)

        for response_data in responses_data:
            selected_options = response_data.pop('selected_options', [])
            response = Response.objects.create(submission=submission, **response_data)
            if selected_options:
                response.selected_options.add(*selected_options)

        return submission
