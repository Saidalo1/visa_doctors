"""Status models for survey functionality."""

from django.db.models import (
    CharField, TextField, PositiveIntegerField, BooleanField, PROTECT
)
from django.utils.translation import gettext_lazy as _

from shared.django import BaseModel


class SubmissionStatus(BaseModel):
    """Status model for submissions.
    
    Allows dynamic management of submission statuses through the admin interface.
    """
    name = CharField(
        _('Name'), 
        max_length=100,
        help_text=_('Name of the status shown to users')
    )
    code = CharField(
        _('Code'), 
        max_length=50, 
        unique=True, 
        help_text=_('Unique code for programmatic usage')
    )
    description = TextField(
        _('Description'),
        blank=True,
        help_text=_('Description of the status and when it should be used')
    )
    color = CharField(
        _('Color'), 
        max_length=20, 
        blank=True, 
        help_text=_('CSS color code for display (e.g., #FF5733)')
    )
    order = PositiveIntegerField(
        _('Order'), 
        default=0,
        help_text=_('Display order in status lists')
    )
    is_default = BooleanField(
        _('Is Default'), 
        default=False,
        help_text=_('Default status for new submissions (only one can be default)')
    )
    is_final = BooleanField(
        _('Is Final'), 
        default=False,
        help_text=_('Whether this status is final (submission is closed)')
    )
    active = BooleanField(
        _('Active'), 
        default=True,
        help_text=_('Whether this status is active for selection')
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = _('Submission Status')
        verbose_name_plural = _('Submission Statuses')
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        """Override save method to ensure uniqueness of default status."""
        # If this status is set as default, remove default flag from all others
        if self.is_default:
            SubmissionStatus.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
