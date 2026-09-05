import os
import unittest
from unittest.mock import Mock, patch

import requests

from src.financial_product_api import (
    fetch_deposit_products,
    fetch_saving_products,
    normalize_financial_products,
)


class FinancialProductApiTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "result": {
                "err_cd": "000",
                "baseList": [
                    {
                        "fin_co_no": "001",
                        "kor_co_nm": "테스트은행",
                        "fin_prdt_cd": "S001",
                        "fin_prdt_nm": "청년 적금",
                        "join_way": "인터넷",
                        "spcl_cnd": "공식 우대조건",
                        "join_member": "개인",
                        "etc_note": "공식 안내",
                    }
                ],
                "optionList": [
                    {
                        "fin_co_no": "001",
                        "fin_prdt_cd": "S001",
                        "save_trm": "12",
                        "intr_rate": 3.1,
                        "intr_rate2": 4.2,
                        "intr_rate_type_nm": "단리",
                        "rsrv_type_nm": "정액적립식",
                    },
                    {
                        "fin_co_no": "999",
                        "fin_prdt_cd": "OTHER",
                        "save_trm": "6",
                    },
                ],
            }
        }

    def test_normalizes_and_joins_base_and_option(self):
        items = normalize_financial_products(self.payload, "saving")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["company_name"], "테스트은행")
        self.assertEqual(items[0]["product_code"], "S001")
        self.assertEqual(items[0]["term_months"], 12)
        self.assertEqual(items[0]["max_rate"], 4.2)
        self.assertEqual(items[0]["reserve_type"], "정액적립식")

    def test_missing_option_fields_are_none(self):
        payload = {"result": {"baseList": self.payload["result"]["baseList"], "optionList": []}}
        item = normalize_financial_products(payload, "deposit")[0]
        self.assertIsNone(item["term_months"])
        self.assertIsNone(item["base_rate"])
        self.assertIsNone(item["max_rate"])

    @patch("src.financial_product_api.requests.get")
    def test_fetch_saving_uses_official_endpoint_and_parses(self, get):
        response = Mock(status_code=200)
        response.json.return_value = self.payload
        response.raise_for_status.return_value = None
        get.return_value = response
        result = fetch_saving_products("key")
        self.assertTrue(result["available"])
        self.assertEqual(len(result["items"]), 1)
        self.assertIn("savingProductsSearch.json", get.call_args.args[0])
        self.assertNotIn("key", get.call_args.args[0])

    @patch("src.financial_product_api.requests.get")
    def test_fetch_deposit_uses_official_endpoint(self, get):
        response = Mock(status_code=200)
        response.json.return_value = self.payload
        response.raise_for_status.return_value = None
        get.return_value = response
        result = fetch_deposit_products("key")
        self.assertTrue(result["available"])
        self.assertEqual(result["items"][0]["product_type"], "deposit")
        self.assertIn("depositProductsSearch.json", get.call_args.args[0])

    @patch("src.financial_product_api.requests.get", side_effect=requests.Timeout)
    def test_timeout_is_structured(self, _get):
        self.assertEqual(fetch_saving_products("key")["error_code"], "TIMEOUT")

    @patch("src.financial_product_api.requests.get")
    def test_auth_error_is_structured(self, get):
        get.return_value = Mock(status_code=403)
        self.assertEqual(fetch_saving_products("bad")["error_code"], "AUTH_ERROR")

    def test_missing_key_does_not_call_api(self):
        with patch.dict(os.environ, {}, clear=True), patch("src.financial_product_api.requests.get") as get:
            result = fetch_saving_products()
        self.assertEqual(result, {"available": False, "error_code": "MISSING_API_KEY", "items": []})
        get.assert_not_called()

    def test_empty_api_result_is_available_empty(self):
        self.assertEqual(normalize_financial_products({"result": {"baseList": [], "optionList": []}}, "saving"), [])


if __name__ == "__main__":
    unittest.main()
