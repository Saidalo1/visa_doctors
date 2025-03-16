from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer, CharField
from django.utils.translation import gettext_lazy as _
import re

from app.models import Question, AnswerOption, SurveySubmission, Response, InputFieldType
from app.utils.telegram import notify_new_submission


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
    """Response serializer."""
    selected_options = PrimaryKeyRelatedField(
        many=True, queryset=AnswerOption.objects.filter(is_selectable=True), required=False
    )
    
    class Meta:
        """Meta class."""
        model = Response
        fields = ['question', 'selected_options', 'text_answer']
    
    def validate(self, attrs):
        """Validate response data."""
        question = attrs.get('question')
        selected_options = attrs.get('selected_options', [])
        text_answer = attrs.get('text_answer', '')
        
        # Проверяем, есть ли ответ в зависимости от типа вопроса
        if question.input_type == Question.InputType.TEXT and not text_answer:
            raise ValidationError({'text_answer': _('Text answer is required for this question.')})
        
        if question.input_type != Question.InputType.TEXT and not selected_options:
            raise ValidationError({'selected_options': _('At least one option must be selected for this question.')})
        
        # Для вопросов с вариантами ответов проверяем на существование custom input
        if selected_options:
            custom_input_required = any(opt.has_custom_input for opt in selected_options)
            if custom_input_required and not text_answer:
                raise ValidationError({
                    'text_answer': _('Text answer is required for the selected option.')
                })
                
            # Проверяем, что все опции принадлежат данному вопросу
            for option in selected_options:
                if option.question_id != question.id:
                    raise ValidationError({
                        'selected_options': _('Option "{0}" does not belong to question "{1}"').format(
                            option.text, question.title
                        )
                    })
        
        return attrs


class SurveySubmissionSerializer(ModelSerializer):
    """Survey submission serializer."""
    responses = ResponseSerializer(many=True)
    status = CharField(read_only=True)
    
    class Meta:
        """Metaclass."""
        model = SurveySubmission
        fields = 'id', 'status', 'responses', 'created_at', 'updated_at'
    
    def validate_responses(self, responses):
        """Validate that all required questions have responses."""
        # Получаем ID всех вопросов в ответах
        question_ids = [response['question'].id for response in responses]
        
        # Получаем список всех обязательных вопросов
        required_questions = Question.objects.filter(is_required=True)
        required_question_ids = set(required_questions.values_list('id', flat=True))
        
        # Проверяем, что все обязательные вопросы имеют ответы
        missing_question_ids = required_question_ids - set(question_ids)
        if missing_question_ids:
            missing_questions = [
                q.title for q in required_questions if q.id in missing_question_ids
            ]
            raise ValidationError(_('Missing responses for questions: {}').format(
                ', '.join(missing_questions)
            ))
        
        # Проверяем, что нет повторяющихся вопросов
        if len(question_ids) != len(set(question_ids)):
            raise ValidationError(_('Duplicate responses for some questions.'))
        
        return responses
    
    def create(self, validated_data):
        """Create survey submission with responses."""
        responses_data = validated_data.pop('responses')
        submission = SurveySubmission.objects.create(**validated_data)
        
        # Создаем ответы на вопросы
        for response_data in responses_data:
            selected_options = response_data.pop('selected_options', [])
            response = Response.objects.create(submission=submission, **response_data)
            
            # Добавляем выбранные варианты ответа, если есть
            if selected_options:
                response.selected_options.set(selected_options)

        notify_new_submission(submission_id=submission.id)

        # После сохранения всех ответов, меняем статус на COMPLETED
        # submission.status = SurveySubmission.Status.COMPLETED
        # submission.save(update_fields=['status'])
        
        return submission
