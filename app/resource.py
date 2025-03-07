# Define Resources for import/export
from import_export.resources import ModelResource

from app.models import SurveySubmission, Response, Question, AnswerOption, InputFieldType


class SurveySubmissionResource(ModelResource):
    """Resource for SurveySubmission model import/export."""

    class Meta:
        """Meta options for SurveySubmission resource."""
        model = SurveySubmission
        fields = 'id', 'status', 'created_at', 'updated_at'
        export_order = 'id', 'status', 'created_at', 'updated_at'


class ResponseResource(ModelResource):
    """Resource for Response model import/export."""

    class Meta:
        """Meta options for Response resource."""
        model = Response
        fields = 'id', 'submission__id', 'question__title', 'text_answer', 'created_at'
        export_order = 'id', 'submission__id', 'question__title', 'text_answer', 'created_at'


class QuestionResource(ModelResource):
    """Resource for Question model import/export."""

    class Meta:
        """Meta options for Question resource."""
        model = Question
        fields = 'id', 'title', 'placeholder', 'input_type', 'order', 'field_type__title', 'created_at'
        export_order = 'id', 'title', 'input_type', 'field_type__title', 'order', 'created_at'


class AnswerOptionResource(ModelResource):
    """Resource for AnswerOption model import/export."""

    class Meta:
        """Meta options for AnswerOption resource."""
        model = AnswerOption
        fields = 'id', 'question__title', 'text', 'order', 'parent__text', 'is_selectable', 'has_custom_input'
        export_order = 'id', 'question__title', 'text', 'order', 'parent__text', 'is_selectable', 'has_custom_input'


class InputFieldTypeResource(ModelResource):
    """Resource for InputFieldType model import/export."""

    class Meta:
        """Meta options for InputFieldType resource."""
        model = InputFieldType
        fields = 'id', 'title', 'regex_pattern', 'error_message', 'description'
        export_order = 'id', 'title', 'regex_pattern', 'error_message', 'description'
