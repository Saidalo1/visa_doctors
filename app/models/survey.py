"""Models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, ForeignKey, CASCADE,
    TextChoices, JSONField
)
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from shared.django import BaseModel


class Question(BaseModel):
    """Survey question model."""

    class InputType(TextChoices):
        """Types of input for questions."""
        TEXT = 'text', _('Text')
        SINGLE_CHOICE = 'single_choice', _('Single Choice')
        MULTIPLE_CHOICE = 'multiple_choice', _('Multiple Choice')
        DATE = 'date', _('Date')
        FILE = 'file', _('File')

    description = TextField(_('Description'))
    input_type = CharField(
        _('Input Type'),
        max_length=20,
        choices=InputType.choices,
        default=InputType.TEXT
    )
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')


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

    class Meta:
        ordering = ['order']
        verbose_name = _('Answer Option')
        verbose_name_plural = _('Answer Options')

    class MPTTMeta:
        """MPTT model meta."""
        order_insertion_by = ['order']


class SurveySubmission(BaseModel):
    """Survey submission model."""

    class Status(TextChoices):
        """Status choices for survey submission."""
        NEW = 'new', _('New')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        REJECTED = 'rejected', _('Rejected')

    status = CharField(
        _('Status'),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )

    class Meta:
        verbose_name = _('Survey Submission')
        verbose_name_plural = _('Survey Submissions')


class Response(BaseModel):
    """Response model for survey questions."""
    submission = ForeignKey('app.SurveySubmission', CASCADE, related_name='responses')
    question = ForeignKey('app.Question', CASCADE, related_name='responses')
    answer = JSONField(_('Answer'))

    class Meta:
        verbose_name = _('Response')
        verbose_name_plural = _('Responses')
