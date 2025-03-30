"""Views for visa functionality."""
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.response import Response
from rest_framework.views import APIView

from app.serializers import (
    VisaStatusCheckInputSerializer,
    VisaStatusCheckResponseSerializer
)
from shared.django import VISA, RecaptchaPermission
from shared.parse import VisaSearchParams, KoreaVisaAPI


@extend_schema_view(
    post=extend_schema(
        summary=_("Check visa status"),
        description=_("""
Check visa application status using passport number, name and birth date.

**Possible Status Values:**
- `Approved`: Your visa has been approved
- `Application Received`: Your application has been received
- `Rejected`: Your application has been rejected
- `Under Review`: Your application is being reviewed
"""),
        request=VisaStatusCheckInputSerializer,
        responses={200: VisaStatusCheckResponseSerializer},
        tags=[VISA]
    )
)
class VisaStatusCheckAPIView(APIView):
    """API view for checking visa status."""
    permission_classes = [RecaptchaPermission]

    @staticmethod
    def post(request):
        """Handle POST request."""
        # print("Request body:", request.body)  # Логируем тело запроса
        # print("Request data:", request.data)  # Логируем данные запроса
        # print("Request POST:", request.POST)  # Логируем POST данные
        # print("Request content type:", request.content_type)  # Логируем тип контента

        # Validate input data
        serializer = VisaStatusCheckInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create search parameters
        search_params = VisaSearchParams(
            passport_number=data['passport_number'],
            english_name=data['english_name'],
            birth_date=data['birth_date'].strftime("%Y-%m-%d")
        )

        # Check visa status
        visa_api = KoreaVisaAPI()
        result = visa_api.check_visa_status(search_params)

        # Validate response data
        response_serializer = VisaStatusCheckResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.validated_data)
