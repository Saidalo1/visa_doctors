from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class ExperienceYearWidget(forms.MultiWidget):
    """Custom widget for experience years input."""
    
    def __init__(self, attrs=None):
        widgets = (
            forms.NumberInput(attrs={'placeholder': _('Years of experience'), 'class': 'form-control'}),
            forms.TextInput(attrs={'placeholder': _('Title'), 'class': 'form-control'})
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """Convert JSON value to list of values for widget."""
        if value:
            try:
                return [value.get('years'), value.get('title')]
            except (AttributeError, KeyError):
                return [None, None]
        return [None, None]


class ExperienceYearFormField(forms.MultiValueField):
    """Form field for experience years input."""
    widget = ExperienceYearWidget

    def __init__(self, **kwargs):
        # Remove JSON-specific kwargs that we don't need
        kwargs.pop('encoder', None)
        kwargs.pop('decoder', None)
        
        fields = (
            forms.IntegerField(
                min_value=0,
                max_value=100,
                error_messages={
                    'min_value': _('Years cannot be negative'),
                    'max_value': _('Years cannot exceed 100'),
                }
            ),
            forms.CharField(max_length=255)
        )
        super().__init__(fields, require_all_fields=True, **kwargs)

    def compress(self, data_list):
        """Convert widget values to JSON format."""
        if data_list and all(data_list):
            return {'years': data_list[0], 'title': data_list[1]}
        return None


class ExperienceYearField(models.JSONField):
    """Custom JSON field for storing experience years data with validation."""
    
    def formfield(self, **kwargs):
        defaults = {'form_class': ExperienceYearFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def validate(self, value, model_instance):
        """Validate the JSON structure."""
        super().validate(value, model_instance)
        
        if not isinstance(value, dict):
            raise ValidationError(_('Value must be a dictionary'))
        
        if 'years' not in value or 'title' not in value:
            raise ValidationError(_('Both "years" and "title" are required'))
            
        if not isinstance(value['years'], int):
            raise ValidationError(_('Years must be an integer'))
            
        if not isinstance(value['title'], str):
            raise ValidationError(_('Title must be a string'))
            
        if value['years'] < 0 or value['years'] > 100:
            raise ValidationError(_('Years must be between 0 and 100'))
            
        if len(value['title']) > 255:
            raise ValidationError(_('Title cannot be longer than 255 characters'))


class FrontContentWidget(forms.MultiWidget):
    """Custom widget for frontend title and subtitle input."""

    def __init__(self, attrs=None):
        widgets = (
            forms.TextInput(attrs={'placeholder': _('Frontend Title'), 'class': 'form-control'}),
            forms.TextInput(attrs={'placeholder': _('Frontend Subtitle'), 'class': 'form-control'})
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """Convert JSON value to list of values for widget."""
        if isinstance(value, dict):
            return [value.get('front_title'), value.get('front_subtitle')]
        return [None, None]


class FrontContentFormField(forms.MultiValueField):
    """Form field for frontend title and subtitle input."""
    widget = FrontContentWidget

    def __init__(self, **kwargs):
        kwargs.pop('encoder', None)
        kwargs.pop('decoder', None)

        fields = (
            forms.CharField(max_length=255, required=False),
            forms.CharField(max_length=255, required=False)
        )
        super().__init__(fields, require_all_fields=False, **kwargs)

    def compress(self, data_list):
        """Convert widget values to JSON format."""
        if data_list:
            return {'front_title': data_list[0] or '', 'front_subtitle': data_list[1] or ''}
        return {}


class FrontContentField(models.JSONField):
    """Custom JSON field for storing frontend content with a proper admin widget."""

    def formfield(self, **kwargs):
        defaults = {'form_class': FrontContentFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def validate(self, value, model_instance):
        """Validate the JSON structure."""
        super().validate(value, model_instance)

        if not isinstance(value, dict):
            raise ValidationError(_('Value must be a dictionary'))

        front_title = value.get('front_title')
        front_subtitle = value.get('front_subtitle')

        if front_title and not isinstance(front_title, str):
            raise ValidationError(_('Frontend title must be a string'))
        if front_subtitle and not isinstance(front_subtitle, str):
            raise ValidationError(_('Frontend subtitle must be a string'))

        if front_title and len(front_title) > 255:
            raise ValidationError(_('Frontend title cannot be longer than 255 characters'))
        if front_subtitle and len(front_subtitle) > 255:
            raise ValidationError(_('Frontend subtitle cannot be longer than 255 characters'))
