"""Models for static pages like About, Results, Contacts, and Visas."""

from django.db.models import TextField, CharField, PositiveIntegerField, ForeignKey, CASCADE, \
    SlugField, SET_NULL, EmailField, URLField, ImageField
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field
from django.core.exceptions import ValidationError

from shared.django import BaseModel
from shared.django.fields import SVGFileField
from app.fields import ExperienceYearField


class About(BaseModel):
    """About page model. Only one instance should exist."""
    title = CharField(_('Title'), max_length=255)
    subtitle = CharField(_('Subtitle'), max_length=255)
    description = CKEditor5Field(_('Description'))
    # image = ImageField(_('Image'), upload_to='about/')
    experience_years = ExperienceYearField(
        _('Experience Years'),
        help_text=_('Enter years of experience and title (e.g., {"years": 28, "title": "Years of Medical Practice"})')
    )
    slug = SlugField(_('Slug'), unique=True)

    class Meta:
        ordering = ['id']
        verbose_name = _('About')
        verbose_name_plural = _('About')
        
    def __str__(self):
        return self.title


class AboutHighlight(BaseModel):
    """Highlights for About page."""
    about = ForeignKey('app.About', CASCADE, related_name='highlights')
    title = CharField(_('Title'), max_length=255)
    # description = TextField(_('Description'))
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('About Highlight')
        verbose_name_plural = _('About Highlights')
        
    def __str__(self):
        return f"{self.about.title} - {self.title}"


class VisaType(BaseModel):
    """Visa type model."""
    title = CharField(_('Title'), max_length=255)
    slug = SlugField(_('Slug'), unique=True)
    icon = SVGFileField(_('Icon'), upload_to='visas/icons/', help_text=_('Upload SVG icon'))
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Visa Type')
        verbose_name_plural = _('Visa Types')
        
    def __str__(self):
        return self.title


class VisaDocument(BaseModel):
    """Required documents for visa types."""
    visa_type = ForeignKey('app.VisaType', CASCADE, related_name='documents')
    title = TextField(_('Title'))
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Visa Document')
        verbose_name_plural = _('Visa Documents')
        
    def __str__(self):
        return f"{self.visa_type.title} - Document {self.order}"


class ResultCategory(BaseModel):
    """Category for results. Only one instance should exist."""
    title = CharField(_('Title'), max_length=255)
    subtitle = CharField(_('Subtitle'), max_length=255, blank=True)
    description = CKEditor5Field(_('Description'), blank=True)

    class Meta:
        verbose_name = _('Result Category')
        verbose_name_plural = _('Result Categories')
        
    def __str__(self):
        return self.title


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
        
    def __str__(self):
        return f"Result {self.id} - {self.category.title if self.category else 'No Category'}"


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
        
    def __str__(self):
        return f"{self.phone} - {self.email}"


class UniversityLogo(BaseModel):
    """University logo model."""
    name = CharField(_('University Name'), max_length=255)
    logo = ImageField(_('Logo'), upload_to='universities/logos/')
    order = PositiveIntegerField(_('Order'), default=0, db_index=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = _('University Logo')
        verbose_name_plural = _('University Logos')
        
    def __str__(self):
        return self.name
