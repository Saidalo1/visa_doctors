from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase, SortableTabularInline
from django.contrib.admin import register, ModelAdmin, TabularInline, StackedInline
from django.forms import BaseInlineFormSet
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin
from mptt.admin import DraggableMPTTAdmin
from rest_framework.exceptions import ValidationError

from app.models.pages import (
    About, AboutHighlight, VisaType, VisaDocument,
    ResultCategory, Result, ContactInfo, UniversityLogo
)
from app.models.survey import Question, AnswerOption, SurveySubmission, Response
from shared.django import CustomSortableAdminMixin


class AboutHighlightInline(SortableTabularInline):
    """Inline admin for AboutHighlight with sorting capability."""
    model = AboutHighlight
    extra = 1


@register(About)
class AboutAdmin(SortableAdminBase, TranslationAdmin):
    """Admin interface for About model."""
    list_display = ['title', 'subtitle', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'subtitle', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [AboutHighlightInline]
    date_hierarchy = 'created_at'


class VisaDocumentInline(SortableInlineAdminMixin, TabularInline):
    """Inline admin for VisaDocument with sorting capability."""
    model = VisaDocument
    extra = 1


@register(VisaType)
class VisaTypeAdmin(CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for VisaType model."""
    list_display = ['title', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [VisaDocumentInline]
    date_hierarchy = 'created_at'


@register(ResultCategory)
class ResultCategoryAdmin(TranslationAdmin):
    """Admin interface for ResultCategory model."""
    list_display = ['title', 'subtitle', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'subtitle', 'description']
    date_hierarchy = 'created_at'


@register(Result)
class ResultAdmin(ModelAdmin):
    """Admin interface for Result model."""
    list_display = ['image', 'category']
    list_filter = ['category']


@register(UniversityLogo)
class UniversityLogoAdmin(CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for UniversityLogo model."""
    list_display = ['name', 'logo', 'order', 'created_at']
    list_editable = ['order']
    list_filter = ['created_at']
    search_fields = ['name']
    date_hierarchy = 'created_at'


@register(ContactInfo)
class ContactInfoAdmin(TranslationAdmin):
    """Admin interface for ContactInfo model."""
    list_display = ['phone', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['phone', 'email', 'address']
    date_hierarchy = 'created_at'


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


@register(SurveySubmission)
class SurveySubmissionAdmin(ModelAdmin):
    """Admin interface for SurveySubmission model."""
    list_display = ['id', 'status', 'created_at', 'get_responses_count']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'responses__text_answer']
    readonly_fields = ['created_at']
    inlines = [ResponseInline]
    date_hierarchy = 'created_at'

    def get_responses_count(self, obj):
        """Get number of responses in submission."""
        return obj.responses.count()

    get_responses_count.short_description = 'Responses'


@register(AnswerOption)
class AnswerOptionAdmin(DraggableMPTTAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for AnswerOption model with MPTT and sorting capabilities."""
    list_display = ['tree_actions', 'indented_title', 'question', 'order']
    list_display_links = ['indented_title']
    list_filter = ['question']
    search_fields = ['text']
    mptt_indent_field = "text"

    def indented_title(self, obj):
        """Return the indented title for MPTT tree display."""
        return obj.text

    indented_title.short_description = 'Text'


class AnswerOptionInlineFormSet(BaseInlineFormSet):
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
    # min_num = 2
    fields = 'text', 'parent', 'has_custom_input'


@register(Question)
class QuestionAdmin(CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for Question model."""
    list_display = ['title', 'input_type', 'created_at', 'order']
    list_filter = ['input_type', 'created_at']
    search_fields = ['title', 'placeholder']
    inlines = [AnswerOptionInline]
    date_hierarchy = 'created_at'

    class Media:
        js = (
            'js/hide_answer_options.js',
        )

# Temporarily hide Response admin
# @register(Response)
# class ResponseAdmin(TranslationAdmin):
#     """Admin interface for Response model."""
#     list_display = ['submission', 'question']
#     list_filter = ['submission', 'question']
