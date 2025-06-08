"""Models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, ForeignKey, CASCADE, PROTECT,
    TextChoices, ManyToManyField, UniqueConstraint, BooleanField, SlugField, Q, CheckConstraint, F, IntegerField
)
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from shared.django import BaseModel
from shared.django.models import TimeBaseModel
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


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

    telegram_topic_id = IntegerField(
        _('Telegram Topic ID'),
        help_text=_('The ID of the Telegram topic associated with this survey.')
    )


    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['is_default'],
                condition=Q(is_default=True),
                name='unique_default_survey',
                violation_error_message=_('Default survey already exists!')
            ),
        ]
        verbose_name = _('Survey')
        verbose_name_plural = _('Surveys')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from app.utils.telegram import (
            get_bot_instance,
            check_telegram_permissions_and_forum_status,
            create_telegram_forum_topic,
            edit_telegram_forum_topic
        )

        with transaction.atomic():
            is_new = not self.pk
            old_title = None
            if not is_new:
                # Retrieve the current title from DB for comparison later
                # This avoids using a potentially stale self.title if it was changed in memory before save
                try:
                    old_title = Survey.objects.get(pk=self.pk).title
                except Survey.DoesNotExist:
                    # This should ideally not happen if self.pk is set for an existing instance
                    # If it does, treat as if old_title couldn't be determined, effectively making title_changed=True if self.title is set
                    pass

            title_changed = not is_new and old_title != self.title

            # --- Default survey logic ---
            if self.is_default:
                Survey.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif is_new and not Survey.objects.filter(is_default=True).exists():
                self.is_default = True
            # --- End Default survey logic ---

            # --- Telegram Pre-Save Logic (Strict) ---
            bot = None
            chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
            telegram_enabled = getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False)
            run_telegram_logic = telegram_enabled and chat_id

            if run_telegram_logic:
                if not settings.TELEGRAM_BOT_TOKEN:
                    # Critical: Bot token must be configured
                    raise ValidationError(_("Telegram bot token (TELEGRAM_BOT_TOKEN) is not configured. Cannot manage topics."))

                try:
                    bot = async_to_sync(get_bot_instance)() # get_bot_instance itself checks token, but explicit check above is clearer
                    if not bot: # Should be caught by the check above, but as a safeguard
                        raise ValidationError(_("Failed to initialize Telegram bot. Token might be invalid or missing."))

                    # Permission checks are needed if it's a new survey or if the title of an existing survey changes
                    # (as topic creation/editing will occur)
                    if is_new or title_changed:
                        can_manage, perm_message = async_to_sync(check_telegram_permissions_and_forum_status)(bot, chat_id)
                        if not can_manage:
                            raise ValidationError(_("Telegram permission/forum status check failed: %(message)s") % {'message': perm_message})

                except ValidationError: # Re-raise validation errors from checks
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during Telegram pre-save checks for Survey '{self.title or 'new'}': {e}", exc_info=True)
                    raise ValidationError(_("An unexpected error occurred during Telegram pre-save checks: %(error)s") % {'error': str(e)})
            # --- End Telegram Pre-Save Logic ---

            super().save(*args, **kwargs) # Actual save to DB

            # --- Telegram Post-Save Logic (Strict) ---
            if run_telegram_logic: # 'bot' should be initialized if pre-save checks passed
                if not bot: # Should not happen if pre-save logic is correct, but as a failsafe
                    logger.error(f"Survey {self.pk} ('{self.title}') saved, but bot instance was unexpectedly None post-save. Skipping Telegram topic management.")
                    # This state indicates a flaw in pre-save logic or an unexpected issue.
                    # Depending on strictness, could raise an error here too, but pre-save should prevent this.
                    return

                try:
                    if is_new:
                        # For new surveys, topic creation is mandatory
                        new_topic_id = async_to_sync(create_telegram_forum_topic)(bot, chat_id, self.title)
                        if new_topic_id is None: # create_telegram_forum_topic returns None on failure
                            # This is a critical failure for a new survey as per requirements
                            raise ValidationError(
                                _("Survey was saved, but failed to create the required Telegram topic. "
                                  "The survey might be in an inconsistent state regarding Telegram integration. "
                                  "Please check Telegram bot permissions and chat settings.")
                            )

                        # Successfully created, update the instance and the DB record
                        # Use queryset.update to avoid recursion and re-triggering save signals
                        Survey.objects.filter(pk=self.pk).update(telegram_topic_id=new_topic_id)
                        self.telegram_topic_id = new_topic_id # Update the current instance field as well
                        logger.info(f"Survey {self.pk} ('{self.title}') created and Telegram topic ID {new_topic_id} assigned.")

                    elif title_changed:
                        # For existing surveys with a title change, topic editing is attempted.
                        # It's implied that self.telegram_topic_id MUST exist if it's not a new survey,
                        # because new surveys without successful topic creation would have raised ValidationError.
                        if not self.telegram_topic_id:
                            # This case should ideally not be reached if logic for new surveys is strict.
                            # It means an existing survey somehow has no topic ID, which is inconsistent.
                            raise ValidationError(
                                _("Survey title changed, but the survey (ID: %(survey_id)s) is missing a Telegram topic ID. "
                                  "Cannot update Telegram topic name. This indicates a potential data inconsistency.")
                                % {'survey_id': self.pk}
                            )

                        success = async_to_sync(edit_telegram_forum_topic)(bot, chat_id, self.telegram_topic_id, self.title)
                        if not success:
                            raise ValidationError(
                                _("Survey title was updated, but failed to update the corresponding Telegram topic name (Topic ID: %(topic_id)s). "
                                  "Please check Telegram bot permissions and chat settings.")
                                % {'topic_id': self.telegram_topic_id}
                            )
                        logger.info(f"Survey {self.pk} ('{self.title}') title updated and Telegram topic ID {self.telegram_topic_id} name updated.")

                except ValidationError: # Re-raise to ensure save transaction might be rolled back if supported
                    raise
                except Exception as e:
                    # Catch-all for other unexpected errors during post-save Telegram operations
                    logger.error(f"Unexpected error during post-save Telegram topic management for Survey {self.pk} ('{self.title}'): {e}", exc_info=True)
                    # This is tricky: the survey is saved, but Telegram failed. Raising ValidationError here
                    # might be too late for a clean rollback depending on DB and transaction handling.
                    # However, for strictness, we signal a failure.
                    raise ValidationError(
                        _("Survey was saved/updated, but an unexpected error occurred during subsequent Telegram topic management: %(error)s. "
                          "The survey's Telegram integration might be inconsistent.")
                        % {'error': str(e)}
                    )
            # --- End Telegram Post-Save Logic ---

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
        help_text=_('Survey this question belongs to')
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
        help_text=_('Survey this submission belongs to')
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
