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

    def get_children(self, obj) -> dict:
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

        # Для текстовых вопросов
        if question.input_type == Question.InputType.TEXT:
            if not text_answer:
                raise ValidationError('Text answer is required for text input')
            if selected_options:
                raise ValidationError('Selected options are not allowed for text input')
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

    def validate_responses(self, responses):
        """Validate that all questions are answered."""
        # Получаем все вопросы
        all_questions = set(Question.objects.values_list('id', flat=True))
        
        # Получаем ID вопросов из ответов
        answered_questions = {response['question'].id for response in responses}
        
        # Проверяем что все вопросы отвечены
        missing_questions = all_questions - answered_questions
        if missing_questions:
            questions = Question.objects.filter(id__in=missing_questions)
            titles = [q.title for q in questions]
            raise ValidationError(f'Не отвечены вопросы: {titles}')

        return responses

    def create(self, validated_data):
        """Create survey submission with responses."""
        responses_data = validated_data.pop('responses')
        
        # Создаем новую заявку
        submission = SurveySubmission.objects.create(**validated_data)
        
        # Список объектов Response для bulk create
        responses_to_create = []

        for response_data in responses_data:
            question = response_data['question']
            selected_options = response_data.pop('selected_options', [])
            
            # Создаем объект Response
            response = Response(
                submission=submission,
                question=question,
                text_answer=response_data.get('text_answer')
            )
            responses_to_create.append(response)
            
            # Если это вопрос с выбором и есть выбранные опции
            if question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE] and selected_options:
                # Сохраняем Response чтобы получить ID
                response.save()
                response.selected_options.set(selected_options)
        
        # Создаем остальные Response одним запросом
        Response.objects.bulk_create([r for r in responses_to_create if not r.id])

        return submission
