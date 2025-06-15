"""Serializers for admin mobile application API."""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
import types

from app.models import SurveySubmission, Response, Question, SubmissionStatus, Survey


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


from django.utils.text import Truncator
from django.utils.html import strip_tags


class SurveyBasicSerializer(serializers.ModelSerializer):
    """Basic serializer for Survey model, returning id and title."""

    class Meta:
        model = Survey
        fields = ['id', 'title']


class SurveySubmissionListSerializer(serializers.ModelSerializer):
    """A dynamic serializer that mimics the list_display of SurveySubmissionAdmin."""
    # Static fields that are always present
    status = serializers.StringRelatedField(read_only=True)
    # 'title' field will be added dynamically by get_fields if applicable
    source = serializers.CharField(source='get_source_display', read_only=True)
    responses_count = serializers.SerializerMethodField()

    class Meta:
        model = SurveySubmission
        # Define only the fields that are always part of the model.
        # Dynamic fields will be added in get_fields.
        fields = [
            'id',
            # 'survey' is removed as it's implicit from the endpoint context
            'status',
            'source',
            'comment',
            'created_at',
            'responses_count'
            # 'title' will be added dynamically by get_fields if applicable
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All field modification logic has been moved to get_fields() to prevent recursion.

    def get_fields(self):
        """
        Dynamically add and order fields to prevent recursion errors.
        The 'title' field is added here if a 'title_question' is in the context.
        """
        # Get the standard fields from Meta
        fields = super().get_fields()

        # Check if we need to add the 'title' field
        title_question = self.context.get('title_question')
        
        if title_question:
            # Add the dynamic 'title' field
            fields['title'] = serializers.SerializerMethodField()

            # Define the method that will provide the value for the 'title' field.
            def get_title_method(self, obj):
                # Logic to extract answer for the title_question
                for response in obj.responses.all():
                    if response.question_id == title_question.id:
                        answer_text = response.text_answer
                        if not answer_text:
                            options = response.selected_options.all()
                            if options:
                                answer_text = ', '.join(opt.text for opt in options)
                        if answer_text:
                            return Truncator(strip_tags(answer_text)).chars(70)
                        return '-'
                return '-'
            
            # Bind the method to the serializer instance. This is crucial for it to
            # receive 'self' (the serializer instance) as the first argument.
            setattr(self, 'get_title', types.MethodType(get_title_method, self))

        # Now, reorder the fields
        ordered_fields_keys = ['id']
        if title_question:
            ordered_fields_keys.append('title')
        
        base_meta_fields = [f for f in self.Meta.fields if f not in ['id', 'survey']]
        ordered_fields_keys.extend(base_meta_fields)

        # Construct the final ordered dictionary
        final_fields = {}
        for key in ordered_fields_keys:
            if key in fields:
                final_fields[key] = fields[key]
        
        # Add any other fields that were not in our ordered list to preserve them
        for key, value in fields.items():
            if key not in final_fields:
                final_fields[key] = value
                
        return final_fields

    def get_responses_count(self, obj):
        """Get the number of responses in the submission."""
        return obj.responses.count()


class SurveySubmissionDetailSerializer(serializers.ModelSerializer):
    """Serializer for SurveySubmission detail API."""
    survey = SurveyBasicSerializer(read_only=True)
    status = serializers.StringRelatedField(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=SubmissionStatus.objects.all(),
        source='status',
        write_only=True,
        label=_('Status ID')
    )
    source = serializers.CharField(source='get_source_display', read_only=True)
    responses_count = serializers.SerializerMethodField()
    responses = ResponseSerializer(many=True, read_only=True)

    class Meta:
        model = SurveySubmission
        fields = [
            'id',
            'survey',
            'status',  # This will be the read_only StringRelatedField
            'status_id',  # This is for writing
            'source',
            'comment',
            'created_at',
            'updated_at',
            'responses_count',
            'responses'
        ]

    def get_responses_count(self, obj):
        """Get the number of responses in the submission."""
        return obj.responses.count()


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
