from re import finditer, sub

from django.utils.html import strip_tags
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from app.models import (
    About, AboutHighlight, VisaType, VisaDocument,
    ResultCategory, Result, UniversityLogo
)


class AboutHighlightSerializer(ModelSerializer):
    """Serializer for AboutHighlight model."""

    class Meta:
        model = AboutHighlight
        fields = 'title',


class AboutPreviewSerializer(ModelSerializer):
    """Serializer for About model with preview description."""
    highlights = AboutHighlightSerializer(many=True, read_only=True)
    preview_description = SerializerMethodField()

    class Meta:
        model = About
        fields = 'title', 'subtitle', 'preview_description', 'slug', 'experience_years', 'highlights'

    @staticmethod
    def get_preview_description(obj) -> str:
        """Get first ~622 characters of description until the end of a sentence."""

        # Strip HTML tags
        text = strip_tags(obj.description)

        # Remove extra whitespace
        text = sub(r'\s+', ' ', text).strip()

        # If text is shorter than 622 characters, return it all
        if len(text) <= 622:
            return text

        # Find the last sentence end within the first 622 characters
        end_pos = 0
        for match in finditer(r'[.!?](\s|$)', text[:622]):
            end_pos = match.end()

        # If no sentence end found, just cut at 622
        if end_pos == 0:
            end_pos = 622

        return text[:end_pos].strip()


class AboutDetailSerializer(ModelSerializer):
    """Serializer for About model with full description."""

    class Meta:
        model = About
        fields = 'title', 'subtitle', 'description', 'slug'


class VisaTypeListSerializer(ModelSerializer):
    """Serializer for VisaType model list."""

    class Meta:
        model = VisaType
        fields = 'title', 'slug', 'icon'


class VisaDocumentSerializer(ModelSerializer):
    """Serializer for VisaDocument model."""

    class Meta:
        model = VisaDocument
        fields = 'description', 'order'


class VisaTypeDetailSerializer(ModelSerializer):
    """Serializer for VisaType model with documents."""
    documents = VisaDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VisaType
        fields = 'title', 'slug', 'icon', 'documents'


class ResultSerializer(ModelSerializer):
    """Serializer for Result model."""

    class Meta:
        model = Result
        fields = 'image',


class ResultCategoryPreviewSerializer(ModelSerializer):
    """Serializer for ResultCategory model with limited results."""
    preview_results = SerializerMethodField()

    class Meta:
        model = ResultCategory
        fields = 'title', 'subtitle', 'description', 'preview_results'

    @extend_schema_field(ResultSerializer(many=True))
    def get_preview_results(self, obj):
        """Get first 6 results."""
        results = obj.results.all()[:6]
        return ResultSerializer(results, many=True).data


class ResultCategoryDetailSerializer(ModelSerializer):
    """Serializer for ResultCategory model with all results."""
    results = ResultSerializer(many=True, read_only=True)

    class Meta:
        model = ResultCategory
        fields = 'title', 'subtitle', 'results'


class UniversityLogoSerializer(ModelSerializer):
    """Serializer for UniversityLogo model."""

    class Meta:
        model = UniversityLogo
        fields = 'name', 'logo'
