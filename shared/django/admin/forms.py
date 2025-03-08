from django.forms import ModelChoiceField, CharField
from import_export.forms import ExportForm

from app.models import Question


class SurveyExportForm(ExportForm):
    """
    Customized ExportForm, где пользователь может выбрать
    конкретный вопрос и/или задать текст для поиска.
    """
    question = ModelChoiceField(
        queryset=Question.objects.all(),
        required=False,
        label='Filter by Question'
    )
    text_search = CharField(
        required=False,
        label='Search in Text Answers'
    )
