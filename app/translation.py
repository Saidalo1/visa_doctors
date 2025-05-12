"""Translation configuration for app models."""
from modeltranslation.translator import register, TranslationOptions

from app.models import (
    About, AboutHighlight, VisaType, VisaDocument, ResultCategory, ContactInfo, UniversityLogo, Question, AnswerOption,
    InputFieldType, SubmissionStatus
)


@register(About)
class AboutTranslationOptions(TranslationOptions):
    """Translation options for About model."""
    fields = 'title', 'subtitle', 'description', 'experience_years'

@register(SubmissionStatus)
class SubmissionStatusTranslationOptions(TranslationOptions):
    """Translation options for SubmissionStatus model."""
    fields = 'name',


@register(AboutHighlight)
class AboutHighlightTranslationOptions(TranslationOptions):
    """Translation options for AboutHighlight model."""
    fields = 'title',


@register(VisaType)
class VisaTypeTranslationOptions(TranslationOptions):
    """Translation options for VisaType model."""
    fields = 'title',


@register(VisaDocument)
class VisaDocumentTranslationOptions(TranslationOptions):
    """Translation options for VisaDocument model."""
    fields = 'title',


@register(ResultCategory)
class ResultCategoryTranslationOptions(TranslationOptions):
    """Translation options for ResultCategory model."""
    fields = 'title', 'subtitle', 'description'


@register(ContactInfo)
class ContactInfoTranslationOptions(TranslationOptions):
    """Translation options for ContactInfo model."""
    fields = 'address',


@register(UniversityLogo)
class UniversityLogoTranslationOptions(TranslationOptions):
    """Translation options for UniversityLogo model."""
    fields = 'name',


@register(Question)
class QuestionTranslationOptions(TranslationOptions):
    """Translation options for Question model."""
    fields = 'title', 'placeholder'


@register(AnswerOption)
class AnswerOptionTranslationOptions(TranslationOptions):
    """Translation options for AnswerOption model."""
    fields = 'text',


@register(InputFieldType)
class InputFieldTypeTranslationOptions(TranslationOptions):
    """Translation options for InputFieldType model."""
    fields = 'title', 'error_message'
