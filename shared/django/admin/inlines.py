"""Admin inline classes for reuse across apps."""

from adminsortable2.admin import SortableInlineAdminMixin
from django.contrib.admin import StackedInline
from django.forms import BaseInlineFormSet, ModelForm
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationTabularInline, TranslationStackedInline
from rest_framework.exceptions import ValidationError

from app.models import AboutHighlight, VisaDocument, Response, AnswerOption


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
    fields = 'question', 'text_answer', 'selected_options'
    autocomplete_fields = ['selected_options']

    class Media:
        js = 'js/readonly_questions.js',


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


class AnswerOptionInlineForm(ModelForm):
    class Meta:
        model = AnswerOption
        fields = 'text', 'parent', 'has_custom_input'


class AnswerOptionInline(TranslationStackedInline):
    """Inline admin for AnswerOption model."""
    model = AnswerOption
    formset = AnswerOptionInlineFormSet
    form = AnswerOptionInlineForm
    extra = 2
    fields = 'text', 'parent', 'has_custom_input'

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'parent' and self:
            kwargs['queryset'] = AnswerOption.objects.filter(parent__isnull=True,
                                                             question_id=request.path.replace('/change/', '')[-1])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
