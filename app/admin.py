from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin, SortableAdminBase, SortableTabularInline
from django.contrib.admin import register, ModelAdmin, TabularInline, StackedInline
from django.utils.html import format_html
from mptt.admin import DraggableMPTTAdmin

from app.models.pages import (
    About, AboutHighlight, VisaType, VisaDocument,
    ResultCategory, Result, ContactInfo, UniversityLogo
)
from app.models.survey import Question, AnswerOption, SurveySubmission, Response


class AboutHighlightInline(SortableTabularInline):
    """Inline admin for AboutHighlight with sorting capability."""
    model = AboutHighlight
    extra = 1


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


@register(UniversityLogo)
class UniversityLogoAdmin(SortableAdminMixin, ModelAdmin):
    """Admin interface for UniversityLogo model."""
    list_display = ['name', 'logo', 'order']
    list_editable = ['order']


@register(ContactInfo)
class ContactInfoAdmin(ModelAdmin):
    """Admin interface for ContactInfo model."""
    list_display = ['phone', 'email']


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
    readonly_fields = ['created_at']
    inlines = [ResponseInline]
    
    def get_responses_count(self, obj):
        """Get number of responses in submission."""
        return obj.responses.count()
    get_responses_count.short_description = 'Responses'


@register(Question)
class QuestionAdmin(SortableAdminMixin, ModelAdmin):
    """Admin interface for Question model."""
    list_display = ['title', 'input_type', 'order']
    list_filter = ['input_type']
    search_fields = ['title']


@register(AnswerOption)
class AnswerOptionAdmin(DraggableMPTTAdmin, SortableAdminMixin, ModelAdmin):
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


@register(Response)
class ResponseAdmin(ModelAdmin):
    """Admin interface for Response model."""
    list_display = ['submission', 'question']
    list_filter = ['submission', 'question']
