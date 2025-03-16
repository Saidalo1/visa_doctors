# app/resource.py

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from import_export import resources, fields
from import_export.resources import ModelResource
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
import tablib

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

        # Get all questions sorted by order
        questions = Question.objects.select_related('field_type').order_by('order')

        for question in questions:
            field_name = f"question_{question.id}"
            
            # Use field_key as column name if available, otherwise use question title
            field_label = question.field_type.field_key if question.field_type and question.field_type.field_key else question.title
            
            # Create field with attribute=None because we'll use custom dehydrate methods
            self.fields[field_name] = fields.Field(
                column_name=field_label,
                attribute=None
            )
            
            # Store question ID as a field property for debugging
            self.fields[field_name].question_id = question.id
            
            # Create a custom dehydrate method specifically for this field
            # This is key to making the export work with dynamic fields
            method_name = f'dehydrate_{field_name}'
            setattr(self, method_name, 
                    lambda obj, qid=question.id: self._get_question_value(obj, qid))
            
            # Print debug information about field mapping
            # print(f"Added field {field_name} with label '{field_label}' for question ID {question.id}")

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

    def get_export_headers(self):
        """
        Get the export headers for each field.

        Returns:
            List of header names for export
        """
        headers = []
        for field_name in self.get_export_order():
            field = self.fields.get(field_name)
            if field is not None:
                # Use column_name if available, otherwise use field_name
                headers.append(field.column_name or field_name)
            else:
                headers.append(field_name)
        return headers

    def after_export(self, queryset, dataset, *args, **kwargs):
        """
        Clean up after export.

        Args:
            queryset: The exported queryset
            dataset: The resulting dataset
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The dataset
        """
        # Clear any caches to free memory
        self._cached_responses = {}
        return dataset

    # Оптимизируем экспорт, кэшируя данные ответов
    _cached_responses = {}

    def before_export(self, queryset, *args, **kwargs):
        """
        Override before_export to prefetch all responses and cache them for better performance
        """
        super().before_export(queryset, *args, **kwargs)

        # Сначала получаем все ID заявок для экспорта
        submission_ids = list(queryset.values_list('id', flat=True))[:200]  # Ограничиваем для безопасности

        # Загружаем все ответы за один запрос с нужными связями
        all_responses = Response.objects.filter(submission_id__in=submission_ids).select_related(
            'question', 'question__field_type'
        ).prefetch_related(
            'selected_options'
        )

        # Создаем кэш ответов в формате {submission_id: {question_id: response}}
        self._cached_responses = {}
        for response in all_responses:
            if response.submission_id not in self._cached_responses:
                self._cached_responses[response.submission_id] = {}

            self._cached_responses[response.submission_id][response.question_id] = response

    def _get_question_value(self, obj, question_id):
        """
        Helper method to get value for a specific question from a submission
        Uses cached responses for performance

        Args:
            obj: SurveySubmission instance
            question_id: ID of the question to get the value for

        Returns:
            Formatted value for the question
        """
        # Используем кэш ответов для быстрого доступа
        if obj.id not in self._cached_responses or question_id not in self._cached_responses[obj.id]:
            return ''

        response = self._cached_responses[obj.id][question_id]

        # Получаем метаданные о типе вопроса
        input_type = response.question.input_type
        field_type = None
        if response.question.field_type:
            field_type = response.question.field_type.field_type_choice

        # Обрабатываем текстовые ответы
        if input_type == Question.InputType.TEXT:
            # Для числовых полей пытаемся конвертировать в float
            if field_type == InputFieldType.FieldTypeChoice.NUMBER:
                try:
                    if response.text_answer and response.text_answer.strip():
                        return float(response.text_answer)
                except (ValueError, TypeError):
                    pass
            # Для обычных текстовых полей возвращаем как есть
            return response.text_answer or ''

        # Обрабатываем вопросы с выбором
        selected_options = list(response.selected_options.all())
        if selected_options:
            # Use `export_field_name` if it is not blank or not null, else use text
            option_texts = [opt.export_field_name if opt.export_field_name else opt.text for opt in selected_options]

            # Проверяем пользовательский ввод
            custom_option = [opt for opt in selected_options if opt.has_custom_input]
            if custom_option and response.text_answer:
                return f"{', '.join(option_texts)} - {response.text_answer}"

            return ', '.join(option_texts)

        # По умолчанию возвращаем текстовый ответ
        return response.text_answer or ''

    def export_resource_fields(self, obj, fields):
        """
        Extract data from an object for export for the given fields.
        This is an optimized version that uses our cached responses when possible.

        Args:
            obj: SurveySubmission instance to export
            fields: List of field names to export

        Returns:
            List of field values for the given object
        """
        row = []
        for field_name in fields:
            # For dynamic question fields, we use our custom dehydrate methods
            if field_name.startswith('question_'):
                method = getattr(self, f'dehydrate_{field_name}', None)
                if method:
                    # Use the custom method directly, which will use cached data
                    value = method(obj)
                else:
                    # Fallback if no method found (shouldn't happen)
                    value = ''
            else:
                # Для стандартных полей используем стандартные методы
                field = self.fields.get(field_name)
                if field:
                    value = self.dehydrate_field(obj, field)
                else:
                    value = ''
            row.append(value)
        return row

    def dehydrate_field(self, obj, field):
        """
        Extract the value for a field from the object.

        This method is only used for standard model fields, as dynamic question fields
        use custom dehydrate methods created in __init__.

        Args:
            obj: SurveySubmission instance
            field: Field to extract value from

        Returns:
            Formatted value for the field
        """
        # Получаем значение поля стандартным способом
        if hasattr(field, 'attribute') and field.attribute:
            value = field.get_value(obj)
        else:
            # Если нет атрибута, пробуем получить значение через dehydrate метод поля
            method_name = f'dehydrate_{field.column_name.lower()}'
            if hasattr(self, method_name):
                value = getattr(self, method_name)(obj)
            else:
                value = ''
        return value

    def export(self, queryset=None, *args, **kwargs):
        """
        Export data to Dataset.
        This is a high-performance implementation that uses response caching and optimized
        Excel formatting.

        Args:
            queryset: QuerySet to export
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Dataset with exported data
        """
        # Start timing the export process
        import time
        start_time = time.time()
        # print(f"Export started at {start_time}")

        # Setup cache and prepare for export
        self.before_export(queryset, *args, **kwargs)

        # Get queryset if not provided
        if queryset is None:
            queryset = self.get_queryset()

        # Apply filters if any
        if kwargs.get('export_form'):
            queryset = self.filter_export(queryset, **kwargs)
            # print(f"Applied filters, final count: {queryset.count()}")

        # Create a new dataset
        dataset = tablib.Dataset()

        # Get export headers
        headers = self.get_export_headers()
        dataset.headers = headers

        # Get export order
        export_order = self.get_export_order()

        # Process data in a single loop - much faster
        for obj in queryset:
            # This uses our optimized dehydrate_field method and cached responses
            # for question fields
            row = self.export_resource_fields(obj, export_order)
            dataset.append(row)

        # Apply Excel formatting only if we need XLSX
        file_format = kwargs.get('file_format', None)
        if file_format and hasattr(file_format, 'get_extension') and file_format.get_extension() == 'xlsx':
            try:
                # Convert data to Excel format
                import io
                xlsx_data = io.BytesIO()
                file_format.export_data(dataset, xlsx_data)
                xlsx_data.seek(0)

                # Load the generated file to apply formatting
                from openpyxl import load_workbook
                wb = load_workbook(xlsx_data)
                ws = wb.active

                # Apply styling only to header row for better performance
                for idx, cell in enumerate(ws[1], 1):
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.font = Font(bold=True)
                    column = get_column_letter(idx)
                    # Set width based on header text length
                    ws.column_dimensions[column].width = min(50, max(15, len(str(cell.value)) + 5))

                # Save the formatted workbook
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)

                # Replace the dataset with the formatted one
                formatted_dataset = tablib.Dataset()
                formatted_dataset.xlsx = output.getvalue()
                dataset = formatted_dataset
            except Exception as e:
                print(f"Error during Excel formatting: {str(e)}")
                # Continue with unformatted data if formatting fails

        # Report timing
        end_time = time.time()
        # print(f"Export completed in {end_time - start_time:.2f} seconds")

        # After-export cleanup
        self.after_export(queryset, dataset, *args, **kwargs)

        return dataset

    class Meta:
        model = SurveySubmission
        fields = ('id', 'status', 'created_at', 'updated_at')
        export_order = ('id', 'status', 'created_at', 'updated_at')
        use_export_filter = True  # Enable filter_export method for filtering


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
