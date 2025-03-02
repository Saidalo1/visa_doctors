"""Custom model fields."""
import os
from django.core.exceptions import ValidationError
from django.db.models import ImageField
from django.utils.translation import gettext_lazy as _


def validate_svg(value):
    """Validate that uploaded file is SVG."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.svg':
        raise ValidationError(_('File type is not supported. Only SVG files are allowed.'))

    # Basic SVG validation - check if file starts with SVG tag
    try:
        content = value.read().decode('utf-8').strip().lower()
        if not content.startswith('<?xml') and not content.startswith('<svg'):
            raise ValidationError(_('File is not a valid SVG image.'))
        value.seek(0)  # Reset file pointer
    except (UnicodeDecodeError, AttributeError):
        raise ValidationError(_('File is not a valid SVG image.'))


class SVGImageField(ImageField):
    """Custom field for SVG images."""
    def __init__(self, *args, **kwargs):
        kwargs['validators'] = [validate_svg]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if 'validators' in kwargs:
            del kwargs['validators']
        return name, path, args, kwargs
