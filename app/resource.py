# app/resource.py

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from import_export import resources, fields
from import_export.resources import ModelResource

from app.models import SurveySubmission, Question, Response, AnswerOption, InputFieldType


class SurveySubmissionResource(resources.ModelResource):
    """
    Resource for SurveySubmission model import/export.
    
    This resource dynamically creates fields for each question in the survey,
    allowing for customized export of survey submissions with all responses.
    """
    id = fields.Field(column_name=_('ID'), attribute='id')
    status = fields.Field(column_name=_('Status'), attribute='status')
    created_at = fields.Field(column_name=_('Created At'), attribute='created_at')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        questions = Question.objects.order_by('order')

        for question in questions:
            field_name = f"question_{question.id}"
            field_label = question.field_type.field_key or question.title

            self.fields[field_name] = fields.Field(
                column_name=field_label,
                attribute=None,
            )
            self.fields[field_name].question_id = question.id
            self.fields[field_name].question_type = question.input_type
            self.fields[field_name].field_type = question.field_type

    def filter_export(self, queryset, **kwargs):
        """
        Filter the export queryset based on the provided parameters.
        
        This method is called by django-import-export if specified in Meta.use_export_filter,
        or can be called manually in get_queryset().
        
        Args:
            queryset: Base queryset to filter
            **kwargs: Additional filter parameters
            
        Returns:
            Filtered queryset
        """

        return queryset

    def get_queryset(self):
        """
        Optimize queryset for export with prefetching related data.
        
        Returns:
            Optimized queryset for export
        """
        return SurveySubmission.objects.prefetch_related(
            Prefetch(
                'responses',
                queryset=Response.objects.select_related('question')
                .prefetch_related('selected_options')
            )
        )

    def get_export_order(self):
        """
        Define the order of fields in the export.
        
        Returns:
            List of field names in the desired order
        """

        fields_order = ['id', 'status', 'created_at']

        questions = Question.objects.order_by('order')
        for question in questions:
            fields_order.append(f"question_{question.id}")

        return fields_order

    def dehydrate_field(self, obj, field):
        """
        Extract the value for a field from the object.
        
        This method handles dynamic question fields and formats the response
        based on the question type (text, single choice, multiple choice).
        
        Args:
            obj: SurveySubmission instance
            field: Field to extract value from
            
        Returns:
            Formatted value for the field
        """

        if hasattr(field, 'question_id'):
            try:

                response = obj.responses.get(question_id=field.question_id)

                if response.question.input_type == Question.InputType.TEXT:

                    if hasattr(field,
                               'field_type_choice') and field.field_type_choice == InputFieldType.FieldTypeChoice.NUMBER:

                        try:
                            if response.text_answer and response.text_answer.strip():
                                return float(response.text_answer)
                        except (ValueError, TypeError):

                            pass

                    return response.text_answer or ''

                selected_options = response.selected_options.all()
                if selected_options:

                    custom_option = [opt for opt in selected_options if opt.has_custom_input]

                    if custom_option and response.text_answer:
                        options_text = [opt.text for opt in selected_options]
                        return f"{', '.join(options_text)} - {response.text_answer}"

                    return ', '.join([opt.text for opt in selected_options])

                return response.text_answer or ''
            except Response.DoesNotExist:

                return ''

        return super().dehydrate_field(obj, field)

    class Meta:
        model = SurveySubmission
        fields = ('id', 'status', 'created_at', 'updated_at')
        export_order = ('id', 'status', 'created_at', 'updated_at')


class ResponseResource(ModelResource):
    """Resource for Response model import/export."""

    class Meta:
        """Meta options for Response resource."""
        model = Response
        fields = 'id', 'submission__id', 'question__title', 'text_answer', 'created_at'
        export_order = 'id', 'submission__id', 'question__title', 'text_answer', 'created_at'


class QuestionResource(ModelResource):
    """Resource for Question model import/export."""

    field_type_choice_display = fields.Field(
        column_name=_('Field Type Choice Display'),
        attribute='get_field_type_choice_display'
    )
    input_type_display = fields.Field(
        column_name=_('Input Type Display'),
        attribute='get_input_type_display'
    )

    class Meta:
        """Meta options for Question resource."""
        model = Question
        fields = (
            'id', 'title', 'field_title', 'placeholder', 'is_required',
            'input_type', 'input_type_display', 'field_type_choice', 'field_type_choice_display',
            'order', 'field_type__title', 'created_at'
        )
        export_order = (
            'id', 'title', 'field_title', 'input_type', 'input_type_display',
            'field_type_choice', 'field_type_choice_display', 'field_type__title',
            'is_required', 'order', 'created_at'
        )


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
