# app/resource.py

from import_export import resources, fields
from django.db.models import Prefetch
from import_export.resources import ModelResource

from app.models import SurveySubmission, Question, Response, AnswerOption, InputFieldType


class SurveySubmissionResource(resources.ModelResource):
    """
    Resource for SurveySubmission model import/export.
    """

    def __init__(self, question_id=None, text_search=None, **kwargs):
        # super() обязательно передавать **kwargs
        super().__init__(**kwargs)
        self.question_id = question_id
        self.text_search = text_search

        # Пример твоей логики с динамическими полями:
        questions = Question.objects.all().order_by('order')
        for question in questions:
            field_name = f"question_{question.id}"
            field_label = f"{question.title}"
            self.fields[field_name] = fields.Field(
                column_name=field_label,
                attribute=None,
            )
            self.fields[field_name].question_id = question.id

    def filter_export(self, queryset, **kwargs):
        """
        Метод, который django-import-export сам вызовет,
        если мы укажем его в Meta -> use `filter_export`.
        Или мы можем вызывать его вручную в get_queryset().
        """
        if self.question_id:
            queryset = queryset.filter(responses__question_id=self.question_id)
        if self.text_search:
            queryset = queryset.filter(responses__text_answer__icontains=self.text_search)
        return queryset

    def get_queryset(self):
        """
        Optimize queryset for export + применяем filter_export.
        """
        qs = SurveySubmission.objects.prefetch_related(
            Prefetch(
                'responses',
                queryset=Response.objects.select_related('question')
                                        .prefetch_related('selected_options')
            )
        )
        # Фильтруем
        qs = self.filter_export(qs)
        return qs

    def dehydrate_field(self, obj, field):
        """
        Твой метод для вывода значений вопрос/ответ.
        """
        if hasattr(field, 'question_id'):
            try:
                response = obj.responses.get(question_id=field.question_id)
                if response.question.input_type == Question.InputType.TEXT:
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
