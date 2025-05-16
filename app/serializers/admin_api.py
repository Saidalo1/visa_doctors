"""Serializers for admin mobile application API."""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from app.models import SurveySubmission, Response, Question, SubmissionStatus


class ResponseSerializer(serializers.ModelSerializer):
    """Serializer for Response model with expanded question data."""
    question_title = serializers.SerializerMethodField()
    question_key = serializers.SerializerMethodField()
    selected_options_text = serializers.SerializerMethodField()

    class Meta:
        model = Response
        fields = [
            'id', 'question', 'question_title', 'question_key',
            'text_answer', 'selected_options', 'selected_options_text'
        ]

    def get_question_title(self, obj):
        """Get question title."""
        return obj.question.title if obj.question else None

    def get_question_key(self, obj):
        """Get question field key for categorization."""
        if not obj.question or not obj.question.field_type:
            return None
        return obj.question.field_type.field_key

    def get_selected_options_text(self, obj):
        """Get text representation of selected options."""
        return [option.text for option in obj.selected_options.all()]


class SurveySubmissionListSerializer(serializers.ModelSerializer):
    """Serializer for SurveySubmission listing API."""
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    language_certificate = serializers.SerializerMethodField()
    field_of_study = serializers.SerializerMethodField()
    status_name = serializers.CharField(source='status.name')
    responses_count = serializers.SerializerMethodField()

    class Meta:
        model = SurveySubmission
        fields = [
            'id', 'full_name', 'phone_number', 'language_certificate',
            'field_of_study', 'status_name', 'source', 'comment',
            'created_at', 'responses_count'
        ]

    def get_responses_count(self, obj):
        """Get the number of responses in the submission."""
        return len(obj.responses.all())

    def get_phone_number(self, obj):
        """Get phone number from responses."""
        for response in obj.responses.all():
            if (hasattr(response.question, 'field_type') and 
                response.question.field_type and 
                response.question.field_type.field_key.lower() == "phone number"):
                return response.text_answer or '-'
        return '-'

    def get_full_name(self, obj):
        """Get name from responses."""
        for response in obj.responses.all():
            if (hasattr(response.question, 'field_type') and 
                response.question.field_type and 
                response.question.field_type.field_key.lower() == "name"):
                return response.text_answer or '-'
        return '-'

    def get_language_certificate(self, obj):
        """Get information about language certificate."""
        for response in obj.responses.all():
            if (hasattr(response.question, 'field_type') and 
                response.question.field_type and 
                response.question.field_type.field_key.lower() == "language certificate"):
                if response.text_answer:
                    return response.text_answer
                options = response.selected_options.all()
                if options:
                    return ', '.join(opt.text for opt in options)
                return '-'
        return '-'

    def get_field_of_study(self, obj):
        """Get information about field of study."""
        for response in obj.responses.all():
            if (hasattr(response.question, 'field_type') and 
                response.question.field_type and 
                response.question.field_type.field_key.lower() == "field of study"):
                if response.text_answer:
                    return response.text_answer
                options = response.selected_options.all()
                if options:
                    return ', '.join(opt.text for opt in options)
                return '-'
        return '-'


class SurveySubmissionDetailSerializer(SurveySubmissionListSerializer):
    """Serializer for SurveySubmission detail API."""
    responses = ResponseSerializer(many=True, read_only=True)
    status = serializers.PrimaryKeyRelatedField(queryset=SubmissionStatus.objects.all())

    class Meta:
        model = SurveySubmission
        fields = SurveySubmissionListSerializer.Meta.fields + ['responses', 'status', 'updated_at']


class SubmissionStatusSerializer(serializers.ModelSerializer):
    """Serializer for SubmissionStatus model."""
    
    class Meta:
        model = SubmissionStatus
        fields = ['id', 'code', 'name', 'description', 'color', 'is_default', 'is_final', 'active']


class QuestionFilterSerializer(serializers.ModelSerializer):
    """Serializer for representing question filters."""
    field_key = serializers.SerializerMethodField()
    filter_choices = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'title', 'field_key', 'filter_choices', 'input_type']
        
    def get_field_key(self, obj):
        """Get field key for the question if available."""
        if obj.field_type:
            return obj.field_type.field_key
        return None
        
    def get_filter_choices(self, obj):
        """Get filter choices based on question type."""
        if obj.input_type in ['single_choice', 'multiple_choice']:
            return [
                {'id': option.id, 'text': option.text}
                for option in obj.options.filter(is_selectable=True)
            ]
        return []
