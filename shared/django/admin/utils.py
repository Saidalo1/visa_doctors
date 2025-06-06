from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from app.models import Survey


class AlwaysShowSurveyFilter(SimpleListFilter):
    title = _('Survey')
    parameter_name = 'survey'

    def lookups(self, request, model_admin):
        return [(str(s.pk), s.title) for s in Survey.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            try:
                return queryset.filter(survey__pk=int(self.value()))
            except (ValueError, TypeError):
                return queryset.none()
        return queryset


class StatusFilter(SimpleListFilter):
    """Фильтр для поля status модели SurveySubmission.
    
    Правильно работает со связью на модель SubmissionStatus через поле code.
    """
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        from app.models.status import SubmissionStatus
        return [(str(s.code), s.name) for s in SubmissionStatus.objects.filter(active=True).order_by('order')]

    def queryset(self, request, queryset):
        # Get all selected status codes from the request
        selected_statuses = request.GET.getlist(self.parameter_name)

        if selected_statuses:
            # Filter by multiple status codes if any are selected
            return queryset.filter(status__code__in=selected_statuses)
        # If no statuses are selected (e.g., 'All' is chosen or no filter applied),
        # return the original queryset
        return queryset
