from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import RetrieveAPIView, ListAPIView
from django.utils.translation import gettext_lazy as _

from app.models.pages import About, VisaType, ResultCategory, UniversityLogo, ContactInfo
from app.serializers.pages import (
    AboutPreviewSerializer, AboutDetailSerializer,
    VisaTypeListSerializer, VisaTypeDetailSerializer,
    ResultCategoryPreviewSerializer, ResultCategoryDetailSerializer,
    UniversityLogoSerializer, ContactInfoSerializer
)
from shared.django import ABOUT, VISA, RESULTS, UNIVERSITIES


@extend_schema_view(
    get=extend_schema(
        summary=_("Get about page preview"),
        description=_("Returns about page with preview description and highlights"),
        tags=[ABOUT]
    )
)
class AboutPreviewAPIView(RetrieveAPIView):
    """API view for About model with preview description."""
    queryset = About.objects.prefetch_related('highlights')
    serializer_class = AboutPreviewSerializer

    def get_object(self):
        """Return the first About instance."""
        return self.get_queryset().first()


@extend_schema_view(
    get=extend_schema(
        summary=_("Get about page detail"),
        description=_("Returns about page with full description"),
        tags=[ABOUT]
    )
)
class AboutDetailAPIView(RetrieveAPIView):
    """API view for About model with full description."""
    queryset = About.objects.all()
    serializer_class = AboutDetailSerializer
    
    def get_object(self):
        """Return the first About instance."""
        return self.get_queryset().first()


@extend_schema_view(
    get=extend_schema(
        summary=_("Get visa types list"),
        description=_("Returns list of visa types with basic info"),
        tags=[VISA]
    )
)
class VisaTypeListAPIView(ListAPIView):
    """API view for VisaType model list."""
    queryset = VisaType.objects.all()
    serializer_class = VisaTypeListSerializer


@extend_schema_view(
    get=extend_schema(
        summary=_("Get visa type detail"),
        description=_("Returns visa type with documents"),
        tags=[VISA]
    )
)
class VisaTypeDetailAPIView(RetrieveAPIView):
    """API view for VisaType model with documents."""
    queryset = VisaType.objects.prefetch_related('documents')
    serializer_class = VisaTypeDetailSerializer
    lookup_field = 'slug'


@extend_schema_view(
    get=extend_schema(
        summary=_("Get result category preview"),
        description=_("Returns result category with first 6 results"),
        tags=[RESULTS]
    )
)
class ResultCategoryPreviewAPIView(RetrieveAPIView):
    """API view for ResultCategory model with limited results."""
    queryset = ResultCategory.objects.prefetch_related('results')
    serializer_class = ResultCategoryPreviewSerializer
    
    def get_object(self):
        """Return the first ResultCategory instance."""
        return self.get_queryset().first()


@extend_schema_view(
    get=extend_schema(
        summary=_("Get result category detail"),
        description=_("Returns result category with all results"),
        tags=[RESULTS]
    )
)
class ResultCategoryDetailAPIView(RetrieveAPIView):
    """API view for ResultCategory model with all results."""
    queryset = ResultCategory.objects.prefetch_related('results')
    serializer_class = ResultCategoryDetailSerializer
    
    def get_object(self):
        """Return the first ResultCategory instance."""
        return self.get_queryset().first()


@extend_schema_view(
    get=extend_schema(
        summary=_("Get university logos"),
        description=_("Returns list of university logos"),
        tags=[UNIVERSITIES]
    )
)
class UniversityLogoListAPIView(ListAPIView):
    """API view for UniversityLogo model list."""
    queryset = UniversityLogo.objects.all()
    serializer_class = UniversityLogoSerializer


@extend_schema_view(
    get=extend_schema(
        summary=_("Get contact information"),
        description=_("Returns contact information"),
        tags=[UNIVERSITIES]
    )
)
class ContactInfoAPIView(RetrieveAPIView):
    """API view for ContactInfo model."""
    queryset = ContactInfo.objects.all()
    serializer_class = ContactInfoSerializer

    def get_object(self):
        """Return the first ContactInfo instance."""
        return self.get_queryset().first()
