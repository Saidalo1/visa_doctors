from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from app.models import Survey


class AlwaysShowSurveyFilter(SimpleListFilter):
    title = _('Survey')
    parameter_name = 'survey'

    def lookups(self, request, model_admin):
        return [(s.pk, s.title) for s in Survey.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(survey__pk=self.value())
        return queryset
