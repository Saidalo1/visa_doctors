from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin, SortableAdminBase, SortableTabularInline
from django.contrib.admin import register, ModelAdmin, TabularInline
from mptt.admin import DraggableMPTTAdmin

from app.models.pages import (
    About, AboutHighlight, VisaType, VisaDocument,
    ResultCategory, Result, ContactInfo
)
from app.models.survey import Question, AnswerOption, SurveySubmission, Response


class AboutHighlightInline(SortableInlineAdminMixin, TabularInline):
    """Inline admin for AboutHighlight with sorting capability."""
    model = AboutHighlight
    extra = 1
    template = 'admin/edit_inline/tabular.html'


@register(About)
class AboutAdmin(SortableAdminBase, ModelAdmin):
    """Admin interface for About model."""
    list_display = ['title', 'subtitle']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [AboutHighlightInline]


class VisaDocumentInline(SortableInlineAdminMixin, TabularInline):
    """Inline admin for VisaDocument with sorting capability."""
    model = VisaDocument
    extra = 1


@register(VisaType)
class VisaTypeAdmin(SortableAdminMixin, ModelAdmin):
    """Admin interface for VisaType model."""
    list_display = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [VisaDocumentInline]


@register(ResultCategory)
class ResultCategoryAdmin(ModelAdmin):
    """Admin interface for ResultCategory model."""
    list_display = ['title']


@register(Result)
class ResultAdmin(ModelAdmin):
    """Admin interface for Result model."""
    list_display = ['image', 'category']
    list_filter = ['category']


@register(ContactInfo)
class ContactInfoAdmin(ModelAdmin):
    """Admin interface for ContactInfo model."""
    list_display = ['phone', 'email']


@register(Question)
class QuestionAdmin(SortableAdminMixin, ModelAdmin):
    """Admin interface for Question model with sorting capability."""
    list_display = ['description', 'input_type', 'order']
    list_filter = ['input_type']


@register(AnswerOption)
class AnswerOptionAdmin(DraggableMPTTAdmin, SortableAdminMixin, ModelAdmin):
    """Admin interface for AnswerOption model with MPTT and sorting capabilities."""
    list_display = ['tree_actions', 'indented_title', 'question', 'order']
    list_display_links = ['indented_title']
    list_filter = ['question']

    def indented_title(self, obj):
        """Return the indented title for MPTT tree display."""
        return obj.text

    indented_title.short_description = 'Text'


@register(SurveySubmission)
class SurveySubmissionAdmin(ModelAdmin):
    """Admin interface for SurveySubmission model."""
    list_display = ['created_at', 'status']
    list_filter = ['status']
    readonly_fields = ['created_at']


@register(Response)
class ResponseAdmin(ModelAdmin):
    """Admin interface for Response model."""
    list_display = ['submission', 'question']
    list_filter = ['submission', 'question']
