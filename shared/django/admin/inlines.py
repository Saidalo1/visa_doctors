"""Admin inline classes for reuse across apps."""

from adminsortable2.admin import SortableInlineAdminMixin
from django.contrib.admin import StackedInline
from django.forms import BaseInlineFormSet, ModelForm
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationTabularInline, TranslationStackedInline
from rest_framework.exceptions import ValidationError

from app.models import AboutHighlight, VisaDocument, Response, AnswerOption
from shared.django.admin.widgets import QuestionSelectWidget


class AboutHighlightInline(SortableInlineAdminMixin, TranslationTabularInline):
    """Inline admin for AboutHighlight with sorting capability."""
    model = AboutHighlight
    extra = 1


class VisaDocumentInline(SortableInlineAdminMixin, TranslationTabularInline):
    """Inline admin for VisaDocument with sorting capability."""
    model = VisaDocument
    extra = 1


class ResponseForm(ModelForm):
    """
    Custom form for Response model with a custom question widget
    that adds data attributes for JavaScript functionality.
    """
    class Meta:
        model = Response
        fields = 'question', 'text_answer', 'selected_options'
        widgets = {
            'question': QuestionSelectWidget,
        }


class ResponseInline(StackedInline):
    """Inline admin for Response model."""
    model = Response
    form = ResponseForm
    extra = 0
    fields = 'question', 'text_answer', 'selected_options'
    autocomplete_fields = ['selected_options']

    class Media:
        js = 'js/readonly_questions.js',


class AnswerOptionInlineFormSet(BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_object'] = self.instance  # self.instance here is the Question model instance
        return kwargs
    """Form set for AnswerOption inline with validation."""

    def clean(self):
        super().clean()
        # self.instance is the parent Question instance
        input_type = self.instance.input_type

        # Count forms that are not marked for deletion and have no errors
        valid_forms = [
            form for form in self.forms
            if not form.cleaned_data.get('DELETE', False) and not form.errors
        ]

        if input_type in ('single_choice', 'multiple_choice'):
            # Require at least 2 options for single/multiple choice input types
            if len(valid_forms) < 2:
                raise ValidationError(
                    _('At least 2 answer options are required for single/multiple choice.')
                )


class AnswerOptionInlineForm(ModelForm):
    class Meta:
        model = AnswerOption
        fields = 'text', 'parent', 'has_custom_input'

    def __init__(self, *args, **kwargs):
        # Pop custom kwargs before calling super
        self.parent_object = kwargs.pop('parent_object', None)
        super().__init__(*args, **kwargs)

        if 'parent' not in self.fields:
            return

        current_question = None
        if self.parent_object and self.parent_object.pk:
            current_question = self.parent_object
        
        if current_question:
            base_queryset = AnswerOption.objects.filter(question=current_question, parent__isnull=True)

            if self.instance and self.instance.pk:  # Editing an existing AnswerOption
                queryset = base_queryset.exclude(pk=self.instance.pk)
                if hasattr(self.instance, 'get_descendants'): # Check if instance is MPTT ready
                    try:
                        descendants = self.instance.get_descendants(include_self=False).values_list('pk', flat=True)
                        queryset = queryset.exclude(pk__in=list(descendants))
                    except Exception:
                        # Could log this if needed, MPTT might not be initialized
                        # on a partially saved/invalid instance during form validation cycle.
                        pass
                self.fields['parent'].queryset = queryset
            else:  # Adding a new AnswerOption
                self.fields['parent'].queryset = base_queryset
        else:
            # No current_question (e.g. Question admin 'add' page before Question is saved)
            self.fields['parent'].queryset = AnswerOption.objects.none()


class AnswerOptionInline(TranslationStackedInline):
    """Inline admin for AnswerOption model."""
    model = AnswerOption
    formset = AnswerOptionInlineFormSet
    form = AnswerOptionInlineForm
    extra = 2
    fields = 'text', 'parent', 'has_custom_input'

