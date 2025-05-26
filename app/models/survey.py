"""Models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, ForeignKey, CASCADE, PROTECT,
    TextChoices, ManyToManyField, UniqueConstraint, BooleanField, SlugField
)
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from django.urls import reverse
from shared.django import BaseModel
from shared.django.models import TimeBaseModel


class InputFieldType(BaseModel):
    """Input field type model for custom validation."""

    class FieldTypeChoice(TextChoices):
        """Types of field for filtering and export."""
        STRING = 'string', _('String')
        NUMBER = 'number', _('Number')
        CHOICES = 'choices', _('Choices')

    title = CharField(_('Field Type Name'), max_length=100)
    field_key = CharField(_('Field key for export'), max_length=100, blank=True,
                          help_text=_('Short title used in exports'))
    field_type_choice = CharField(
        _('Field type for filtering'),
        max_length=20,
        choices=FieldTypeChoice.choices,
        default=FieldTypeChoice.STRING,
        help_text=_('Determines how this field is filtered in exports')
    )
    regex_pattern = CharField(
        _('Regular Expression Pattern'),
        max_length=255,
        help_text=_('Regular expression pattern for field validation'),
        blank=True
    )
    error_message = CharField(
        _('Error Message'),
        max_length=255,
        help_text=_('Error message to display when validation fails')
    )

    class Meta:
        verbose_name = _('Input Field Type')
        verbose_name_plural = _('Input Field Types')

    def __str__(self):
        """Return string representation."""
        return self.title


class Survey(TimeBaseModel):
    """Survey/Questionnaire model."""
    title = CharField(_('Survey title'), max_length=255)
    description = TextField(_('Description'), blank=True, null=True)
    slug = SlugField(
        _('URL Slug'), 
        max_length=100, 
        unique=True,
        help_text=_('URL-friendly name for the survey (used in frontend URLs)')
    )
    is_active = BooleanField(_('Is active'), default=True)
    is_default = BooleanField(
        _('Is default survey'), 
        default=False,
        help_text=_('If True, this survey will be used when no specific survey is selected')
    )
    
    class Meta:
        verbose_name = _('Survey')
        verbose_name_plural = _('Surveys')
        
    def __str__(self):
        return self.title
        
    def save(self, *args, **kwargs):
        # Ensure only one default survey exists
        if self.is_default:
            Survey.objects.filter(is_default=True).update(is_default=False)
        # If no default exists, make this one default
        elif not Survey.objects.filter(is_default=True).exists() and not self.pk:
            self.is_default = True
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('survey:survey-detail', kwargs={'slug': self.slug})


class Question(BaseModel):
    """Survey question model."""

    class InputType(TextChoices):
        """Types of input for questions."""
        TEXT = 'text', _('Text')
        SINGLE_CHOICE = 'single_choice', _('Single Choice')
        MULTIPLE_CHOICE = 'multiple_choice', _('Multiple Choice')

    title = CharField(_('Question title'), max_length=255)
    placeholder = CharField(_('Placeholder'), max_length=255, blank=True, null=True)
    is_required = BooleanField(_('Is required'), default=True)

    input_type = CharField(
        _('Input Type'),
        max_length=20,
        choices=InputType.choices,
        default=InputType.TEXT
    )
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)
    survey = ForeignKey(
        'app.Survey',
        on_delete=CASCADE,
        related_name='questions',
        verbose_name=_('Survey'),
        help_text=_('Survey this question belongs to'),
        null=True,
        blank=True
    )
    field_type = ForeignKey(
        'app.InputFieldType',
        null=True,
        blank=True,
        on_delete=CASCADE,
        related_name='questions',
        help_text=_('Field type for validation (only applicable for text questions)')
    )

    class Meta:
        ordering = ['survey', 'order']
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')

    def __str__(self):
        """Return string representation."""
        return f"{self.title} ({self.get_input_type_display()})"


class AnswerOption(MPTTModel, BaseModel):
    """Answer option model with tree structure."""
    question = ForeignKey('app.Question', CASCADE, related_name='options')
    text = CharField(_('Text'), max_length=255)
    parent = TreeForeignKey(
        'self',
        CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)
    is_selectable = BooleanField(_('Is Selectable'), default=True)
    has_custom_input = BooleanField(
        _('Has Custom Input'),
        default=False,
        help_text=_('Allow custom text input for this option')
    )
    export_field_name = CharField(
        blank=True,
        help_text="Short name to use in exports instead of full text",
        max_length=100,
        null=True,
        verbose_name="Export Field Name")

    class Meta:
        ordering = ['order']
        verbose_name = _('Answer Option')
        verbose_name_plural = _('Answer Options')

    class MPTTMeta:
        """MPTT model meta."""
        order_insertion_by = ['order']

    def __str__(self):
        return self.text


class SurveySubmission(BaseModel):
    """Survey submission model."""

    class StatusChoices(TextChoices):
        """Status choices for survey submission."""
        NEW = 'new', _('New')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        REJECTED = 'rejected', _('Rejected')

    class Source(TextChoices):
        """Source choices for survey submission."""
        WEBSITE = 'website', _('Website')
        FACEBOOK = 'facebook', _('Facebook')
        INSTAGRAM = 'instagram', _('Instagram')
        TELEGRAM = 'telegram', _('Telegram')
        WHATSAPP = 'whatsapp', _('WhatsApp')
        VK = 'vk', _('VKontakte')
        YOUTUBE = 'youtube', _('YouTube')
        LINKEDIN = 'linkedin', _('LinkedIn')
        TWITTER = 'twitter', _('Twitter')
        TIKTOK = 'tiktok', _('TikTok')
        OTHER = 'other', _('Other')

    survey = ForeignKey(
        'app.Survey',
        verbose_name=_('Survey'),
        on_delete=PROTECT,  # Защита от удаления опросника с ответами
        related_name='submissions',
        help_text=_('Survey this submission belongs to'),
        null=True,
        blank=True
    )
    
    # Поле status теперь связано с моделью SubmissionStatus вместо использования фиксированных вариантов
    status = ForeignKey(
        'app.SubmissionStatus',
        verbose_name=_('Status'),
        on_delete=PROTECT,  # Защита от удаления используемых статусов
        related_name='submissions',
        to_field='code',  # Связь по коду статуса для совместимости с существующим кодом
        help_text=_('Статус заявки')
    )

    source = CharField(
        _('Source'),
        max_length=20,
        choices=Source.choices,
        default=Source.WEBSITE,
        help_text=_('Where did the user come from?')
    )

    comment = TextField(
        _('Comment'),
        blank=True,
        null=True,
        help_text=_('Comment about this submission')
    )

    class Meta:
        verbose_name = _('Survey Submission')
        verbose_name_plural = _('Survey Submissions')

    def __str__(self):
        return f"Submission {self.id} - {self.status}"


class Response(BaseModel):
    """Response model for survey questions."""
    submission = ForeignKey('app.SurveySubmission', CASCADE, related_name='responses', db_index=True)
    question = ForeignKey('app.Question', CASCADE, related_name='responses', db_index=True)

    # For answer options (single/multiple choice)
    selected_options = ManyToManyField(
        'app.AnswerOption',
        related_name='responses',
        blank=True,
        verbose_name=_('Selected options'),
        db_index=True
    )

    # For text answers
    text_answer = TextField(_('Text answer'), blank=True, null=True)

    class Meta:
        verbose_name = _('Response')
        verbose_name_plural = _('Responses')
        index_together = 'submission', 'question'
        constraints = [
            # Ensure one response per question per submission
            UniqueConstraint(
                fields=['submission', 'question'],
                name='unique_response_per_question'
            )
        ]
        
    def clean(self):
        """Validate that the question belongs to the submission's survey."""
        from django.core.exceptions import ValidationError
        # Проверяем только если у обоих объектов указан опросник
        if self.question.survey_id and self.submission.survey_id and self.question.survey_id != self.submission.survey_id:
            raise ValidationError({
                'question': _('Question must belong to the same survey as the submission')
            })

    def __str__(self):
        if self.question.input_type == self.question.InputType.TEXT:
            return f"Text Response: {self.text_answer[:50]}..."
        return f"Options Response: {', '.join(str(opt) for opt in self.selected_options.all())}"
