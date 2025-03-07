from adminsortable2.admin import SortableAdminBase
from django.contrib.admin import register, ModelAdmin
from import_export.admin import ImportExportModelAdmin
from modeltranslation.admin import TranslationAdmin
from mptt.admin import DraggableMPTTAdmin

from app.models import (
    About, VisaType, ResultCategory, Result, ContactInfo, UniversityLogo, Question, AnswerOption, SurveySubmission,
    InputFieldType
)
from app.resource import QuestionResource, InputFieldTypeResource, SurveySubmissionResource, AnswerOptionResource
from shared.django.admin import (
    AboutHighlightInline, VisaDocumentInline,
    ResponseInline, AnswerOptionInline, CustomSortableAdminMixin
)


@register(About)
class AboutAdmin(SortableAdminBase, TranslationAdmin):
    """Admin interface for About model."""
    list_display = ['title', 'subtitle', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'subtitle', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [AboutHighlightInline]
    date_hierarchy = 'created_at'


@register(VisaType)
class VisaTypeAdmin(CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for VisaType model."""
    list_display = ['title', 'slug', 'created_at', 'order']
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


@register(SurveySubmission)
class SurveySubmissionAdmin(ImportExportModelAdmin, ModelAdmin):
    """Admin interface for SurveySubmission model."""
    resource_class = SurveySubmissionResource
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
class AnswerOptionAdmin(ImportExportModelAdmin, DraggableMPTTAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for AnswerOption model with MPTT and sorting capabilities."""
    resource_class = AnswerOptionResource
    list_display = ['tree_actions', 'indented_title', 'question', 'order']
    list_display_links = ['indented_title']
    list_filter = ['question']
    search_fields = ['text']
    mptt_indent_field = "text"

    def indented_title(self, obj):
        """Return the indented title for MPTT tree display."""
        return obj.text

    indented_title.short_description = 'Text'


@register(Question)
class QuestionAdmin(ImportExportModelAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for Question model."""
    resource_class = QuestionResource
    list_display = ['title', 'input_type', 'field_type', 'created_at', 'order']
    list_filter = ['input_type', 'field_type', 'created_at']
    search_fields = ['title', 'placeholder']
    inlines = [AnswerOptionInline]
    date_hierarchy = 'created_at'
    autocomplete_fields = ['field_type']

    class Media:
        js = (
            'js/hide_answer_options.js',
        )


@register(InputFieldType)
class InputFieldTypeAdmin(ImportExportModelAdmin, TranslationAdmin):
    """Admin interface for InputFieldType model."""
    resource_class = InputFieldTypeResource
    list_display = ['title', 'regex_pattern', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'regex_pattern', 'error_message']
    date_hierarchy = 'created_at'
    search_help_text = "Search by title, regex pattern or error message"

# Temporarily hide Response admin
# @register(Response)
# class ResponseAdmin(ImportExportModelAdmin, TranslationAdmin):
#     """Admin interface for Response model."""
#     resource_class = ResponseResource
#     list_display = ['submission', 'question', 'text_answer', 'created_at']
#     list_filter = ['question', 'created_at']
#     search_fields = ['text_answer']
#     date_hierarchy = 'created_at'
