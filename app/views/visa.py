"""Views for visa functionality."""
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.http import HttpResponse
from rest_framework.exceptions import APIException
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
import requests

from app.serializers import (
    VisaStatusCheckInputSerializer,
    VisaStatusCheckResponseSerializer,
    VisaPDFDownloadSerializer
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


class VisaPDFDownloadAPIView(APIView):
    """API view for downloading visa PDF."""
    permission_classes = [RecaptchaPermission]

    @extend_schema(
        request=VisaPDFDownloadSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description=_("PDF file content")
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description=_("Bad request")
            ),
            500: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description=_("Server error")
            )
        },
        tags=[VISA]
    )
    def post(self, request):
        """Download visa PDF."""
        serializer = VisaPDFDownloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Создаем временную сессию для PDF
            pdf_session = requests.Session()
            pdf_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/pdf,application/x-pdf,application/octet-stream",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": settings.KOREA_VISA_API_URL,
                "Referer": f"{settings.KOREA_VISA_API_URL}/openPage.do?MENU_ID=10301",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin"
            })

            # Сначала инициализируем сессию
            pdf_session.get(
                f"{settings.KOREA_VISA_API_URL}/openPage.do",
                params={"MENU_ID": "10301"}
            )

            # Отправляем запрос на PDF
            pdf_response = pdf_session.post(
                serializer.validated_data['pdf_url'],
                data=serializer.validated_data['pdf_params'],
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            pdf_response.raise_for_status()

            # Возвращаем PDF
            response = HttpResponse(pdf_response.content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="visa_{serializer.validated_data["pdf_params"]["EV_SEQ"]}.pdf"'
            return response

        except Exception as e:
            raise APIException(_("Failed to download PDF: {error}").format(error=str(e)))
