"""Utilities for reCAPTCHA validation."""
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission


def verify_recaptcha(token):
    """
    Verify reCAPTCHA token.

    Args:
        token: The reCAPTCHA token to verify

    Raises:
        ValidationError: If token is invalid or the score is too low
    """
    # Skip verification in DEBUG mode
    if settings.DEBUG and not settings.RECAPTCHA_ENABLED:
        return True

    # Build request data
    data = {
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': token
    }

    # Make verification request
    response = urlopen('https://www.google.com/recaptcha/api/siteverify', urlencode(data).encode('utf-8'))
    result = json.loads(response.read().decode('utf-8'))

    # Check if verification succeeded
    if not result.get('success'):
        raise ValidationError(_('Invalid ReCaptcha'))

    # Check if score is high enough
    if result.get('score', 0) < settings.RECAPTCHA_REQUIRED_SCORE:
        raise ValidationError(_('ReCaptcha score too low'))

    return True


class RecaptchaPermission(BasePermission):
    """Permission class that verifies reCAPTCHA token."""

    def has_permission(self, request, view):
        """Check if request has valid reCAPTCHA token."""
        # Skip verification in DEBUG mode
        if settings.DEBUG and not settings.RECAPTCHA_ENABLED:
            return True

        # Get token from headers
        token = request.headers.get('X-Recaptcha-Token')
        if not token:
            raise ValidationError({'token': [_('ReCaptcha token is required')]})

        # Verify token
        verify_recaptcha(token)

        return True
