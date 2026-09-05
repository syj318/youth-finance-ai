"""온통청년 OPEN API 정책 응답을 내부 표준 구조로 변환한다."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any, Mapping

import requests


YOUTH_POLICY_URL = "https://www.youthcenter.go.kr/opi/youthPlcyList.do"


def _first(item: Mapping[str, Any], *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_youth_policy(item: Mapping[str, Any]):
    """온통청년 신·구 공식 필드명을 손실 없는 표준 필드로 매핑한다."""
    return {
        "source": "ONTONG_YOUTH",
        "policy_id": _first(item, "plcyNo", "bizId"),
        "policy_name": _first(item, "plcyNm", "polyBizSjnm"),
        "region": _first(item, "zipCdNm", "region", "polyBizSecd"),
        "policy_category": _first(item, "lclsfNm", "mclsfNm", "polyRlmCd"),
        "support_content": _first(item, "plcySprtCn", "sporCn", "polyItcnCn"),
        "age_condition": _first(item, "sprtTrgtAgeCn", "ageInfo"),
        "min_age": _first(item, "sprtTrgtMinAge", "minAge"),
        "max_age": _first(item, "sprtTrgtMaxAge", "maxAge"),
        "income_condition": _first(item, "earnCndCn", "accrRqisCn"),
        "min_income": _first(item, "earnMinAmt", "minIncome"),
        "max_income": _first(item, "earnMaxAmt", "maxIncome"),
        "employment_condition": _first(item, "jobCdNm", "empmSttsCn"),
        "education_condition": _first(item, "schoolCdNm", "accrRqisCn"),
        "marital_condition": _first(item, "mrgSttsCdNm", "mrgSttsCd"),
        "application_period": _first(item, "aplyYmd", "rqutPrdCn"),
        "application_method": _first(item, "plcyAplyMthdCn", "rqutProcCn"),
        "detail_url": _first(item, "aplyUrlAddr", "rqutUrla", "refUrlAddr1"),
        "additional_conditions": _first(item, "addAplyQlfcCndCn", "aditRscn"),
        "exclusion_conditions": _first(item, "ptcpPrpTrgtCn", "prcpLmttTrgtCn"),
    }


def _xml_items(content: bytes):
    root = ET.fromstring(content)
    candidates = root.findall(".//youthPolicy") or root.findall(".//item") or root.findall(".//emp")
    return [
        {child.tag.split("}")[-1]: (child.text or "").strip() for child in node}
        for node in candidates
    ]


def fetch_youth_policies(api_key=None, user_profile=None, keyword=None, timeout=10):
    key = api_key or os.getenv("YOUTH_POLICY_API_KEY")
    if not key:
        return {"available": False, "error_code": "MISSING_API_KEY", "items": []}
    profile = user_profile if isinstance(user_profile, Mapping) else {}
    params = {"openApiVlak": key, "pageIndex": 1, "display": 100}
    if keyword:
        params["query"] = keyword
    if profile.get("region"):
        params["keyword"] = str(profile["region"])
    try:
        response = requests.get(YOUTH_POLICY_URL, params=params, timeout=timeout)
        if response.status_code in (401, 403):
            return {"available": False, "error_code": "AUTH_ERROR", "items": []}
        response.raise_for_status()
        items = _xml_items(response.content)
        return {
            "available": True,
            "error_code": None,
            "items": [normalize_youth_policy(item) for item in items],
        }
    except requests.Timeout:
        return {"available": False, "error_code": "TIMEOUT", "items": []}
    except (requests.RequestException, ET.ParseError, ValueError, TypeError):
        return {"available": False, "error_code": "API_UNAVAILABLE", "items": []}
