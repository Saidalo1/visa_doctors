from adminsortable2.admin import SortableAdminBase
from django.contrib.admin import register, ModelAdmin
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.utils.text import Truncator
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from modeltranslation.admin import TranslationAdmin
from mptt.admin import DraggableMPTTAdmin

from shared.django.admin.utils import AlwaysShowSurveyFilter, StatusFilter

try:
    # Import only from the django-jazzmin-admin-rangefilter module
    from rangefilter.filters import DateRangeFilter
except ImportError:
    # Backup option - use the standard filter
    from django.contrib.admin import DateFieldListFilter as DateRangeFilter

from app.models import (
    About, VisaType, ResultCategory, Result, ContactInfo, UniversityLogo, Question, AnswerOption, SurveySubmission,
    InputFieldType, SubmissionStatus, Response, Survey
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


# @register(SurveySubmission)
# class SurveySubmissionAdmin(ImportExportModelAdmin, ModelAdmin):
#     """Admin interface for SurveySubmission model."""
#     resource_class = SurveySubmissionResource
#     list_display = (
#         'id',
#         'get_full_name',
#         'get_phone_number',
#         'get_language_certificate',
#         'get_field_of_study',
#         'get_status_display',
#         'source',
#         'comment',
#         'created_at',
#         'get_responses_count'
#     )
#     list_filter = ('survey', 'status', 'source', ('created_at', DateRangeFilter))
#     search_fields = 'id', 'responses__text_answer', 'comment'
#     readonly_fields = 'created_at',
#     date_hierarchy = 'created_at'
#     inlines = [ResponseInline]
#     # export_form_class = SurveyExportForm
#
#     # Cache for question filters - will be created once at server startup
#     _cached_question_filters = None
#
#     def get_list_filter(self, request):
#         """
#         Return a sequence containing the fields to be displayed as filters in
#         the right sidebar of the changelist page.
#
#         Uses caching to prevent recreating filters on each request.
#         """
#         # Get base filters from the list_filter attribute
#         base_filters = list(self.list_filter)
#
#         # Use cached filters if they already exist
#         if self.__class__._cached_question_filters is None:
#             # Cache is empty - create filters
#             questions = Question.objects.select_related('field_type')
#             dynamic_filters = []
#
#             for q in questions:
#                 # Get all filters for this question (one per option family)
#                 filter_classes = create_question_filters(q)
#                 # Add each filter to the list
#                 dynamic_filters.extend(filter_classes)
#
#             # Save to cache
#             self.__class__._cached_question_filters = dynamic_filters
#
#         # Return combined filters using cached filters
#         return base_filters + self.__class__._cached_question_filters
#
#     def get_export_queryset(self, request):
#         """
#         Return the base queryset for export. Filtering will be handled by the resource's filter_export method.
#
#         Args:
#             request: The HTTP request object
#
#         Returns:
#             Base queryset for export
#         """
#         return super().get_export_queryset(request)
#
#     def get_export_data(self, file_format, queryset, *args, **kwargs):
#         """
#         Extract data from the export form and pass it to the resource for filtering.
#
#         Args:
#             file_format: The export file format
#             queryset: The queryset to export
#             *args: Additional arguments
#             **kwargs: Additional keyword arguments including export_form
#
#         Returns:
#             Exported data in the specified format
#         """
#         # Store the export form for later use
#         self.export_form = kwargs.get('export_form')
#
#         # Extract form data to pass to the resource's filter_export method
#         if self.export_form and self.export_form.is_valid():
#             form_data = self.export_form.cleaned_data
#
#             # Add form data to kwargs that will be passed to resource.filter_export
#             # Skip file_format since it's already a positional argument
#             for key, value in form_data.items():
#                 if key != 'file_format':  # Skip file_format to avoid duplicate argument
#                     kwargs[key] = value
#
#         return super().get_export_data(file_format, queryset, *args, **kwargs)
#
#     def get_queryset(self, request):
#         """
#         Optimize the queryset for the admin interface by prefetching related responses.
#
#         Args:
#             request: The HTTP request object
#
#         Returns:
#             Optimized queryset with prefetched related objects
#         """
#         qs = super().get_queryset(request)
#         # Optimize the query by loading all related data in a single query
#         return qs.select_related('status').prefetch_related(
#             # Prefetch responses with their related data
#             Prefetch('responses',
#                      queryset=Response.objects.select_related('question', 'question__field_type')
#                      .prefetch_related('selected_options')
#             )
#         )
#
#     def get_responses_count(self, obj):
#         """
#         Get the number of responses in the submission. Uses prefetched data.
#         """
#         # Use len instead of count() to prevent additional DB query
#         return len(obj.responses.all())
#
#     get_responses_count.short_description = _('Responses')
#
#     def get_phone_number(self, obj):
#         """
#         Get phone number from responses, if there is a question with phone field type.
#         Uses prefetched data to prevent additional queries.
#         """
#         try:
#             # Search in already loaded data instead of making a new query
#             for response in obj.responses.all():
#                 if response.question.field_type.field_key.lower() == "phone number":
#                     return response.text_answer or '-'
#         except Exception:
#             pass
#         return '-'
#
#     get_phone_number.short_description = _('Phone Number')
#
#     def get_full_name(self, obj):
#         """
#         Get name from responses, if there is a question with name.
#         Uses prefetched data to prevent additional queries.
#         """
#         try:
#             # Search in already loaded data instead of making a new query
#             for response in obj.responses.all():
#                 if response.question.field_type.field_key.lower() == "name":
#                     return response.text_answer or '-'
#         except Exception:
#             pass
#         return '-'
#
#     get_full_name.short_description = _('Full Name')
#
#     def get_language_certificate(self, obj):
#         """Get information about language certificate.
#         Uses prefetched data to prevent additional queries."""
#         try:
#             # Search in already loaded data instead of making a new query
#             for response in obj.responses.all():
#                 if response.question.field_type.field_key.lower() == "language certificate":
#                     if response.text_answer:  # if there is user input
#                         return response.text_answer
#                     # if there are selected options - they are already loaded via prefetch_related
#                     options = response.selected_options.all()
#                     if options:
#                         return ', '.join(opt.text for opt in options)
#                     return '-'
#         except Exception:
#             pass
#         return '-'
#
#     get_language_certificate.short_description = _('Language Certificate')
#
#     def get_field_of_study(self, obj):
#         """Get information about field of study.
#         Uses prefetched data to prevent additional queries."""
#         try:
#             # Search in already loaded data instead of making a new query
#             for response in obj.responses.all():
#                 if response.question.field_type.field_key.lower() == "field of study":
#                     if response.text_answer:  # if there is user input
#                         return response.text_answer
#                     # if there are selected options - they are already loaded via prefetch_related
#                     options = response.selected_options.all()
#                     if options:
#                         return ', '.join(opt.text for opt in options)
#                     return '-'
#         except Exception:
#             pass
#         return '-'
#
#     get_field_of_study.short_description = _('Field of Study')
#
#     def get_status_display(self, obj):
#         """Display status name from related SubmissionStatus model.
#         Uses select_related to prevent additional queries."""
#         # Status is already loaded via select_related
#         return obj.status.name
#
#     get_status_display.short_description = _('Status')
#
#     def changelist_view(self, request, extra_context=None):
#         """'new' filter is set by default, but if the user removed it manually - don't force it again."""
#
#         # If status filter is missing but other GET parameters exist → user removed the filter manually
#         if "status__code__exact" not in request.GET and request.GET:
#             return super().changelist_view(request, extra_context)
#
#         # If there are no parameters in GET request → it's the first visit, set status "new"
#         if not request.GET:
#             q = request.GET.copy()
#             q["status__code__exact"] = "new"
#             return HttpResponseRedirect(f"{request.path}?{q.urlencode()}")
#
#         return super().changelist_view(request, extra_context)
#
#     class Media:
#         js = 'admin/js/multi_select.js',
#         css = {
#             'all': ['admin/css/multi_select.css']
#         }


@register(AnswerOption)
class AnswerOptionAdmin(ImportExportModelAdmin, DraggableMPTTAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for AnswerOption model with MPTT and sorting capabilities."""
    resource_class = AnswerOptionResource
    list_display = ['tree_actions', 'indented_title', 'question', 'order']
    list_display_links = ['indented_title']
    list_filter = ['question']
    search_fields = ['text']
    mptt_indent_field = "text"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure 'parent' field is present in the form
        if 'parent' not in form.base_fields:
            return form

        if obj:  # Editing an existing AnswerOption
            if obj.question:
                base_queryset = AnswerOption.objects.filter(question=obj.question, parent__isnull=True)
                queryset = base_queryset.exclude(pk=obj.pk)
                if hasattr(obj, 'get_descendants'): # Check if instance is MPTT ready
                    try:
                        descendants = obj.get_descendants(include_self=False).values_list('pk', flat=True)
                        queryset = queryset.exclude(pk__in=list(descendants))
                    except Exception:
                        # MPTT might not be initialized on a partially saved/invalid instance.
                        pass
                form.base_fields['parent'].queryset = queryset
            else:
                # Should not happen for an existing option, but as a fallback
                form.base_fields['parent'].queryset = AnswerOption.objects.none()
        else:  # Adding a new AnswerOption
            # For new options, if a question is pre-selected via URL (e.g., from filter or custom add link)
            # restrict parent choices to that question. Otherwise, allow any (MPTT handles tree_id).
            question_id = request.GET.get('question', None) # Check if 'question' is in GET params
            if not question_id and hasattr(self.model, 'question_id_for_new_instance_from_request'):
                # Attempt to get question_id from a custom attribute if available
                # This part is hypothetical and depends on how you might pass question_id
                question_id = self.model.question_id_for_new_instance_from_request(request)

            if question_id:
                try:
                    form.base_fields['parent'].queryset = AnswerOption.objects.filter(question_id=question_id, parent__isnull=True)
                except ValueError:
                     # Invalid question_id, fallback to empty or all
                    form.base_fields['parent'].queryset = AnswerOption.objects.none() # Or .all() if preferred
            else:
                # No specific question context for a new option, allow selection from any question
                # or make it empty if parent must belong to the same (future) question.
                # For DraggableMPTTAdmin, it's often fine to allow broader selection for 'add' root/child cases.
                # If question is a required field for AnswerOption, this will be caught at validation.
                form.base_fields['parent'].queryset = AnswerOption.objects.none() # No question context, so no parents to choose from
        return form

    def indented_title(self, obj):
        """Return the indented title for MPTT tree display."""
        return obj.text

    indented_title.short_description = 'Text'


@register(Question)
class QuestionAdmin(ImportExportModelAdmin, CustomSortableAdminMixin, TranslationAdmin):
    """Admin interface for Question model."""
    resource_class = QuestionResource
    list_display = ['survey', 'title', 'input_type', 'field_type', 'is_required', 'created_at', 'order']
    list_filter = ['survey', 'input_type', 'field_type', 'is_required', 'created_at']
    search_fields = ['title', 'field_type__title', 'placeholder']
    list_editable = 'is_required',
    inlines = [AnswerOptionInline]
    date_hierarchy = 'created_at'
    autocomplete_fields = ['field_type']
    fieldsets = [
        (None, {
            'fields': ('survey', 'title', 'placeholder', 'is_required', 'is_title')
        }),
        (_('Input Configuration'), {
            'fields': ('input_type', 'field_type')
        })
    ]

    class Media:
        js = (
            'js/hide_answer_options.js',
        )


@register(Survey)
class SurveyModelAdmin(TranslationAdmin):
    """Admin interface for Survey model."""
    list_display = ['title', 'is_active', 'is_default', 'slug']
    list_filter = ['is_active', 'is_default']
    search_fields = ['title', 'slug']
    readonly_fields = 'telegram_topic_id',


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


@register(SurveySubmission)
class SurveySubmissionAdmin(ImportExportModelAdmin, ModelAdmin):
    """Admin interface for SurveySubmission model with dynamic question columns."""
    resource_class = SurveySubmissionResource
    # Базовые поля, которые всегда будут отображаться
    base_list_display = [
        'survey',
        'status',
        'source',
        'comment',
        'created_at',
        'get_responses_count'
    ]
    list_filter = AlwaysShowSurveyFilter, StatusFilter, 'source', ('created_at', DateRangeFilter)
    search_fields = 'id', 'responses__text_answer', 'comment'
    readonly_fields = 'created_at',
    date_hierarchy = 'created_at'
    inlines = [ResponseInline]

    # export_form_class = SurveyExportForm

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_export_resource_kwargs(request, *args, **kwargs)
        survey_id = request.GET.get('survey')
        if survey_id:
            kwargs['survey_id'] = survey_id
        # print(f"Passing to resource kwargs: {kwargs}")
        return kwargs

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # Кэш для динамических методов
        self._dynamic_methods_cache = {}

    def get_list_display(self, request):
        """
        Динамически формируем список отображаемых полей на основе вопросов из базы данных.
        """
        # Получаем базовый список полей
        list_display = ['id']

        # Get the selected questionnaire from the request parameters
        survey_id = request.GET.get('survey')

        # If no questionnaire is selected, use the default questionnaire
        try:
            from app.models import Survey

            if not survey_id:
                # Search for the default questionnaire
                default_survey = Survey.objects.filter(is_default=True).first()
                if default_survey:
                    survey_id = default_survey.id
        except:
            pass

        # Получаем все вопросы и сортируем их по порядку
        questions = Question.objects.filter(survey_id=survey_id).order_by('order')

        # Для каждого вопроса создаем динамический метод получения ответа
        for question in questions:
            # Создаем метод только если его еще нет
            method_name = f'get_question_{question.id}_answer'
            if method_name not in self._dynamic_methods_cache:
                # Создаем функцию динамически
                def create_method(q_id):
                    def method(self, obj):
                        for response in obj.responses.all():
                            if response.question_id == q_id:
                                answer_text = response.text_answer
                                if not answer_text:
                                    options = response.selected_options.all()
                                    if options:
                                        answer_text = ', '.join(opt.text for opt in options)
                                if answer_text:
                                    # Truncate the answer text to 50 characters
                                    return Truncator(strip_tags(answer_text)).chars(50)
                                return '-'
                        return '-'

                    return method

                # Создаем динамический метод
                dynamic_method = create_method(question.id)
                # Добавляем метод к классу администратора
                setattr(SurveySubmissionAdmin, method_name, dynamic_method)
                # Устанавливаем описание для колонки
                getattr(SurveySubmissionAdmin, method_name).short_description = question.field_type.field_key
                # Кэшируем метод
                self._dynamic_methods_cache[method_name] = True

            # Добавляем метод в список отображаемых полей
            list_display.append(method_name)
        list_display += self.base_list_display

        return list_display

    def get_list_filter(self, request):
        """We create filters for the admin panel, taking into account the selected questionnaire.
        If the questionnaire is selected, we show filters only for its questions.
        If the questionnaire is not selected, we use the default questionnaire.
        """
        # Get basic filters
        base_filters = list(self.list_filter)

        # Get the selected questionnaire from the request parameters
        survey_id = request.GET.get('survey')

        # If no questionnaire is selected, use the default questionnaire
        try:
            from app.models import Survey

            if not survey_id:
                # Search for the default questionnaire
                default_survey = Survey.objects.filter(is_default=True).first()
                if default_survey:
                    survey_id = default_survey.id
        except:
            pass

        # Filter questions by the selected questionnaire
        questions_query = Question.objects.all()
        if survey_id:
            try:
                survey_id = int(survey_id)
                questions_query = questions_query.filter(survey_id=survey_id)
            except (ValueError, TypeError):
                pass

        # Add dynamic filters for each question
        dynamic_filters = []
        for q in questions_query:
            # Get all filters for this question (one for each option family)
            filter_classes = create_question_filters(q)
            # Add filters to the list
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

    def changelist_view(self, request, extra_context=None):
        """
        Добавляем автоматическую фильтрацию по умолчанию:
        1. Статус 'new' по умолчанию
        2. Опросник по умолчанию, если есть
        
        Если пользователь убрал фильтры вручную - не навязываем их снова.
        """
        # Если в GET-запросе уже есть параметры - пользователь сам выбрал фильтры
        if request.GET:
            return super().changelist_view(request, extra_context)

        # Если это первый заход - добавляем фильтры по умолчанию
        q = request.GET.copy()

        # Добавляем фильтр по статусу "new"
        # Используем параметр status для кастомного StatusFilter
        if "status" not in q:
            q["status"] = "new"

        # Добавляем фильтр по опроснику по умолчанию
        try:
            from app.models import Survey

            # Получаем опросник по умолчанию
            default_survey = Survey.objects.filter(is_default=True, is_active=True).first()
            if default_survey:
                q["survey"] = str(default_survey.id)
            else:
                # Если нет опросника по умолчанию, пробуем найти любой активный опросник
                any_active_survey = Survey.objects.filter(is_active=True).first()
                if any_active_survey:
                    q["survey"] = str(any_active_survey.id)
        except Exception:
            pass

        return HttpResponseRedirect(f"{request.path}?{q.urlencode()}")

    class Media:
        js = 'admin/js/multi_select.js',
        css = {
            'all': ['admin/css/multi_select.css']
        }
