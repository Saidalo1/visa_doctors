from modeltranslation.translator import register, TranslationOptions

from app.models import (
    About, AboutHighlight, VisaType, VisaDocument, ResultCategory, ContactInfo, UniversityLogo, Question, AnswerOption
)


@register(About)
class AboutTranslationOptions(TranslationOptions):
    """Translation options for About model."""
    fields = 'title', 'subtitle', 'description'


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
    fields = 'description',


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
