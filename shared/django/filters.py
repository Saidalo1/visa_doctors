from django_filters.rest_framework import FilterSet

from app.models import Question


class QuestionFilter(FilterSet):

    class Meta:
        model = Question
        fields = ['survey_id']
