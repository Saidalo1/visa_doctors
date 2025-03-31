"""Visa status parser for Korea visa."""
import random
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from lxml import html
from rest_framework.exceptions import APIException


@dataclass
class VisaSearchParams:
    """Class for visa search parameters"""
    passport_number: str
    english_name: str
    birth_date: str
    application_type: str = "gb03"  # Default search through embassy


# Pre-compile regex pattern
ERROR_PATTERN = re.compile(r'ERROR_TYPE')

# Status translations as a constant
STATUS_TRANSLATIONS = {
    '허가': 'Approved',
    '상세정보접수': 'Application Received',
    '불허': 'Rejected',
    '심사중': 'Under Review',
    '접수': 'Application Received'
}


class KoreaVisaAPI:
    def __init__(self):
        self.base_url = settings.KOREA_VISA_API_URL
        self.session = requests.Session()
        self._update_headers()

    @staticmethod
    def _get_random_language_header() -> str:
        """Generate random language header"""
        return random.choice([
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9",
            "ko-KR,ko;q=0.9,en-US;q=0.8",
            "ja-JP,ja;q=0.9,en-US;q=0.8",
            "zh-CN,zh;q=0.9,en-US;q=0.8"
        ])

    @staticmethod
    def _get_user_agent() -> str:
        """Get random user agent from predefined list"""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36",
            "Mozilla/5.0 (iPad; CPU OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
        ])

    def _update_headers(self) -> None:
        """Update headers with random values"""
        self.session.headers.update({
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": self._get_random_language_header(),
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/openPage.do?MENU_ID=10301",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        })

    def _initialize_session(self) -> None:
        """Initialize session"""
        response = self.session.get(
            f"{self.base_url}/openPage.do",
            params={"MENU_ID": "10301"}
        )
        response.raise_for_status()

    @staticmethod
    def _prepare_search_data(params: VisaSearchParams) -> Dict[str, str]:
        """Prepare search data"""
        return {
            "CMM_TEST_VAL": "test",
            "sBUSI_GB": "PASS_NO",
            "sBUSI_GBNO": params.passport_number,
            "ssBUSI_GBNO": params.passport_number,
            "pRADIOSEARCH": params.application_type,
            "sEK_NM": params.english_name.upper(),
            "sFROMDATE": params.birth_date,
            "sMainPopUpGB": "main",
            "TRAN_TYPE": "ComSubmit",
            "SE_FLAG_YN": "",
            "LANG_TYPE": "KO"
        }

    @staticmethod
    def _format_date(date_str: str) -> Optional[str]:
        """Format date string to YYYY-MM-DD format"""
        if not date_str:
            return None

        date_str = date_str.strip('.')
        try:
            if '.' in date_str:
                date_obj = datetime.strptime(date_str, '%Y.%m.%d')
            elif '-' in date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except (ValueError, AttributeError):
            return None

    def check_visa_status(self, params: VisaSearchParams) -> Dict[str, Any]:
        """Check visa status"""
        self._update_headers()
        self._initialize_session()

        search_data = self._prepare_search_data(params)
        response = self.session.post(
            f"{self.base_url}/openPage.do",
            data=search_data,
            params={"MENU_ID": "10301"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()

        if ERROR_PATTERN.search(response.text):
            raise APIException(_("Server returned error response"))

        tree = html.fromstring(response.text)
        # Создаем словарь всех элементов с атрибутом id для быстрого доступа
        elements = {el.get("id"): el.text_content().strip() for el in tree.xpath('//*[@id]')}

        # Извлекаем статус и дату из элемента с id "PROC_STS_CDNM_1"
        proc_text = elements.get("PROC_STS_CDNM_1", "")
        if proc_text:
            parts = proc_text.split('(', 1)
            status = parts[0].strip()
            review_date_raw = parts[1].rstrip(')').strip() if len(parts) > 1 else ""
        else:
            status, review_date_raw = "", ""

        # Определяем дату подачи заявления
        application_date_raw = elements.get("APPL_DTM") or elements.get("RECPT_YMD")
        formatted_application_date = self._format_date(application_date_raw) if application_date_raw else None

        # Если статус "접수" (Application Received) — возвращаем минимальные данные
        if status == '접수':
            return {
                "status": "success",
                "visa_data": {
                    "entry_purpose": elements.get("ENTRY_PURPOSE", ""),
                    "progress_status": status,
                    "status_en": STATUS_TRANSLATIONS.get(status, ''),
                    "application_date": formatted_application_date
                }
            }

        # Для других статусов собираем полные данные
        expiry_date = self._format_date(elements.get("VISA_EXPR_YMD", ""))
        review_date = self._format_date(review_date_raw) if review_date_raw else None

        visa_data = {
            "application_date": formatted_application_date,
            "entry_purpose": elements.get("ENTRY_PURPOSE", ""),
            "progress_status": status,
            "status_en": STATUS_TRANSLATIONS.get(status, ''),
            "visa_type": elements.get("VISA_KIND_CD", ""),
            "stay_qualification": elements.get("SOJ_QUAL_NM", ""),
            "expiry_date": expiry_date,
            "review_date": review_date
        }

        # Проверяем наличие причины отказа
        rejection_elements = tree.xpath(
            '//tr[@id="INTNET_OPEN_REJ_RSN_CD" and not(contains(@style, "display:none"))]//td'
        )
        if rejection_elements:
            visa_data['rejection_reason'] = rejection_elements[0].text_content().strip()

        # Если виза одобрена, добавляем информацию для скачивания PDF
        if status == '허가':
            ev_seq = str(tree.xpath('//input[@id="EV_SEQ"]/@value')[0])
            if ev_seq:
                visa_data['pdf_url'] = f"{self.base_url}/biz/ap/ev/selectElectronicVisaPrint3.do"
                visa_data['pdf_params'] = {
                    "EV_SEQ": ev_seq,
                    "INVITEE_SEQ": "0",
                    "APPL_NO": "",
                    "ENG_NM": params.english_name,
                    "BIRTH_YMD": params.birth_date.replace("-", ""),
                    "sBUSI_GB": "PASS_NO",
                    "sBUSI_GBNO": params.passport_number,
                    "TRAN_TYPE": "ComSubmit",
                    "IN_PHOTO": f"{self.base_url}/biz/ap/ev/selectInviteeXvarmImage.do",
                    "SE_FLAG_YN": "",
                    "LANG_TYPE": "KO"
                }

        # Удаляем пустые значения
        visa_data = {k: v for k, v in visa_data.items() if v}

        return {
            "status": "success",
            "visa_data": visa_data
        }


def format_date(date_str: str) -> str:
    """Format date to required format"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(_("Invalid date format. Use YYYY-MM-DD"))
