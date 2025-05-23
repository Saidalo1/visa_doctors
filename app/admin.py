from adminsortable2.admin import SortableAdminBase
from django.contrib.admin import register, ModelAdmin
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from modeltranslation.admin import TranslationAdmin
from mptt.admin import DraggableMPTTAdmin

try:
    # Import only from the django-jazzmin-admin-rangefilter module
    from rangefilter.filters import DateRangeFilter
except ImportError:
    # Backup option - use the standard filter
    from django.contrib.admin import DateFieldListFilter as DateRangeFilter

from app.models import (
    About, VisaType, ResultCategory, Result, ContactInfo, UniversityLogo, Question, AnswerOption, SurveySubmission,
    InputFieldType, SubmissionStatus, Response
)
from app.resource import QuestionResource, InputFieldTypeResource, SurveySubmissionResource, AnswerOptionResource


from shared.django.admin import (
    AboutHighlightInline, VisaDocumentInline,
    AnswerOptionInline, CustomSortableAdminMixin, ResponseInline
)
from shared.django.admin.filters import create_question_filters


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
    list_display = ['name', 'logo', 'url', 'order', 'created_at']
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
    list_display = (
        'id', 
        'get_full_name', 
        'get_phone_number',
        'get_language_certificate',
        'get_field_of_study',
        'get_status_display',
        'source', 
        'comment',
        'created_at', 
        'get_responses_count'
    )
    list_filter = ('status', 'source', ('created_at', DateRangeFilter))
    search_fields = 'id', 'responses__text_answer', 'comment'
    readonly_fields = 'created_at',
    date_hierarchy = 'created_at'
    inlines = [ResponseInline]
    # export_form_class = SurveyExportForm
    
    # Cache for question filters - will be created once at server startup
    _cached_question_filters = None
    
    def get_list_filter(self, request):
        """
        Return a sequence containing the fields to be displayed as filters in
        the right sidebar of the changelist page.
        
        Uses caching to prevent recreating filters on each request.
        """
        # Get base filters from the list_filter attribute
        base_filters = list(self.list_filter)

        # Use cached filters if they already exist
        if self.__class__._cached_question_filters is None:
            # Cache is empty - create filters
            questions = Question.objects.select_related('field_type')
            dynamic_filters = []

            for q in questions:
                # Get all filters for this question (one per option family)
                filter_classes = create_question_filters(q)
                # Add each filter to the list
                dynamic_filters.extend(filter_classes)
                
            # Save to cache
            self.__class__._cached_question_filters = dynamic_filters
        
        # Return combined filters using cached filters
        return base_filters + self.__class__._cached_question_filters

    def get_export_queryset(self, request):
        """
        Return the base queryset for export. Filtering will be handled by the resource's filter_export method.

        Args:
            request: The HTTP request object

        Returns:
            Base queryset for export
        """
        return super().get_export_queryset(request)

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        """
        Extract data from the export form and pass it to the resource for filtering.

        Args:
            file_format: The export file format
            queryset: The queryset to export
            *args: Additional arguments
            **kwargs: Additional keyword arguments including export_form

        Returns:
            Exported data in the specified format
        """
        # Store the export form for later use
        self.export_form = kwargs.get('export_form')

        # Extract form data to pass to the resource's filter_export method
        if self.export_form and self.export_form.is_valid():
            form_data = self.export_form.cleaned_data
            
            # Add form data to kwargs that will be passed to resource.filter_export
            # Skip file_format since it's already a positional argument
            for key, value in form_data.items():
                if key != 'file_format':  # Skip file_format to avoid duplicate argument
                    kwargs[key] = value

        return super().get_export_data(file_format, queryset, *args, **kwargs)

    def get_queryset(self, request):
        """
        Optimize the queryset for the admin interface by prefetching related responses.

        Args:
            request: The HTTP request object

        Returns:
            Optimized queryset with prefetched related objects
        """
        qs = super().get_queryset(request)
        # Optimize the query by loading all related data in a single query
        return qs.select_related('status').prefetch_related(
            # Prefetch responses with their related data
            Prefetch('responses', 
                     queryset=Response.objects.select_related('question', 'question__field_type')
                     .prefetch_related('selected_options')
            )
        )

    def get_responses_count(self, obj):
        """
        Get the number of responses in the submission. Uses prefetched data.
        """
        # Use len instead of count() to prevent additional DB query
        return len(obj.responses.all())

    get_responses_count.short_description = _('Responses')

    def get_phone_number(self, obj):
        """
        Get phone number from responses, if there is a question with phone field type.
        Uses prefetched data to prevent additional queries.
        """
        try:
            # Search in already loaded data instead of making a new query
            for response in obj.responses.all():
                if response.question.field_type.field_key.lower() == "phone number":
                    return response.text_answer or '-'
        except Exception:
            pass
        return '-'

    get_phone_number.short_description = _('Phone Number')

    def get_full_name(self, obj):
        """
        Get name from responses, if there is a question with name.
        Uses prefetched data to prevent additional queries.
        """
        try:
            # Search in already loaded data instead of making a new query
            for response in obj.responses.all():
                if response.question.field_type.field_key.lower() == "name":
                    return response.text_answer or '-'
        except Exception:
            pass
        return '-'

    get_full_name.short_description = _('Full Name')

    def get_language_certificate(self, obj):
        """Get information about language certificate.
        Uses prefetched data to prevent additional queries."""
        try:
            # Search in already loaded data instead of making a new query
            for response in obj.responses.all():
                if response.question.field_type.field_key.lower() == "language certificate":
                    if response.text_answer:  # if there is user input
                        return response.text_answer
                    # if there are selected options - they are already loaded via prefetch_related
                    options = response.selected_options.all()
                    if options:
                        return ', '.join(opt.text for opt in options)
                    return '-'
        except Exception:
            pass
        return '-'
        
    get_language_certificate.short_description = _('Language Certificate')

    def get_field_of_study(self, obj):
        """Get information about field of study.
        Uses prefetched data to prevent additional queries."""
        try:
            # Search in already loaded data instead of making a new query
            for response in obj.responses.all():
                if response.question.field_type.field_key.lower() == "field of study":
                    if response.text_answer:  # if there is user input
                        return response.text_answer
                    # if there are selected options - they are already loaded via prefetch_related
                    options = response.selected_options.all()
                    if options:
                        return ', '.join(opt.text for opt in options)
                    return '-'
        except Exception:
            pass
        return '-'
        
    get_field_of_study.short_description = _('Field of Study')

    def get_status_display(self, obj):
        """Display status name from related SubmissionStatus model.
        Uses select_related to prevent additional queries."""
        # Status is already loaded via select_related
        return obj.status.name
        
    get_status_display.short_description = _('Status')
    
    def changelist_view(self, request, extra_context=None):
        """'new' filter is set by default, but if the user removed it manually - don't force it again."""

        # If status filter is missing but other GET parameters exist → user removed the filter manually
        if "status__code__exact" not in request.GET and request.GET:
            return super().changelist_view(request, extra_context)

        # If there are no parameters in GET request → it's the first visit, set status "new"
        if not request.GET:
            q = request.GET.copy()
            q["status__code__exact"] = "new"
            return HttpResponseRedirect(f"{request.path}?{q.urlencode()}")

        return super().changelist_view(request, extra_context)

    class Media:
        js = 'admin/js/multi_select.js',
        css = {
            'all': ['admin/css/multi_select.css']
        }


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
    list_display = ['title', 'input_type', 'field_type', 'is_required', 'created_at', 'order']
    list_filter = ['input_type', 'field_type', 'is_required', 'created_at']
    search_fields = ['title', 'field_type__title', 'placeholder']
    list_editable = 'is_required',
    inlines = [AnswerOptionInline]
    date_hierarchy = 'created_at'
    autocomplete_fields = ['field_type']
    fieldsets = [
        (None, {
            'fields': ('title', 'placeholder', 'is_required')
        }),
        (_('Input Configuration'), {
            'fields': ('input_type', 'field_type')
        })
    ]

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


@register(SubmissionStatus)
class SubmissionStatusAdmin(ImportExportModelAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for SubmissionStatus model."""
    list_display = [
        'name', 'code', 'color', 'is_default', 'is_final', 'active', 'created_at', 'order'
    ]
    list_filter = ['is_default', 'is_final', 'active', 'created_at']
    search_fields = ['name', 'code', 'description']
    list_editable = ['order', 'color', 'is_default', 'is_final', 'active']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        (None, {
            'fields': ('name', 'code', 'description', 'color')
        }),
        (_('Status Behavior'), {
            'fields': ('is_default', 'is_final', 'active')
        }),
        (_('System Information'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    ]

    class Media:
        css = {
            'all': ['admin/css/status_colors.css']
        }
        js = ['admin/js/status_colors.js']
