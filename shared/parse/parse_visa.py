"""Visa status parser for Korea visa."""
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from fake_useragent import UserAgent
from rest_framework.exceptions import APIException


@dataclass
class VisaSearchParams:
    """Class for visa search parameters"""
    passport_number: str
    english_name: str
    birth_date: str
    application_type: str = "gb03"  # Default search through embassy


class KoreaVisaAPI:
    def __init__(self):
        self.base_url = settings.KOREA_VISA_API_URL
        self.session = requests.Session()
        self._update_headers()

    @staticmethod
    def _get_random_language_header():
        """Generate random language header"""
        languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9",
            "ko-KR,ko;q=0.9,en-US;q=0.8",
            "ja-JP,ja;q=0.9,en-US;q=0.8",
            "zh-CN,zh;q=0.9,en-US;q=0.8"
        ]
        return random.choice(languages)

    @staticmethod
    def _get_fallback_user_agent():
        """Get random user agent from fallback list"""
        fallback_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
        return random.choice(fallback_user_agents)

    def _update_headers(self):
        """Update headers with random values"""
        try:
            ua = UserAgent(browsers=['chrome', 'firefox', 'safari'])
            user_agent = ua.random
        except Exception as e:
            print(f"Warning: Failed to get random User-Agent from fake_useragent: {str(e)}")
            print("Using fallback User-Agent list instead")
            user_agent = self._get_fallback_user_agent()

        self.session.headers.update({
            "User-Agent": user_agent,
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

    def _initialize_session(self) -> bool:
        """Initialize session"""
        try:
            response = self.session.get(
                f"{self.base_url}/openPage.do",
                params={"MENU_ID": "10301"}
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            raise APIException(_("Failed to initialize session: {}").format(str(e)))

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
    def _get_div_text(soup: BeautifulSoup, div_id: str) -> str:
        """Get text from div by ID"""
        div = soup.find('div', id=div_id)
        return div.get_text(strip=True) if div else ""

    def check_visa_status(self, params: VisaSearchParams) -> Dict[str, Any]:
        """Check visa status"""
        try:
            self._update_headers()
            if not self._initialize_session():
                raise APIException(_("Failed to initialize session"))

            search_data = self._prepare_search_data(params)
            time.sleep(random.uniform(1, 3))

            response = self.session.post(
                f"{self.base_url}/openPage.do",
                data=search_data,
                params={"MENU_ID": "10301"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()

            if "ERROR_TYPE" in response.text:
                raise APIException(_("Server returned error response"))

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract all available data
            visa_data = {
                "application_number": self._get_div_text(soup, "ONLINE_APPL_NO"),
                "application_date": self._get_div_text(soup, "APPL_DTM"),
                "entry_purpose": self._get_div_text(soup, "ENTRY_PURPOSE"),
                "progress_status": self._get_div_text(soup, "PROC_STS_CDNM_1"),
                "visa_type": self._get_div_text(soup, "VISA_KIND_CD"),
                "stay_qualification": self._get_div_text(soup, "SOJ_QUAL_NM"),
                "expiry_date": self._get_div_text(soup, "VISA_EXPR_YMD")
            }

            # Check for rejection reason
            rejection_row = soup.find('tr', id='INTNET_OPEN_REJ_RSN_CD')
            if rejection_row and rejection_row.get('style') != 'display:none;':
                visa_data['rejection_reason'] = rejection_row.find('td').get_text(strip=True)

            # Add status translation
            status_translations = {
                '허가': 'Approved',
                '상세정보접수': 'Application Received',
                '불허': 'Rejected',
                '심사중': 'Under Review'
            }

            if visa_data['progress_status'] in status_translations:
                visa_data['status_en'] = status_translations[visa_data['progress_status']]

            return {
                "status": "success",
                "visa_data": {k: v for k, v in visa_data.items() if v}
            }

        except requests.RequestException as e:
            raise APIException(_("Failed to check visa status: {}").format(str(e)))
        except Exception as e:
            raise APIException(_("Unexpected error: {}").format(str(e)))


def format_date(date_str: str) -> str:
    """Format date to required format"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(_("Invalid date format. Use YYYY-MM-DD"))
