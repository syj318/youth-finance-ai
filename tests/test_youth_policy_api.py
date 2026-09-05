import os
import unittest
from unittest.mock import Mock, patch

import requests

from src.youth_policy_api import fetch_youth_policies, normalize_youth_policy


class YouthPolicyApiTests(unittest.TestCase):
    def test_normalizes_current_official_fields(self):
        item = normalize_youth_policy(
            {
                "plcyNo": "P1",
                "plcyNm": "청년 자산형성",
                "zipCdNm": "서울",
                "lclsfNm": "금융·복지",
                "plcySprtCn": "지원 내용",
                "sprtTrgtMinAge": "19",
                "sprtTrgtMaxAge": "34",
                "earnMaxAmt": "40000000",
                "jobCdNm": "재직자",
                "aplyYmd": "상시",
                "plcyAplyMthdCn": "온라인",
                "aplyUrlAddr": "https://example.test/p1",
            }
        )
        self.assertEqual(item["source"], "ONTONG_YOUTH")
        self.assertEqual(item["policy_id"], "P1")
        self.assertEqual(item["max_age"], "34")
        self.assertEqual(item["max_income"], "40000000")

    def test_normalizes_legacy_official_fields(self):
        item = normalize_youth_policy(
            {"bizId": "OLD", "polyBizSjnm": "정책", "sporCn": "지원", "ageInfo": "만 19세 이상"}
        )
        self.assertEqual(item["policy_id"], "OLD")
        self.assertEqual(item["policy_name"], "정책")
        self.assertEqual(item["age_condition"], "만 19세 이상")

    @patch("src.youth_policy_api.requests.get")
    def test_parses_xml_response(self, get):
        response = Mock(status_code=200)
        response.content = (
            b"<response><youthPolicy><plcyNo>P1</plcyNo>"
            b"<plcyNm>Policy</plcyNm><jobCdNm>Worker</jobCdNm>"
            b"</youthPolicy></response>"
        )
        response.raise_for_status.return_value = None
        get.return_value = response
        result = fetch_youth_policies("key", {"region": "서울"}, keyword="자산")
        self.assertTrue(result["available"])
        self.assertEqual(result["items"][0]["policy_id"], "P1")
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["openApiVlak"], "key")
        self.assertEqual(params["query"], "자산")

    @patch("src.youth_policy_api.requests.get", side_effect=requests.Timeout)
    def test_timeout_is_structured(self, _get):
        self.assertEqual(fetch_youth_policies("key")["error_code"], "TIMEOUT")

    @patch("src.youth_policy_api.requests.get")
    def test_auth_error_is_structured(self, get):
        get.return_value = Mock(status_code=401)
        self.assertEqual(fetch_youth_policies("bad")["error_code"], "AUTH_ERROR")

    @patch("src.youth_policy_api.requests.get")
    def test_invalid_xml_is_structured(self, get):
        response = Mock(status_code=200, content=b"not xml")
        response.raise_for_status.return_value = None
        get.return_value = response
        self.assertEqual(fetch_youth_policies("key")["error_code"], "API_UNAVAILABLE")

    def test_missing_key_and_empty_profile_are_safe(self):
        with patch.dict(os.environ, {}, clear=True), patch("src.youth_policy_api.requests.get") as get:
            result = fetch_youth_policies(user_profile=None)
        self.assertEqual(result["error_code"], "MISSING_API_KEY")
        self.assertEqual(result["items"], [])
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
