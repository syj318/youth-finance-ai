"""금융감독원 금융상품 한눈에 API의 예금·적금 상품을 표준화한다."""

from __future__ import annotations

import os
from typing import Any, Mapping

import requests


FINLIFE_BASE_URL = "https://finlife.fss.or.kr/finlifeapi"


def _result(available: bool, items=None, error_code=None):
    return {"available": available, "error_code": error_code, "items": items or []}


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _term(value):
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else number


def normalize_financial_products(payload: Mapping[str, Any], product_type: str):
    """공식 baseList/optionList를 회사·상품 코드 기준으로 결합한다."""
    result = payload.get("result", payload) if isinstance(payload, Mapping) else {}
    if not isinstance(result, Mapping):
        raise ValueError("금융상품 API 응답의 result 형식이 올바르지 않습니다.")
    bases = result.get("baseList", [])
    options = result.get("optionList", [])
    if not isinstance(bases, list) or not isinstance(options, list):
        raise ValueError("금융상품 API의 baseList 또는 optionList 형식이 올바르지 않습니다.")

    grouped = {}
    for option in options:
        if not isinstance(option, Mapping):
            continue
        key = (option.get("fin_co_no"), option.get("fin_prdt_cd"))
        grouped.setdefault(key, []).append(option)

    normalized = []
    for base in bases:
        if not isinstance(base, Mapping):
            continue
        key = (base.get("fin_co_no"), base.get("fin_prdt_cd"))
        matched = grouped.get(key) or [None]
        for option in matched:
            option = option or {}
            normalized.append(
                {
                    "source": "FSS_FINLIFE",
                    "product_type": product_type,
                    "company_name": base.get("kor_co_nm"),
                    "product_name": base.get("fin_prdt_nm"),
                    "product_code": base.get("fin_prdt_cd"),
                    "company_code": base.get("fin_co_no"),
                    "join_way": base.get("join_way"),
                    "term_months": _term(option.get("save_trm")),
                    "base_rate": _number(option.get("intr_rate")),
                    "max_rate": _number(option.get("intr_rate2")),
                    "rate_type": option.get("intr_rate_type_nm"),
                    "reserve_type": option.get("rsrv_type_nm"),
                    "special_conditions": base.get("spcl_cnd"),
                    "join_member": base.get("join_member"),
                    "etc_note": base.get("etc_note"),
                }
            )
    return normalized


def _fetch(product_type: str, api_key=None, timeout=10):
    key = api_key or os.getenv("FSS_FINLIFE_API_KEY")
    if not key:
        return _result(False, error_code="MISSING_API_KEY")
    endpoint = (
        "savingProductsSearch.json"
        if product_type == "saving"
        else "depositProductsSearch.json"
    )
    try:
        response = requests.get(
            f"{FINLIFE_BASE_URL}/{endpoint}",
            params={"auth": key, "topFinGrpNo": "020000", "pageNo": 1},
            timeout=timeout,
        )
        if response.status_code in (401, 403):
            return _result(False, error_code="AUTH_ERROR")
        response.raise_for_status()
        payload = response.json()
        api_result = payload.get("result", {}) if isinstance(payload, Mapping) else {}
        if isinstance(api_result, Mapping) and api_result.get("err_cd") not in (None, "000"):
            code = "AUTH_ERROR" if str(api_result.get("err_cd")) in {"010", "020"} else "API_ERROR"
            return _result(False, error_code=code)
        return _result(True, normalize_financial_products(payload, product_type))
    except requests.Timeout:
        return _result(False, error_code="TIMEOUT")
    except (requests.RequestException, ValueError, TypeError):
        return _result(False, error_code="API_UNAVAILABLE")


def fetch_saving_products(api_key=None, timeout=10):
    return _fetch("saving", api_key, timeout)


def fetch_deposit_products(api_key=None, timeout=10):
    return _fetch("deposit", api_key, timeout)
