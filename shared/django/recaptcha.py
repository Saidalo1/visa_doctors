"""ReCaptcha permissions and utilities."""
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission


def verify_recaptcha(token):
    """Verify ReCaptcha token with Google API."""
    response = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': token,
        }
    )
    result = response.json()

    if not result['success']:
        raise ValidationError('Invalid ReCaptcha')

    # For v3, we should also check the score
    if 'score' in result and result['score'] < settings.RECAPTCHA_REQUIRED_SCORE:
        raise ValidationError('ReCaptcha score too low')

    return result


class RecaptchaPermission(BasePermission):
    """Permission class to require ReCaptcha validation for POST requests."""

    def has_permission(self, request, view):
        """Check ReCaptcha token for POST requests."""
        # Get token from headers
        token = request.headers.get('X-Recaptcha-Token')
        if not token:
            raise ValidationError({'token': ['ReCaptcha token is required']})

        # Verify token
        verify_recaptcha(token)
        return True
