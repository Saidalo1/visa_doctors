"""Serializers for visa functionality."""
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, DateField
from rest_framework.serializers import Serializer


class VisaStatusCheckInputSerializer(Serializer):
    """Serializer for visa status check input."""
    passport_number = CharField(
        max_length=20,
        help_text=_("Passport number")
    )
    english_name = CharField(
        max_length=255,
        help_text=_("Full name in English")
    )
    birth_date = DateField(
        help_text=_("Date of birth in YYYY-MM-DD format")
    )

    @staticmethod
    def validate_birth_date(value):
        """Validate birthdate."""
        if value > datetime.now().date():
            raise ValidationError(_("Birth date cannot be in the future"))
        return value

    @staticmethod
    def validate_passport_number(value):
        """Validate passport number."""
        if not value.isalnum():
            raise ValidationError(_("Passport number must contain only letters and numbers"))
        return value.upper()


class VisaDataSerializer(Serializer):
    """Serializer for visa data response."""
    application_number = CharField(
        required=False,
        help_text=_("Application number")
    )
    application_date = CharField(
        required=False,
        help_text=_("Application submission date")
    )
    entry_purpose = CharField(
        required=False,
        help_text=_("Purpose of entry")
    )
    progress_status = CharField(
        required=False,
        help_text=_("Current status in Korean")
    )
    status_en = CharField(
        required=False,
        help_text=_("Current status in English")
    )
    visa_type = CharField(
        required=False,
        help_text=_("Type of visa")
    )
    stay_qualification = CharField(
        required=False,
        help_text=_("Stay qualification")
    )
    expiry_date = CharField(
        required=False,
        help_text=_("Visa expiry date")
    )
    rejection_reason = CharField(
        required=False,
        help_text=_("Rejection reason if application was rejected")
    )


class VisaStatusCheckResponseSerializer(Serializer):
    """Serializer for visa status check response."""
    status = CharField(
        help_text=_("Response status (success/error)")
    )
    visa_data = VisaDataSerializer(
        required=False,
        help_text=_("Visa application data")
    ) 