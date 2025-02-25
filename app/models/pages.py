"""Models for static pages like About, Results, Contacts, and Visas."""

from django.db.models import TextField, CharField, PositiveIntegerField, ForeignKey, CASCADE, \
    ImageField, JSONField, SlugField, SET_NULL, EmailField, URLField
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from shared.django import BaseModel


class About(BaseModel):
    """About page model."""
    title = CharField(_('Title'), max_length=255)
    subtitle = CharField(_('Subtitle'), max_length=255)
    description = CKEditor5Field(_('Description'))
    image = ImageField(_('Image'), upload_to='about/')
    experience_years = JSONField(_('Experience Years'))
    slug = SlugField(_('Slug'), unique=True)

    class Meta:
        ordering = ['id']
        verbose_name = _('About')
        verbose_name_plural = _('About')


class AboutHighlight(BaseModel):
    """Highlights for About page."""
    about = ForeignKey('app.About', CASCADE, related_name='highlights')
    title = CharField(_('Title'), max_length=255)
    description = TextField(_('Description'))
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('About Highlight')
        verbose_name_plural = _('About Highlights')


class VisaType(BaseModel):
    """Visa type model."""
    title = CharField(_('Title'), max_length=255)
    slug = SlugField(_('Slug'), unique=True)
    icon = ImageField(_('Icon'), upload_to='visas/icons/')

    class Meta:
        ordering = ['id']
        verbose_name = _('Visa Type')
        verbose_name_plural = _('Visa Types')


class VisaDocument(BaseModel):
    """Required documents for visa types."""
    visa_type = ForeignKey('app.VisaType', CASCADE, related_name='documents')
    description = TextField(_('Description'))
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Visa Document')
        verbose_name_plural = _('Visa Documents')


class ResultCategory(BaseModel):
    """Category for results."""
    title = CharField(_('Title'), max_length=255)

    class Meta:
        verbose_name = _('Result Category')
        verbose_name_plural = _('Result Categories')


class Result(BaseModel):
    """Results model."""
    image = ImageField(_('Image'), upload_to='results/')
    category = ForeignKey(
        'app.ResultCategory',
        SET_NULL,
        null=True,
        blank=True,
        related_name='results'
    )

    class Meta:
        verbose_name = _('Result')
        verbose_name_plural = _('Results')


class ContactInfo(BaseModel):
    """Contact information model."""
    phone = CharField(_('Phone'), max_length=20)
    email = EmailField(_('Email'))
    address = TextField(_('Address'), blank=True)
    telegram = URLField(_('Telegram'), blank=True)
    instagram = URLField(_('Instagram'), blank=True)
    facebook = URLField(_('Facebook'), blank=True)
    youtube = URLField(_('YouTube'), blank=True)

    class Meta:
        verbose_name = _('Contact Information')
        verbose_name_plural = _('Contact Information')
