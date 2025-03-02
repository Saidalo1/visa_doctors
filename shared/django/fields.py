"""Custom model fields."""
import os
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import FileField
from django.utils.translation import gettext_lazy as _


def validate_svg(value):
    """Validate that uploaded file is SVG."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.svg':
        raise ValidationError(_('Only SVG files are allowed.'))

    # Basic SVG validation - check if file starts with SVG tag
    try:
        if hasattr(value, 'temporary_file_path'):
            with open(value.temporary_file_path(), 'r') as f:
                content = f.read().lower()
        else:
            content = value.read().decode('utf-8').lower()
            value.seek(0)  # Reset file pointer
            
        if not (content.startswith('<?xml') or content.startswith('<svg')):
            raise ValidationError(_('File is not a valid SVG image.'))
    except (UnicodeDecodeError, AttributeError, IOError):
        raise ValidationError(_('File is not a valid SVG image.'))


class SVGFileField(FileField):
    """Custom field for SVG files."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(validate_svg)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
