"""Base models for the project."""
from django.db.models import DateTimeField, Model
from django.utils.translation import gettext_lazy as _
from safedelete.models import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel


class TimeBaseModel(Model):
    """Base model with timestamps."""
    created_at = DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SafeDeleteBaseModel(SafeDeleteModel):
    """Base model with safe delete functionality."""
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Meta:
        abstract = True


class BaseModel(TimeBaseModel, SafeDeleteBaseModel):
    """Base model with timestamps and safe delete functionality."""

    class Meta:
        abstract = True
