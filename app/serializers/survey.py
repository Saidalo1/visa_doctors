from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer, CharField
from django.utils.translation import gettext_lazy as _
import re

from app.models import Question, AnswerOption, SurveySubmission, Response, InputFieldType, Survey
from app.utils.telegram import notify_new_submission_async


class InputFieldTypeSerializer(ModelSerializer):
    """Serializer for InputFieldType model."""
    
    class Meta:
        model = InputFieldType
        fields = 'id', 'title', 'field_key', 'regex_pattern', 'error_message'


class AnswerOptionSerializer(ModelSerializer):
    """Serializer for AnswerOption model."""
    children = SerializerMethodField()

    class Meta:
        model = AnswerOption
        fields = 'id', 'text', 'is_selectable', 'has_custom_input', 'children'

    def get_children(self, obj) -> dict:
        """Get children of answer option."""
        return AnswerOptionSerializer(obj.get_children(), many=True).data


class SurveySerializer(ModelSerializer):
    """Serializer for Survey model."""
    
    class Meta:
        model = Survey
        fields = 'id', 'title', 'description', 'slug', 'is_active', 'is_default'


class QuestionSerializer(ModelSerializer):
    """Serializer for Question model."""
    options = AnswerOptionSerializer(many=True, read_only=True)
    field_type = InputFieldTypeSerializer(read_only=True)
    # survey = SurveySerializer(read_only=True)

    class Meta:
        model = Question
        fields = 'id', 'title', 'input_type', 'options', 'field_type', 'is_required', 'placeholder'


class ResponseSerializer(ModelSerializer):
    """Response serializer."""
    selected_options = PrimaryKeyRelatedField(
        many=True, queryset=AnswerOption.objects.filter(is_selectable=True), required=False
    )
    
    class Meta:
        """Metaclass."""
        model = Response
        fields = ['question', 'selected_options', 'text_answer']
    
    def validate(self, attrs):
        """Validate response data."""
        question = attrs.get('question')
        selected_options = attrs.get('selected_options', [])
        text_answer = attrs.get('text_answer', '')
        
        # Check if there is an answer depending on the question type
        if question.input_type == Question.InputType.TEXT and question.is_required and not text_answer:
            raise ValidationError({'text_answer': _('Text answer is required for this question.')})
        
        if question.input_type != Question.InputType.TEXT and not selected_options:
            raise ValidationError({'selected_options': _('At least one option must be selected for this question.')})
        
        # For questions with answer options, check if custom input exists
        if selected_options:
            custom_input_required = any(opt.has_custom_input for opt in selected_options)
            if custom_input_required and not text_answer:
                raise ValidationError({
                    'text_answer': _('Text answer is required for the selected option.')
                })
                
            # Check that all options belong to this question
            for option in selected_options:
                if option.question_id != question.id:
                    raise ValidationError({
                        'selected_options': _('Option "{0}" does not belong to question "{1}"').format(
                            option.text, question.title
                        )
                    })

        # Check regex validation if the question has a field_type with a regular expression
        if (
                question.input_type == Question.InputType.TEXT
                and question.field_type
                and question.field_type.regex_pattern.strip()  # Check that regex is not empty
        ):
            pattern = question.field_type.regex_pattern
            if not re.fullmatch(pattern, text_answer):
                error_message = question.field_type.error_message or _(
                    'Text answer does not match the required format.')
                raise ValidationError({'text_answer': error_message})

        return attrs


class SurveySubmissionSerializer(ModelSerializer):
    """Survey submission serializer."""
    responses = ResponseSerializer(many=True)
    status = CharField(read_only=True)
    survey_id = PrimaryKeyRelatedField(queryset=Survey.objects.filter(is_active=True), required=False, write_only=True)
    
    class Meta:
        """Metaclass."""
        model = SurveySubmission
        fields = 'id', 'status', 'source', 'responses', 'created_at', 'updated_at', 'survey_id'
    
    def validate_responses(self, responses):
        """Validate that all required questions have responses."""
        # Get IDs of all questions in the responses
        question_ids = [response['question'].id for response in responses]

        # Get survey ID from context or use default survey
        survey_id = self.initial_data.get('survey_id')
        if not survey_id:
            # If survey_id is not provided, use the default survey
            try:
                default_survey = Survey.objects.get(is_default=True, is_active=True)
                survey_id = default_survey.id
            except Survey.DoesNotExist:
                # No default survey found - consider all questions
                survey_filter = {}
        else:
            # Check if the survey exists and is active
            try:
                Survey.objects.get(id=survey_id, is_active=True)
                survey_filter = {'survey_id': survey_id}
            except Survey.DoesNotExist:
                raise ValidationError(_('The specified survey does not exist or is not active.'))
            except ValueError:
                raise ValidationError({'survey_id': _('Survey ID is invalid.')})

        # Check if survey id is available
        try:
            survey_id = int(survey_id)
        except ValueError:
            raise ValidationError({'survey_id': _('Survey ID is invalid.')})

        # Check all questions belongs to current survey or not
        survey_ids = Question.objects.filter(id__in=question_ids).values_list('survey_id', flat=True).distinct()
        if survey_ids.count() != 1 or survey_ids[0] != survey_id:
            raise ValidationError(_('Not all questions belong to the current survey.'))


        # Get a list of all required questions for this survey
        if 'survey_filter' in locals():
            required_questions = Question.objects.filter(is_required=True, **survey_filter)
        else:
            required_questions = Question.objects.filter(is_required=True)
            
        required_question_ids = set(required_questions.values_list('id', flat=True))
        
        # Check that all required questions have answers
        missing_question_ids = required_question_ids - set(question_ids)
        if missing_question_ids:
            missing_questions = [
                q.title for q in required_questions if q.id in missing_question_ids
            ]
            raise ValidationError(_('Missing responses for questions: {}').format(
                ', '.join(missing_questions)
            ))
        
        # Check that there are no duplicate questions
        if len(question_ids) != len(set(question_ids)):
            raise ValidationError(_('Duplicate responses for some questions.'))
        
        return responses
    
    def create(self, validated_data):
        """Create survey submission with responses."""
        from app.models.status import SubmissionStatus
        
        # Get response data from validated_data
        responses_data = validated_data.pop('responses')
        
        # Handle survey_id if provided
        survey_id = validated_data.pop('survey_id', None)
        if survey_id:
            # If survey_id is provided, set it directly
            validated_data['survey'] = survey_id
        else:
            # If no survey_id is provided, use the default survey
            try:
                default_survey = Survey.objects.get(is_default=True, is_active=True)
                validated_data['survey'] = default_survey
            except Survey.DoesNotExist:
                # Leave survey as null if no default found
                pass
        
        # Check if status is specified, if not - use default status
        if 'status' not in validated_data:
            try:
                # Try to find the default status
                default_status = SubmissionStatus.objects.get(is_default=True)
                validated_data['status'] = default_status
            except SubmissionStatus.DoesNotExist:
                # If default status is not found, look for status with code 'new'
                try:
                    default_status = SubmissionStatus.objects.get(code='new')
                    validated_data['status'] = default_status
                except SubmissionStatus.DoesNotExist:
                    # If none of the statuses is found, take the first status
                    default_status = SubmissionStatus.objects.first()
                    if default_status is None:
                        raise ValidationError(_("Не найден ни один статус для заявки"))
                    validated_data['status'] = default_status
        
        # Create submission record
        submission = SurveySubmission.objects.create(**validated_data)
        
        # Create responses
        for response_data in responses_data:
            selected_options = response_data.pop('selected_options', [])
            response = Response.objects.create(submission=submission, **response_data)
            
            # Add selected options if any
            if selected_options:
                response.selected_options.set(selected_options)

        notify_new_submission_async(submission_id=submission.id)
        
        return submission
