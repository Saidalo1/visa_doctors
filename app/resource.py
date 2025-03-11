# app/resource.py

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from import_export import resources, fields
from import_export.resources import ModelResource
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

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
        
        This method is called by django-import-export on export. It receives the export form
        in the kwargs and should extract and apply filter parameters from it.
        
        Args:
            queryset: Base queryset to filter
            **kwargs: Contains 'export_form' with the form instance and may contain individual filter parameters
            
        Returns:
            Filtered queryset
        """
        # Print debug information about the received parameters
        print(f"SurveySubmissionResource.filter_export received kwargs: {kwargs}")
        
        # We can get the filter values from both sources:
        # 1. Directly from kwargs if admin.py added them there
        # 2. From the export_form.cleaned_data if present
        
        # Initialize form_data as an empty dict
        form_data = {}
        
        # Check if we have apply_filters directly in kwargs
        apply_filters = kwargs.get('apply_filters')
        if apply_filters is not None:
            form_data['apply_filters'] = apply_filters
        else:
            # Check if we have an export form
            export_form = kwargs.get('export_form')
            if export_form and hasattr(export_form, 'cleaned_data'):
                form_data = export_form.cleaned_data
                print(f"Form cleaned data from export_form: {form_data}")
            else:
                print("No valid export form found and no direct filter parameters")
                return queryset
        
        # Check if filters should be applied
        if not form_data.get('apply_filters', False):
            print("No filters requested")
            return queryset
        
        # Add any direct filter parameters from kwargs that aren't in form_data
        for key, value in kwargs.items():
            if key.startswith('filter_q_') and key not in form_data:
                form_data[key] = value
            
        # Process filter parameters for questions
        from app.models import Question, InputFieldType
        
        # Get all questions to check for filters
        questions = Question.objects.all()
        
        # Track if any filters were applied
        any_filter_applied = False
        
        # Apply filters for each question based on form data
        for question in questions:
            field_name = f"filter_q_{question.id}"
            
            # Handle numeric range filters
            if hasattr(question.field_type, 'field_type_choice') and question.field_type.field_type_choice == InputFieldType.FieldTypeChoice.NUMBER:
                value_from = form_data.get(f"{field_name}_from")
                value_to = form_data.get(f"{field_name}_to")
                
                if value_from is not None:
                    any_filter_applied = True
                    print(f"Applying number filter (from): {question.id} >= {value_from}")
                    
                    # Use a simpler approach that's more resilient to non-numeric data
                    # Get all submissions for this question
                    submissions_with_question = queryset.filter(responses__question_id=question.id)
                    
                    # Filter submissions with this question to only include those with valid numeric answers
                    filtered_submissions = []
                    
                    # Use raw SQL to filter by numeric values safely
                    from django.db import connection
                    
                    # Get all submission IDs that have numeric values >= value_from
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT DISTINCT app_surveysubmission.id 
                            FROM app_surveysubmission
                            INNER JOIN app_response ON app_response.submission_id = app_surveysubmission.id
                            WHERE app_response.question_id = %s
                              AND app_response.text_answer ~ '^-?[0-9]+(\\.[0-9]+)?$'
                              AND CAST(app_response.text_answer AS FLOAT) >= %s
                        """, [question.id, value_from])
                        valid_submission_ids = [row[0] for row in cursor.fetchall()]
                    
                    print(f"Found {len(valid_submission_ids)} submissions with age >= {value_from}")
                    
                    # Filter the queryset to only include these submissions
                    if valid_submission_ids:
                        queryset = queryset.filter(id__in=valid_submission_ids)
                    else:
                        # If no valid submissions found, return an empty queryset
                        queryset = queryset.filter(id__in=[])
                
                if value_to is not None:
                    any_filter_applied = True
                    print(f"Applying number filter (to): {question.id} <= {value_to}")
                    
                    # Use raw SQL to filter by numeric values safely
                    from django.db import connection
                    
                    # Get all submission IDs that have numeric values <= value_to
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT DISTINCT app_surveysubmission.id 
                            FROM app_surveysubmission
                            INNER JOIN app_response ON app_response.submission_id = app_surveysubmission.id
                            WHERE app_response.question_id = %s
                              AND app_response.text_answer ~ '^-?[0-9]+(\\.[0-9]+)?$'
                              AND CAST(app_response.text_answer AS FLOAT) <= %s
                        """, [question.id, value_to])
                        valid_submission_ids = [row[0] for row in cursor.fetchall()]
                    
                    print(f"Found {len(valid_submission_ids)} submissions with age <= {value_to}")
                    
                    # Filter the queryset to only include these submissions
                    if valid_submission_ids:
                        queryset = queryset.filter(id__in=valid_submission_ids)
                    else:
                        # If no valid submissions found, return an empty queryset
                        queryset = queryset.filter(id__in=[])
            
            # Handle choice questions (single or multiple choice)
            elif question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE]:
                selected_options = form_data.get(field_name, [])
                
                # Check if we have any group selections
                group_option_ids = [opt_id for opt_id in selected_options if opt_id and str(opt_id).startswith('group_')]
                valid_option_ids = [opt_id for opt_id in selected_options if opt_id and not str(opt_id).startswith('group_')]
                
                # print(f"Processing question {question.id} - selected options: {selected_options}")
                # print(f"- Group options: {group_option_ids}")
                # print(f"- Direct options: {valid_option_ids}")
                
                if group_option_ids:
                    # If we have group_ids, we need to find all option IDs that belong to these groups
                    from app.models import AnswerOption
                    for group_id in group_option_ids:
                        # Extract the numeric part after 'group_'
                        try:
                            parent_id = int(group_id.replace('group_', ''))
                            print(f"Finding options for group: {parent_id}")
                            
                            # Find all options that belong to this parent
                            child_options = AnswerOption.objects.filter(parent_id=parent_id).values_list('id', flat=True)
                            # print(f"SQL query for child options: {AnswerOption.objects.filter(parent_id=parent_id).query}")
                            
                            # Debug info about the group
                            parent_info = AnswerOption.objects.filter(id=parent_id).values('id', 'text', 'question_id').first()
                            # print(f"Parent option info: {parent_info}")
                            
                            if child_options:
                                valid_option_ids.extend([str(opt_id) for opt_id in child_options])
                                # print(f"Added child options: {list(child_options)}")
                                any_filter_applied = True
                            else:
                                # print(f"No child options found for parent ID: {parent_id}")
                                
                                # Try finding this record directly if it's a selectable option
                                direct_option = AnswerOption.objects.filter(id=parent_id, is_selectable=True).first()
                                if direct_option:
                                    valid_option_ids.append(str(parent_id))
                                    # print(f"Added parent as direct option: {parent_id}")
                                    any_filter_applied = True
                                
                        except (ValueError, TypeError) as e:
                            print(f"Could not parse group ID: {group_id} - Error: {str(e)}")
                
                if valid_option_ids:
                    any_filter_applied = True
                    option_ids = [int(opt_id) for opt_id in valid_option_ids]
                    print(f"Applying choice filter: {question.id} with options {option_ids}")
                    
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__selected_options__id__in=option_ids
                    ).distinct()
            
            # Handle text search for text questions
            else:
                search_text = form_data.get(field_name)
                
                if search_text:
                    any_filter_applied = True
                    print(f"Applying text filter: {question.id} contains '{search_text}'")
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__text_answer__icontains=search_text
                    )
        
        # Log whether filters were applied and result count
        filtered_count = queryset.count()
        print(f"Applied filters: {any_filter_applied}, filtered count: {filtered_count}")
        
        return queryset.distinct()

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
        # Print debug information about the field being processed
        field_name = field.attribute if hasattr(field, 'attribute') else str(field)
        print(f"Processing field: {field_name}")
        
        if hasattr(field, 'question_id'):
            try:
                question_id = field.question_id
                print(f"Found question_id: {question_id}")
                
                # Check if this submission has a response for this question
                try:
                    response = obj.responses.get(question_id=question_id)
                    print(f"Found response for question {question_id}")
                    
                    # Get question type and field type info
                    input_type = response.question.input_type
                    print(f"Question input_type: {input_type}")
                    
                    # Process text answers
                    if input_type == Question.InputType.TEXT:
                        print(f"Text answer: '{response.text_answer}'")
                        
                        # Handle numeric fields
                        if hasattr(field, 'field_type') and hasattr(field.field_type, 'field_type_choice') and \
                           field.field_type.field_type_choice == InputFieldType.FieldTypeChoice.NUMBER:
                            try:
                                if response.text_answer and response.text_answer.strip():
                                    return float(response.text_answer)
                            except (ValueError, TypeError):
                                pass
                        
                        return response.text_answer or ''
                    
                    # Process choice questions
                    selected_options = response.selected_options.all()
                    if selected_options:
                        option_texts = [opt.text for opt in selected_options]
                        print(f"Selected options: {option_texts}")
                        
                        custom_option = [opt for opt in selected_options if opt.has_custom_input]
                        
                        if custom_option and response.text_answer:
                            return f"{', '.join(option_texts)} - {response.text_answer}"
                        
                        return ', '.join(option_texts)
                    
                    # Fallback for empty options
                    return response.text_answer or ''
                except Response.DoesNotExist:
                    print(f"No response found for question {question_id}")
                    return ''
            except Exception as e:
                print(f"Error processing question field: {str(e)}")
                return ''
        
        # For non-question fields, use the standard ModelResource behavior
        return super().dehydrate_field(obj, field)


    

    
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
