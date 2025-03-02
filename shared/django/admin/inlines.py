"""Admin inline classes for reuse across apps."""

from adminsortable2.admin import SortableTabularInline, SortableInlineAdminMixin
from django.contrib.admin import TabularInline, StackedInline
from django.forms import BaseInlineFormSet
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationTabularInline
from rest_framework.exceptions import ValidationError

from app.models.pages import AboutHighlight, VisaDocument
from app.models.survey import Response, Question, AnswerOption


class AboutHighlightInline(SortableInlineAdminMixin, TranslationTabularInline):
    """Inline admin for AboutHighlight with sorting capability."""
    model = AboutHighlight
    extra = 1


class VisaDocumentInline(SortableInlineAdminMixin, TranslationTabularInline):
    """Inline admin for VisaDocument with sorting capability."""
    model = VisaDocument
    extra = 1


class ResponseInline(StackedInline):
    """Inline admin for Response model."""
    model = Response
    extra = 0
    readonly_fields = ['question', 'get_answer_display']
    fields = ['question', 'get_answer_display']
    can_delete = False
    max_num = 0

    def get_answer_display(self, obj):
        """Format answer display based on question type."""
        if obj.question.input_type in [Question.InputType.SINGLE_CHOICE, Question.InputType.MULTIPLE_CHOICE]:
            options = obj.selected_options.all()
            return format_html(
                '<br>'.join(f'• {opt.text}' for opt in options)
            ) if options else '-'
        return obj.text_answer or '-'

    get_answer_display.short_description = 'Answer'


class AnswerOptionInlineFormSet(BaseInlineFormSet):
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


class AnswerOptionInline(StackedInline):
    """Inline admin for AnswerOption model."""
    model = AnswerOption
    formset = AnswerOptionInlineFormSet
    extra = 2
    fields = ('text', 'parent', 'has_custom_input')
