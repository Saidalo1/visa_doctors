"""Models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, ForeignKey, CASCADE,
    TextChoices, ManyToManyField, UniqueConstraint, Q, CheckConstraint
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

    # For answer options (single/multiple choice)
    selected_options = ManyToManyField(
        'app.AnswerOption',
        related_name='responses',
        blank=True,
        verbose_name=_('Selected options')
    )

    # For text answers
    text_answer = TextField(_('Text answer'), blank=True, null=True)

    class Meta:
        verbose_name = _('Response')
        verbose_name_plural = _('Responses')
        constraints = [
            # Ensure one response per question per submission
            UniqueConstraint(
                fields=['submission', 'question'],
                name='unique_response_per_question'
            ),
            # Ensure text answer for text questions
            # CheckConstraint(
            #     check=Q(
            #         Q(question__input_type='text', text_answer__isnull=False) |
            #         ~Q(question__input_type='text')
            #     ),
            #     name='text_answer_required_for_text_questions'
            # ),
            # # Ensure selected options for choice questions
            # CheckConstraint(
            #     check=Q(
            #         Q(question__input_type__in=['single_choice', 'multiple_choice']) |
            #         ~Q(selected_options__isnull=True)
            #     ),
            #     name='options_required_for_choice_questions'
            # )
        ]
