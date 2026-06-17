"""
kis_api.py — KIS 인증 & API 호출 모듈
autotrader.py에서 사용하는 인터페이스를 제공한다.
"""

import csv
import datetime
import importlib
import io
import os
import time

import requests

CFG_MODULE = os.getenv("TRADER_CONFIG_MODULE", "config")
cfg = importlib.import_module(CFG_MODULE)

APP_KEY = getattr(cfg, "APP_KEY", "")
APP_SECRET = getattr(cfg, "APP_SECRET", "")
ACCOUNT_NO = getattr(cfg, "ACCOUNT_NO", "")
BASE_URL = getattr(cfg, "BASE_URL", "")
IS_VIRTUAL = getattr(cfg, "IS_VIRTUAL", True)
US_EXCHANGE = getattr(cfg, "US_EXCHANGE", "NAS")
US_UNIVERSE = getattr(cfg, "US_UNIVERSE", [])

_access_token = None
_token_expired_at = None


def _parse_account_no() -> tuple[str, str]:
    raw = ACCOUNT_NO.strip()
    if "-" in raw:
        acc_no, acc_prod = raw.split("-", 1)
    else:
        acc_no, acc_prod = raw[:8], raw[8:]
    if not acc_no or not acc_prod:
        raise ValueError("ACCOUNT_NO 형식이 올바르지 않습니다. 예: 50123456-01")
    return acc_no, acc_prod


def _to_int(value) -> int:
    try:
        return int(str(value).replace(",", "").strip() or "0")
    except (TypeError, ValueError):
        return 0


def _to_float(value) -> float:
    try:
        return float(str(value).replace(",", "").strip() or "0")
    except (TypeError, ValueError):
        return 0.0


def _first_nonzero_int(*values) -> int:
    for value in values:
        parsed = _to_int(value)
        if parsed != 0:
            return parsed
    return 0


def _first_nonzero_float(*values) -> float:
    for value in values:
        parsed = _to_float(value)
        if parsed != 0:
            return parsed
    return 0.0


def _extract_numeric_by_keywords(data: dict, keywords: tuple[str, ...], as_int: bool = False):
    for key, value in data.items():
        k = str(key).lower()
        if any(token in k for token in keywords):
            parsed = _to_int(value) if as_int else _to_float(value)
            if parsed != 0:
                return parsed
    return 0 if as_int else 0.0


def _first_payload_dict(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    for key in ("output", "output1", "output2"):
        block = payload.get(key)
        if isinstance(block, dict) and block:
            return block
        if isinstance(block, list) and block and isinstance(block[0], dict):
            return block[0]
    if _extract_numeric_by_keywords(payload, ("price", "prpr", "last", "close"), as_int=True) > 0:
        return payload
    return {}


def _normalize_us_exchange(exchange: str) -> str:
    mapping = {
        "NASD": "NAS",
        "NASDAQ": "NAS",
        "NYSE": "NYS",
        "AMEX": "AMS",
    }
    ex = str(exchange or "").upper().strip()
    return mapping.get(ex, ex or "NAS")


def get_access_token() -> str:
    global _access_token, _token_expired_at
    now = datetime.datetime.now()
    if _access_token and _token_expired_at and now < _token_expired_at:
        return _access_token

    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
    }
    res = requests.post(url, headers=headers, json=body, timeout=10)
    try:
        res.raise_for_status()
    except requests.HTTPError as e:
        msg = ""
        try:
            payload = res.json()
            msg = payload.get("msg1", "") or payload.get("msg_cd", "") or res.text
        except Exception:
            msg = res.text
        raise RuntimeError(f"토큰 발급 실패({res.status_code}): {msg}") from e

    data = res.json()
    _access_token = data.get("access_token", "")
    _token_expired_at = now + datetime.timedelta(hours=23)
    return _access_token


def _headers(tr_id: str, hash_key: str = None) -> dict:
    token = get_access_token()
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
    }
    if hash_key:
        headers["hashkey"] = hash_key
    return headers


def get_hashkey(body: dict) -> str:
    url = f"{BASE_URL}/uapi/hashkey"
    res = requests.post(
        url,
        headers={"content-type": "application/json", "appkey": APP_KEY, "appsecret": APP_SECRET},
        json=body,
        timeout=10,
    )
    return (res.json() or {}).get("HASH", "")


# ===== 국내 =====

def get_current_price(stock_code: str) -> dict:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
    res = requests.get(url, headers=_headers("FHKST01010100"), params=params, timeout=10)
    return (res.json() or {}).get("output", {})


def get_intraday_minute_candles(stock_code: str, count: int = 30) -> list[dict]:
    """
    국내 분봉 데이터(최근 N개) 조회.
    실패 시 빈 리스트 반환.
    """
    try:
        limit = max(5, min(120, int(count)))
    except Exception:
        limit = 30

    try:
        url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        params = {
            "FID_ETC_CLS_CODE": "",
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": datetime.datetime.now().strftime("%H%M%S"),
            "FID_PW_DATA_INCU_YN": "Y",
        }
        res = requests.get(url, headers=_headers("FHKST03010200"), params=params, timeout=10)
        payload = res.json() or {}
    except Exception:
        return []

    rows = payload.get("output2")
    if not isinstance(rows, list):
        rows = payload.get("output1")
    if not isinstance(rows, list):
        return []

    candles = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        close = _first_nonzero_int(row.get("stck_prpr"), row.get("close"), row.get("cur_prc"))
        high = _first_nonzero_int(row.get("stck_hgpr"), row.get("high"), close)
        low = _first_nonzero_int(row.get("stck_lwpr"), row.get("low"), close)
        volume = _first_nonzero_int(row.get("cntg_vol"), row.get("acml_vol"), row.get("volume"))
        if close <= 0:
            continue
        candles.append(
            {
                "close": float(close),
                "high": float(high if high > 0 else close),
                "low": float(low if low > 0 else close),
                "volume": float(max(0, volume)),
            }
        )
        if len(candles) >= limit:
            break

    return list(reversed(candles))


def get_premarket_price_snapshot(stock_code: str) -> dict:
    """
    장전(동시호가) 관찰용 스냅샷.
    - 기본 현재가 스냅샷을 기반으로, 예상체결 값을 덮어쓴다.
    - 필드가 비어 있으면 기본 현재가를 그대로 반환한다.
    """
    base = get_current_price(stock_code) or {}
    try:
        url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
        res = requests.get(url, headers=_headers("FHKST01010200"), params=params, timeout=10)
        payload = res.json() or {}
    except Exception:
        return base

    snap = {}
    for key in ("output", "output1", "output2"):
        block = payload.get(key)
        if isinstance(block, dict) and block:
            snap = block
            break
        if isinstance(block, list) and block and isinstance(block[0], dict):
            snap = block[0]
            break

    if not snap:
        return base

    expected_price = _first_nonzero_int(
        snap.get("antc_cnpr"),
        snap.get("antc_prpr"),
        snap.get("stck_prpr"),
    )
    expected_rate = _first_nonzero_float(
        snap.get("antc_cntg_prdy_ctrt"),
        snap.get("antc_prdy_ctrt"),
        snap.get("prdy_ctrt"),
    )
    expected_vol = _first_nonzero_int(
        snap.get("antc_vol"),
        snap.get("acml_vol"),
        base.get("acml_vol", 0),
    )

    merged = dict(base)
    if expected_price > 0:
        merged["stck_prpr"] = str(expected_price)
    if expected_rate != 0:
        merged["prdy_ctrt"] = str(expected_rate)
    if expected_vol > 0:
        merged["acml_vol"] = str(expected_vol)
        merged["vol_tnrt"] = str(expected_vol)
        merged["avls_hmcl_no"] = str(max(1, expected_vol))
    return merged


def get_volume_rank() -> list:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/volume-rank"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0",
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1": "1000",
        "FID_INPUT_PRICE_2": "300000",
        "FID_VOL_CNT": "50000",
        "FID_INPUT_DATE_1": "",
    }
    res = requests.get(url, headers=_headers("FHPST01710000"), params=params, timeout=10)
    return (res.json() or {}).get("output", [])


def get_fluctuation_rank() -> list:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/ranking/fluctuation"
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20624",
        "fid_input_iscd": "0000",
        "fid_rank_sort_cls_code": "0",
        "fid_input_cnt_1": "0",
        "fid_prc_cls_code": "1",
        "fid_input_price_1": "1000",
        "fid_input_price_2": "300000",
        "fid_vol_cnt": "50000",
        "fid_trgt_cls_code": "0",
        "fid_trgt_exls_cls_code": "0",
        "fid_div_cls_code": "0",
        "fid_rsfl_rate1": str(1.0),
        "fid_rsfl_rate2": str(25.0),
    }
    res = requests.get(url, headers=_headers("FHPST01650000"), params=params, timeout=10)
    return (res.json() or {}).get("output", [])


def get_balance() -> list:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
    tr_id = "VTTC8434R" if IS_VIRTUAL else "TTTC8434R"
    acc_no, acc_prod = _parse_account_no()
    params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
    return (res.json() or {}).get("output1", [])


def get_available_cash(stock_code: str, price: int) -> int:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
    tr_id = "VTTC8908R" if IS_VIRTUAL else "TTTC8908R"
    acc_no, acc_prod = _parse_account_no()
    params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "PDNO": stock_code,
        "ORD_UNPR": str(max(1, int(price))),
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N",
    }
    res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
    data = (res.json() or {}).get("output", {})
    for key in ("ord_psbl_cash", "nrcvb_buy_amt", "max_buy_amt", "ord_psbl_amt"):
        amount = _to_int(data.get(key, 0))
        if amount > 0:
            return amount
    return 0


def buy_market_order(stock_code: str, qty: int) -> dict:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = "VTTC0802U" if IS_VIRTUAL else "TTTC0802U"
    acc_no, acc_prod = _parse_account_no()
    body = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "PDNO": stock_code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",
    }
    hash_key = get_hashkey(body)
    res = requests.post(url, headers=_headers(tr_id, hash_key), json=body, timeout=10)
    return res.json()


def sell_market_order(stock_code: str, qty: int) -> dict:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = "VTTC0801U" if IS_VIRTUAL else "TTTC0801U"
    acc_no, acc_prod = _parse_account_no()
    body = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "PDNO": stock_code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",
    }
    hash_key = get_hashkey(body)
    res = requests.post(url, headers=_headers(tr_id, hash_key), json=body, timeout=10)
    return res.json()


def get_today_realized_pnl_kr() -> int:
    """
    국내주식 계좌의 당일 실현손익 조회.
    - 주식일별주문체결조회 API를 사용
    - 응답 포맷 차이를 고려해 여러 후보 필드를 순차 파싱
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    acc_no, acc_prod = _parse_account_no()
    today = datetime.datetime.now().strftime("%Y%m%d")

    # 신/구 TR 모두 시도 (환경별 호환)
    tr_candidates = ["VTTC0081R", "VTTC8001R"] if IS_VIRTUAL else ["TTTC0081R", "TTTC8001R"]
    base_params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",  # 전체(매도/매수)
        "INQR_DVSN": "00",        # 역순
        "PDNO": "",
        "CCLD_DVSN": "01",        # 체결
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    for tr_id in tr_candidates:
        try:
            res = requests.get(url, headers=_headers(tr_id), params=base_params, timeout=10)
            payload = res.json() or {}
        except Exception:
            continue

        summary_amount = None
        # 1) 집계 영역 우선 파싱 (0도 유효값)
        output2 = payload.get("output2")
        if isinstance(output2, dict):
            for key in (
                "prsm_tlex_smtl",      # 추정손익합계(문서/샘플에서 자주 사용)
                "realized_pfls_amt",
                "rlzt_pfls_amt",
                "tot_rlzt_pfls",
                "tot_pfls",
            ):
                if key in output2:
                    summary_amount = _to_int(output2.get(key, 0))
                    break

        # 2) 체결 목록에서 "매도" 체결 손익 계산 (필드가 없으면 약식 계산)
        rows = payload.get("output1")
        if isinstance(rows, list) and rows:
            total = 0
            parsed_sell_row = False
            for row in rows:
                if not isinstance(row, dict):
                    continue

                side_name = str(
                    row.get("sll_buy_dvsn_cd_name", row.get("sll_buy_dvsn_name", row.get("trad_dvsn_name", "")))
                ).strip()
                side_code = str(row.get("sll_buy_dvsn_cd", "")).strip()

                is_sell = False
                if "매도" in side_name:
                    is_sell = True
                elif side_name and "매수" in side_name:
                    is_sell = False
                elif side_code in ("01",):
                    # 문서/응답별 매도 코드 차이를 고려한 보수적 fallback
                    is_sell = True
                elif side_code in ("02",):
                    is_sell = False

                if not is_sell:
                    continue
                parsed_sell_row = True

                qty = _to_int(row.get("tot_ccld_qty", row.get("ccld_qty", 0)))
                avg_price = _to_int(row.get("avg_prvs", row.get("pchs_avg_pric", 0)))
                ccld_amt = _to_int(row.get("tot_ccld_amt", row.get("sttl_amt", 0)))

                pnl = None
                for key in (
                    "realized_pfls_amt",
                    "rlzt_pfls_amt",
                    "evlu_pfls_amt",
                    "prsm_tlex_smtl",
                ):
                    if key in row:
                        pnl = _to_int(row.get(key, 0))
                        break

                if pnl is None:
                    pnl = ccld_amt - (avg_price * qty)
                total += pnl

            if parsed_sell_row:
                return total

        if summary_amount is not None:
            return summary_amount

        # 정상 응답이지만 내역/집계 키가 없는 경우
        if payload.get("rt_cd") == "0":
            return 0

    return 0


def get_order_fills_kr(order_no: str) -> dict:
    """
    국내 주문번호 기준 당일 체결 내역 조회.
    반환값:
      {
        "order_no": str,
        "filled_qty": int,
        "ordered_qty": int,
        "remaining_qty": int,
        "avg_fill_price": int,
        "status": "none" | "partial" | "filled",
      }
    """
    odno = str(order_no or "").strip()
    if not odno:
        return {
            "order_no": "",
            "filled_qty": 0,
            "ordered_qty": 0,
            "remaining_qty": 0,
            "avg_fill_price": 0,
            "status": "none",
        }

    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    acc_no, acc_prod = _parse_account_no()
    today = datetime.datetime.now().strftime("%Y%m%d")
    tr_candidates = ["VTTC0081R", "VTTC8001R"] if IS_VIRTUAL else ["TTTC0081R", "TTTC8001R"]
    params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",
        "INQR_DVSN": "00",
        "PDNO": "",
        "CCLD_DVSN": "00",
        "ORD_GNO_BRNO": "",
        "ODNO": odno,
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    for tr_id in tr_candidates:
        try:
            res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
            payload = res.json() or {}
        except Exception:
            continue
        rows = payload.get("output1")
        if not isinstance(rows, list):
            continue

        filtered = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_odno = str(row.get("odno", row.get("ODNO", ""))).strip()
            if row_odno and row_odno != odno:
                continue
            filtered.append(row)
        if not filtered:
            continue

        ordered_qty = 0
        filled_qty = 0
        remaining_qty = 0
        fill_amt = 0
        for row in filtered:
            ordered_qty = max(
                ordered_qty,
                _to_int(row.get("ord_qty", row.get("tot_ord_qty", row.get("ord_tmd_qty", 0)))),
            )
            row_filled = _to_int(row.get("tot_ccld_qty", row.get("ccld_qty", 0)))
            filled_qty = max(filled_qty, row_filled)
            row_remaining = _to_int(
                row.get("rmn_qty", row.get("ord_psbl_qty", row.get("nccs_qty", 0)))
            )
            remaining_qty = max(remaining_qty, row_remaining)
            row_amt = _to_int(row.get("tot_ccld_amt", row.get("ccld_amt", row.get("sttl_amt", 0))))
            fill_amt = max(fill_amt, row_amt)

        if ordered_qty <= 0 and filled_qty > 0:
            ordered_qty = filled_qty + remaining_qty

        avg_fill_price = 0
        if filled_qty > 0 and fill_amt > 0:
            avg_fill_price = int(fill_amt / max(1, filled_qty))
        if avg_fill_price <= 0:
            for row in filtered:
                avg_fill_price = _to_int(row.get("avg_prvs", row.get("ccld_unpr", row.get("ord_unpr", 0))))
                if avg_fill_price > 0:
                    break

        if filled_qty <= 0:
            status = "none"
        elif ordered_qty > 0 and filled_qty >= ordered_qty and remaining_qty == 0:
            status = "filled"
        else:
            status = "partial"

        return {
            "order_no": odno,
            "filled_qty": int(filled_qty),
            "ordered_qty": int(ordered_qty),
            "remaining_qty": int(remaining_qty),
            "avg_fill_price": int(avg_fill_price),
            "status": status,
        }

    return {
        "order_no": odno,
        "filled_qty": 0,
        "ordered_qty": 0,
        "remaining_qty": 0,
        "avg_fill_price": 0,
        "status": "none",
    }


# ===== 해외 =====

def get_us_current_price(stock_code: str, exchange: str = US_EXCHANGE) -> dict:
    ex = _normalize_us_exchange(exchange)
    ex_candidates = [ex, "NAS", "NYS", "AMS", "NASD", "NYSE", "AMEX"]
    quote_apis = [
        (f"{BASE_URL}/uapi/overseas-price/v1/quotations/price", "HHDFS00000300"),
        (f"{BASE_URL}/uapi/overseas-price/v1/quotations/price-detail", "HHDFS76200200"),
    ]
    tried = set()

    for ex_code in ex_candidates:
        if ex_code in tried:
            continue
        tried.add(ex_code)
        params = {"AUTH": "", "EXCD": ex_code, "SYMB": stock_code}
        output = {}
        for url, tr_id in quote_apis:
            try:
                res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
                output = _first_payload_dict(res.json() or {})
                if output:
                    break
            except Exception:
                continue

        price = _first_nonzero_int(output.get("last"), output.get("ovrs_nmix_prpr"), output.get("stck_prpr"), output.get("close"))
        if price <= 0 and output:
            price = _extract_numeric_by_keywords(output, ("last", "prpr", "close", "cur", "price"), as_int=True)
        if price <= 0:
            continue

        prev = _first_nonzero_float(output.get("base"), output.get("ovrs_nmix_prdy_clpr"), output.get("prev"), output.get("pclos"))
        change_rate = _first_nonzero_float(output.get("rate"), output.get("prdy_ctrt"), output.get("chg_rate"))
        if change_rate == 0 and output:
            change_rate = _extract_numeric_by_keywords(output, ("rate", "ctrt", "chg"), as_int=False)
        if prev > 0 and change_rate == 0:
            change_rate = (price - prev) / prev * 100

        volume = _first_nonzero_int(output.get("tvol"), output.get("acml_vol"), output.get("volume"))
        if volume <= 0:
            volume = _extract_numeric_by_keywords(output, ("vol", "qty"), as_int=True)

        return {
            "stck_prpr": str(price),
            "prdy_ctrt": str(change_rate),
            "vol_tnrt": str(volume),
            "acml_vol": str(volume),
            "avls_hmcl_no": str(max(1, volume)),
            "w52_hgpr": str(_first_nonzero_float(output.get("h52p"), output.get("w52_hgpr"), price)),
            "w52_lwpr": str(_first_nonzero_float(output.get("l52p"), output.get("w52_lwpr"), price)),
            "per": str(_first_nonzero_float(output.get("perx"), output.get("per"))),
        }

    return {
        "stck_prpr": "0",
        "prdy_ctrt": "0",
        "vol_tnrt": "0",
        "acml_vol": "0",
        "avls_hmcl_no": "1",
        "w52_hgpr": "0",
        "w52_lwpr": "0",
        "per": "",
    }


def get_us_rank_candidates(exchange: str = US_EXCHANGE) -> list:
    ex = _normalize_us_exchange(exchange)
    endpoint_specs = [
        (f"{BASE_URL}/uapi/overseas-stock/v1/ranking/updown", ("HHDFS76240000", "HHDFS76200400")),
        (f"{BASE_URL}/uapi/overseas-stock/v1/ranking/volume", ("HHDFS76240100", "HHDFS76200500")),
    ]
    exchange_candidates = [ex, "NAS", "NYS", "AMS"]
    candidates = {}

    for url, tr_ids in endpoint_specs:
        for tr_id in tr_ids:
            for ex_code in exchange_candidates:
                params = {"AUTH": "", "EXCD": ex_code, "SORT": "1", "TOPN": "30", "CNT": "30"}
                try:
                    res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
                    payload = res.json() or {}
                except Exception:
                    continue

                rows = []
                for key in ("output", "output1", "output2"):
                    block = payload.get(key)
                    if isinstance(block, list):
                        rows.extend([r for r in block if isinstance(r, dict)])

                for row in rows:
                    code = (
                        str(row.get("symb", "")).strip()
                        or str(row.get("ovrs_pdno", "")).strip()
                        or str(row.get("pdno", "")).strip()
                        or str(row.get("code", "")).strip()
                    )
                    if not code:
                        continue
                    name = (
                        str(row.get("ovrs_item_name", "")).strip()
                        or str(row.get("name", "")).strip()
                        or code
                    )
                    change_rate = _first_nonzero_float(row.get("prdy_ctrt"), row.get("rate"), row.get("chg_rate"))
                    candidates[code] = {"code": code, "name": name, "change_rate": change_rate}

                if len(candidates) >= 10:
                    return list(candidates.values())[:30]

    return list(candidates.values())[:30]


def get_us_current_price_public(stock_code: str) -> dict:
    # Yahoo
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_code}"
        res = requests.get(url, params={"range": "1d", "interval": "1d"}, timeout=10)
        payload = res.json() or {}
        result = (((payload.get("chart") or {}).get("result") or [None])[0]) or {}
        meta = result.get("meta") or {}
        quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}

        close = _to_float(meta.get("regularMarketPrice", 0))
        prev_close = _to_float(meta.get("previousClose", 0))
        open_p = _to_float(meta.get("regularMarketOpen", prev_close))
        high = _to_float(meta.get("regularMarketDayHigh", close))
        low = _to_float(meta.get("regularMarketDayLow", close))
        vol_list = quote.get("volume") or []
        volume = _to_int(vol_list[-1] if vol_list else 0)
        if close > 0:
            change_rate = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
            return {
                "stck_prpr": str(int(round(close))),
                "prdy_ctrt": str(change_rate),
                "vol_tnrt": str(volume),
                "acml_vol": str(volume),
                "avls_hmcl_no": str(max(1, volume)),
                "w52_hgpr": str(int(round(high if high > 0 else close))),
                "w52_lwpr": str(int(round(low if low > 0 else close))),
                "per": "",
            }
    except Exception:
        pass

    # Stooq
    try:
        symbol = stock_code.lower().replace(".", "-")
        url = f"https://stooq.com/q/l/?s={symbol}.us&i=d"
        res = requests.get(url, timeout=10)
        if res.status_code == 200 and res.text.strip():
            row = next(csv.DictReader(io.StringIO(res.text)), None)
            if row:
                close = _to_float(row.get("Close", 0))
                open_p = _to_float(row.get("Open", 0))
                high = _to_float(row.get("High", 0))
                low = _to_float(row.get("Low", 0))
                volume = _to_int(row.get("Volume", 0))
                if close > 0:
                    change_rate = ((close - open_p) / open_p * 100) if open_p > 0 else 0.0
                    return {
                        "stck_prpr": str(int(round(close))),
                        "prdy_ctrt": str(change_rate),
                        "vol_tnrt": str(volume),
                        "acml_vol": str(volume),
                        "avls_hmcl_no": str(max(1, volume)),
                        "w52_hgpr": str(int(round(high if high > 0 else close))),
                        "w52_lwpr": str(int(round(low if low > 0 else close))),
                        "per": "",
                    }
    except Exception:
        pass

    return {
        "stck_prpr": "0",
        "prdy_ctrt": "0",
        "vol_tnrt": "0",
        "acml_vol": "0",
        "avls_hmcl_no": "1",
        "w52_hgpr": "0",
        "w52_lwpr": "0",
        "per": "",
    }


def get_us_candidates(exchange: str = US_EXCHANGE, symbols: list[str] = None) -> list:
    rank = get_us_rank_candidates(exchange=exchange)
    if rank:
        return rank

    target_symbols = symbols or US_UNIVERSE
    candidates = []
    success_count = 0
    for symbol in target_symbols:
        try:
            detail = get_us_current_price(symbol, exchange=exchange)
            if _to_int(detail.get("stck_prpr", 0)) <= 0:
                detail = get_us_current_price_public(symbol)
            price = _to_int(detail.get("stck_prpr", 0))
            if price <= 0:
                continue
            success_count += 1
            candidates.append({"code": symbol, "name": symbol, "change_rate": _to_float(detail.get("prdy_ctrt", 0))})
        except Exception:
            continue
        time.sleep(0.05)
    if success_count == 0 and target_symbols:
        print("[US] KIS+공개시세 조회가 모두 실패해 후보를 만들지 못했습니다. 네트워크/프록시/해외시세 권한을 확인하세요.")
    return candidates


def get_us_available_cash(stock_code: str, price: int, exchange: str = US_EXCHANGE) -> int:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-psamount"
    tr_id = "VTTS3007R" if IS_VIRTUAL else "TTTS3007R"
    acc_no, acc_prod = _parse_account_no()
    params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "OVRS_EXCG_CD": _normalize_us_exchange(exchange),
        "ITEM_CD": stock_code,
        "OVRS_ORD_UNPR": str(max(1, int(price))),
    }
    res = requests.get(url, headers=_headers(tr_id), params=params, timeout=10)
    data = (res.json() or {}).get("output", {})
    for key in ("ord_psbl_frcr_amt", "frcr_dncl_amt_2", "ovrs_ord_psbl_amt"):
        amount = _to_int(data.get(key, 0))
        if amount > 0:
            return amount
    return 0


def buy_us_market_order(stock_code: str, qty: int, exchange: str = US_EXCHANGE) -> dict:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
    tr_id = "VTTT1002U" if IS_VIRTUAL else "TTTT1002U"
    acc_no, acc_prod = _parse_account_no()
    body = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "OVRS_EXCG_CD": _normalize_us_exchange(exchange),
        "PDNO": stock_code,
        "ORD_QTY": str(qty),
        "OVRS_ORD_UNPR": "0",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "01",
    }
    hash_key = get_hashkey(body)
    res = requests.post(url, headers=_headers(tr_id, hash_key), json=body, timeout=10)
    return res.json()


def sell_us_market_order(stock_code: str, qty: int, exchange: str = US_EXCHANGE) -> dict:
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
    tr_id = "VTTT1006U" if IS_VIRTUAL else "TTTT1006U"
    acc_no, acc_prod = _parse_account_no()
    body = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "OVRS_EXCG_CD": _normalize_us_exchange(exchange),
        "PDNO": stock_code,
        "ORD_QTY": str(qty),
        "OVRS_ORD_UNPR": "0",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "01",
    }
    hash_key = get_hashkey(body)
    res = requests.post(url, headers=_headers(tr_id, hash_key), json=body, timeout=10)
    return res.json()


# ===== 시장 공통 =====

def get_current_price_by_market(stock_code: str, market: str) -> dict:
    if market == "US":
        detail = get_us_current_price(stock_code)
        if _to_int(detail.get("stck_prpr", 0)) <= 0:
            detail = get_us_current_price_public(stock_code)
        return detail
    return get_current_price(stock_code)


def get_premarket_price_snapshot_by_market(stock_code: str, market: str) -> dict:
    if market == "US":
        return get_current_price_by_market(stock_code, market)
    return get_premarket_price_snapshot(stock_code)


def get_screening_candidates(market: str) -> list:
    if market == "US":
        return get_us_candidates()

    source_limit = max(30, _to_int(getattr(cfg, "SCREENING_SOURCE_LIMIT", 120)))
    candidates = {}
    for item in get_volume_rank()[:source_limit]:
        code = item.get("mksc_shrn_iscd", "")
        name = item.get("hts_kor_isnm", code)
        change_rate = _to_float(item.get("prdy_ctrt", 0))
        if code and code not in candidates:
            candidates[code] = (name, change_rate)
    for item in get_fluctuation_rank()[:source_limit]:
        code = item.get("stck_shrn_iscd", "")
        name = item.get("hts_kor_isnm", code)
        change_rate = _to_float(item.get("prdy_ctrt", 0))
        if code and code not in candidates:
            candidates[code] = (name, change_rate)

    return [{"code": c, "name": n, "change_rate": r} for c, (n, r) in candidates.items()]


def get_intraday_minute_candles_by_market(stock_code: str, market: str, count: int = 30) -> list[dict]:
    if market == "US":
        return []
    return get_intraday_minute_candles(stock_code, count=count)


def get_available_cash_by_market(stock_code: str, price: int, market: str) -> int:
    if market == "US":
        return get_us_available_cash(stock_code, price)
    return get_available_cash(stock_code, price)


def buy_market_order_by_market(stock_code: str, qty: int, market: str) -> dict:
    if market == "US":
        return buy_us_market_order(stock_code, qty)
    return buy_market_order(stock_code, qty)


def sell_market_order_by_market(stock_code: str, qty: int, market: str) -> dict:
    if market == "US":
        return sell_us_market_order(stock_code, qty)
    return sell_market_order(stock_code, qty)


def get_today_realized_pnl_by_market(market: str) -> int:
    if market == "US":
        # 현재 코드베이스는 국내 계좌 기준 브리핑/손익 로직 중심
        return 0
    return get_today_realized_pnl_kr()


def get_order_fills_by_market(order_no: str, market: str) -> dict:
    if market == "US":
        return {
            "order_no": str(order_no or ""),
            "filled_qty": 0,
            "ordered_qty": 0,
            "remaining_qty": 0,
            "avg_fill_price": 0,
            "status": "none",
        }
    return get_order_fills_kr(order_no)