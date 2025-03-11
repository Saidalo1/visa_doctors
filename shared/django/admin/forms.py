from django import forms
from django.forms import CharField, FloatField, MultipleChoiceField
from django.utils.translation import gettext_lazy as _
from import_export.forms import ExportForm

from app.models import Question, InputFieldType, AnswerOption


class SurveyExportForm(ExportForm):
    """
    Enhanced export form with dynamic filters for each question.
    
    This form dynamically generates filter fields based on the questions in the survey.
    For text/string questions, it provides text search fields.
    For numeric questions, it provides range filters (from/to).
    For choice questions, it provides multiple choice selection.
    """
    
    # Hidden field to indicate that filters were applied
    apply_filters = forms.BooleanField(initial=True, widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get all questions sorted by order
        questions = Question.objects.order_by('order')

        for question in questions:
            field_name = f"filter_q_{question.id}"
            # Use field_title if available, otherwise use title
            field_label = question.field_type.field_key or question.field_type.title

            # Create different field types based on question type
            if hasattr(question.field_type, 'field_type_choice') and question.field_type.field_type_choice == InputFieldType.FieldTypeChoice.NUMBER:
                # Create range fields (from-to) for number type questions
                self.fields[f"{field_name}_from"] = FloatField(
                    required=False,
                    label=f"{field_label} (from)",
                    widget=forms.NumberInput(attrs={'step': 'any'})
                )
                self.fields[f"{field_name}_to"] = FloatField(
                    required=False,
                    label=f"{field_label} (to)",
                    widget=forms.NumberInput(attrs={'step': 'any'})
                )
            elif question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE]:
                # Get parent options (top level) only for hierarchical display
                parent_options = question.options.filter(parent__isnull=True).order_by('order')
                
                # Create a hierarchical choice structure
                choices = []
                for parent in parent_options:
                    # Add parent as a group header (not selectable)
                    choices.append((f"group_{parent.id}", f"{parent.text}"))
                    
                    # Add children with indentation
                    children = AnswerOption.objects.filter(parent=parent).order_by('order')
                    for child in children:
                        choices.append((child.id, f"-- {child.text}"))
                
                if choices:
                    self.fields[field_name] = MultipleChoiceField(
                        required=False,
                        label=field_label,
                        choices=choices,
                        widget=forms.CheckboxSelectMultiple
                    )
            else:
                # Create text search field for text questions
                self.fields[field_name] = CharField(
                    required=False,
                    label=field_label
                )

    def get_filter_queryset(self, queryset):
        """
        Apply filters from the form to the queryset.
        
        Args:
            queryset: The base queryset to filter
            
        Returns:
            Filtered queryset based on form data
        """
        # Check if any filters have been applied
        if not self.is_valid() or not self.cleaned_data.get('apply_filters'):
            return queryset
            
        cleaned_data = self.cleaned_data
        
        # Get all questions to process filters
        questions = Question.objects.all()
        
        # Track if any filter has been applied
        any_filter_applied = False
        
        # Apply filters for each question
        for question in questions:
            field_name = f"filter_q_{question.id}"
            
            # Handle numeric range filters
            if hasattr(question.field_type, 'field_type_choice') and question.field_type.field_type_choice == InputFieldType.FieldTypeChoice.NUMBER:
                value_from = cleaned_data.get(f"{field_name}_from")
                value_to = cleaned_data.get(f"{field_name}_to")
                
                if value_from is not None:
                    any_filter_applied = True
                    # Filter responses where text_answer is a number >= value_from
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__text_answer__regex=r'^-?\d+(\.\d+)?$',  # Ensure it's a number
                        responses__text_answer__gte=str(value_from)
                    )
                
                if value_to is not None:
                    any_filter_applied = True
                    # Filter responses where text_answer is a number <= value_to
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__text_answer__regex=r'^-?\d+(\.\d+)?$',  # Ensure it's a number
                        responses__text_answer__lte=str(value_to)
                    )
            
            # Handle choice questions (single or multiple choice)
            elif question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE]:
                selected_options = cleaned_data.get(field_name, [])
                
                # Filter out group headers which are not actual options
                valid_option_ids = [opt_id for opt_id in selected_options if not str(opt_id).startswith('group_')]
                
                if valid_option_ids:
                    any_filter_applied = True
                    # Convert string IDs to integers
                    option_ids = [int(opt_id) for opt_id in valid_option_ids]
                    
                    # Filter submissions where selected_options includes any of the specified options
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__selected_options__id__in=option_ids
                    ).distinct()
            
            # Handle text search for text questions
            else:
                search_text = cleaned_data.get(field_name)
                
                if search_text:
                    any_filter_applied = True
                    # Filter submissions where text_answer contains the search text
                    queryset = queryset.filter(
                        responses__question_id=question.id,
                        responses__text_answer__icontains=search_text
                    )
        
        # If no filters were applied, return all submissions
        if not any_filter_applied:
            return queryset.distinct()
            
        return queryset.distinct()
