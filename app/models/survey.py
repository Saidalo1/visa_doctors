"""Models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, ForeignKey, CASCADE,
    TextChoices, ManyToManyField, UniqueConstraint, Q, CheckConstraint,
    BooleanField
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

    title = CharField(_('Question title'), max_length=255)
    placeholder = CharField(_('Placeholder'), max_length=255, blank=True, null=True)

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
        
    def __str__(self):
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
    has_custom_input = BooleanField(_('Has Custom Input'), default=False, help_text=_('Allow custom text input for this option'))

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
        
    def __str__(self):
        return f"Submission {self.id} - {self.get_status_display()}"


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
        
    def __str__(self):
        if self.question.input_type == self.question.InputType.TEXT:
            return f"Text Response: {self.text_answer[:50]}..."
        return f"Options Response: {', '.join(str(opt) for opt in self.selected_options.all())}"
