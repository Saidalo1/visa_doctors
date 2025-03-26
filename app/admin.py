from adminsortable2.admin import SortableAdminBase
from django.contrib.admin import register, ModelAdmin
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from modeltranslation.admin import TranslationAdmin
from mptt.admin import DraggableMPTTAdmin
from django.http import HttpResponseRedirect

try:
    # Импортируем только из модуля django-jazzmin-admin-rangefilter
    from rangefilter.filters import DateRangeFilter
except ImportError:
    # Резервный вариант - используем стандартный фильтр
    from django.contrib.admin import DateFieldListFilter as DateRangeFilter

from app.models import (
    About, VisaType, ResultCategory, Result, ContactInfo, UniversityLogo, Question, AnswerOption, SurveySubmission,
    InputFieldType
)
from app.resource import QuestionResource, InputFieldTypeResource, SurveySubmissionResource, AnswerOptionResource
from shared.django.admin import (
    AboutHighlightInline, VisaDocumentInline,
    AnswerOptionInline, CustomSortableAdminMixin, ResponseInline
)
from shared.django.admin.filters import create_question_filters
from shared.django.admin.forms import SurveyExportForm


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
        'status', 
        'created_at', 
        'get_responses_count'
    )
    list_filter = ('status', ('created_at', DateRangeFilter))
    search_fields = 'id', 'responses__text_answer'
    readonly_fields = 'created_at',
    date_hierarchy = 'created_at'
    inlines = [ResponseInline]
    # export_form_class = SurveyExportForm

    def get_list_filter(self, request):
        """
        Return a sequence containing the fields to be displayed as filters in
        the right sidebar of the changelist page.
        """
        # Get base filters from the list_filter attribute
        base_filters = list(self.list_filter)

        # Add dynamic filters for each question
        questions = Question.objects.all()
        dynamic_filters = []

        for q in questions:
            # Get all filters for this question (one per option family)
            filter_classes = create_question_filters(q)
            # Add each filter to the list
            dynamic_filters.extend(filter_classes)

        # Return combined filters
        return base_filters + dynamic_filters

    def get_export_queryset(self, request):
        """
        Return the base queryset for export. Filtering will be handled by the resource's filter_export method.

        Args:
            request: The HTTP request object

        Returns:
            Base queryset for export
        """
        # We'll just log the form data for debugging but won't apply filters here
        # as they will be applied in resource.filter_export
        # if hasattr(self, 'export_form') and self.export_form.is_valid():
            # print(f"Export form data: {self.export_form.cleaned_data}")

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
            # print(f"Export form data: {form_data}")

            # Add form data to kwargs that will be passed to resource.filter_export
            # Skip file_format since it's already a positional argument
            for key, value in form_data.items():
                if key != 'file_format':  # Skip file_format to avoid duplicate argument
                    kwargs[key] = value

        # print(file_format, kwargs)
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
        return qs.prefetch_related('responses', 'responses__selected_options', 'responses__question')

    def get_responses_count(self, obj):
        """
        Получить количество ответов в заявке.
        """
        return obj.responses.count()

    get_responses_count.short_description = _('Responses')

    def get_phone_number(self, obj):
        """
        Получить номер телефона из ответов, если есть вопрос с типом поля для телефона.
        """
        # Ищем ответ на вопрос с телефоном (по field_type или field_title)
        try:
            phone_response = obj.responses.filter(
                question__field_type__field_key__iexact="phone number"
            ).first()

            if phone_response:
                return phone_response.text_answer
        except Exception:
            pass

        return '-'

    get_phone_number.short_description = _('Phone Number')

    def get_full_name(self, obj):
        """
        Получить имя из ответов, если есть вопрос с именем.
        """
        # Ищем ответ на вопрос с именем (по field_title или title)
        try:
            name_response = obj.responses.filter(
                question__field_type__field_key__iexact="name"
            ).first()

            if name_response:
                return name_response.text_answer
        except Exception:
            pass

        return '-'

    get_full_name.short_description = _('Full Name')

    def get_language_certificate(self, obj):
        """Получить информацию о языковом сертификате."""
        try:
            cert_response = obj.responses.filter(
                question__field_type__field_key__iexact="language certificate"
            ).first()
            if cert_response:
                if cert_response.text_answer:  # если есть пользовательский ввод
                    return cert_response.text_answer
                # если есть выбранные опции
                options = cert_response.selected_options.all()
                if options:
                    return ', '.join(opt.text for opt in options)
            return '-'
        except Exception:
            return '-'
    get_language_certificate.short_description = _('Language Certificate')

    def get_field_of_study(self, obj):
        """Получить информацию о направлении обучения."""
        try:
            study_response = obj.responses.filter(
                question__field_type__field_key__iexact="field of study"
            ).first()
            if study_response:
                if study_response.text_answer:  # если есть пользовательский ввод
                    return study_response.text_answer
                # если есть выбранные опции
                options = study_response.selected_options.all()
                if options:
                    return ', '.join(opt.text for opt in options)
            return '-'
        except Exception:
            return '-'
    get_field_of_study.short_description = _('Field of Study')

    def changelist_view(self, request, extra_context=None):
        """Фильтр 'new' ставится по умолчанию, но если пользователь убрал его вручную — не навязываем снова."""

        # Если фильтр статуса отсутствует, но другие GET-параметры есть → юзер сам убрал фильтр
        if "status__exact" not in request.GET and request.GET:
            return super().changelist_view(request, extra_context)

        # Если в GET-запросе вообще нет параметров → значит, это первый заход, ставим статус "new"
        if not request.GET:
            q = request.GET.copy()
            q["status__exact"] = "new"
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
    search_fields = ['title', 'field_type__field_title', 'placeholder']
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
