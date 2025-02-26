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
