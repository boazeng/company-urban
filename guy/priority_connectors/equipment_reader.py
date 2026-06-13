"""Priority Cloud OData equipment reader for Guy's bot engine.

Ported from urbangroup's 600-equipment agent, stripped of urbangroup path/dotenv
coupling. Identifies a customer's parking equipment by matching their WhatsApp
phone number against PHONENUM in Priority's SERNUMBERS entity.

Wired into the engine via BOT_EQUIPMENT_READER_MODULE behind
EQUIPMENT_READER_ENABLED (see agents/bot_engine/integrations.py). Credentials
come from the Lambda environment: PRIORITY_URL_REAL / PRIORITY_USERNAME /
PRIORITY_PASSWORD.

Exposes the interface the engine expects:
  fetch_equipment_by_phone(phone) -> list[dict]
  fetch_equipment_by_sernum(sernum) -> dict | None
"""

import os
import re
import logging

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("guy.priority.equipment")

PRIORITY_URL = (os.getenv("PRIORITY_URL_REAL") or os.getenv("PRIORITY_URL", "")).rstrip("/")
PRIORITY_USERNAME = os.getenv("PRIORITY_USERNAME", "")
PRIORITY_PASSWORD = os.getenv("PRIORITY_PASSWORD", "")

EQUIPMENT_FIELDS = (
    "SERNUM,PARTNAME,PARTDES,CUSTNAME,CDES,PHONENUM,"
    "STATUSNAME,FAMILYNAME,FAMILYDES,FACILITYNAME,FACILITYDES"
)


def _phone_variants(phone):
    """Priority stores phone numbers inconsistently (+972…, 054-…, 0542…);
    build every format we might need to match. WhatsApp sends '972542777757'."""
    digits = re.sub(r"[^0-9]", "", phone or "")
    if digits.startswith("972") and len(digits) > 9:
        local9 = digits[3:]
    elif digits.startswith("0") and len(digits) >= 9:
        local9 = digits[1:]
    else:
        local9 = digits
    variants = set()
    if len(local9) == 9:
        variants.add(f"+972{local9}")            # +972542777757
        variants.add(f"0{local9}")               # 0542777757
        variants.add(f"0{local9[:2]}-{local9[2:]}")  # 054-2777757
    if digits:
        variants.add(digits)                     # original digits, fallback
    return variants


def _to_device(rec):
    return {
        "sernum": rec.get("SERNUM", ""),
        "partname": rec.get("PARTNAME", ""),
        "partdes": rec.get("PARTDES", ""),
        "custname": rec.get("CUSTNAME", ""),
        "cdes": rec.get("CDES", ""),
        "phonenum": rec.get("PHONENUM", ""),
        "statusname": rec.get("STATUSNAME", ""),
        "familyname": rec.get("FAMILYNAME", ""),
        "familydes": rec.get("FAMILYDES", ""),
        "facilityname": rec.get("FACILITYNAME", ""),
        "facilitydes": rec.get("FACILITYDES", ""),
    }


def _query(filter_expr):
    url = f"{PRIORITY_URL}/SERNUMBERS"
    params = {"$filter": filter_expr, "$select": EQUIPMENT_FIELDS}
    headers = {"Accept": "application/json", "OData-Version": "4.0"}
    auth = HTTPBasicAuth(PRIORITY_USERNAME, PRIORITY_PASSWORD)
    r = requests.get(url, params=params, headers=headers, auth=auth, timeout=15)
    r.raise_for_status()
    return r.json().get("value", [])


def fetch_equipment_by_phone(phone):
    """Return active devices for a customer phone (empty list on miss/error)."""
    variants = _phone_variants(phone)
    if not variants:
        return []
    or_clauses = " or ".join(f"PHONENUM eq '{v}'" for v in variants)
    try:
        records = _query(f"({or_clauses})")
    except requests.exceptions.RequestException as e:
        logger.error(f"Priority API error (phone {phone}): {e}")
        return []
    devices = [_to_device(r) for r in records if r.get("STATUSNAME") != "Reject"]
    logger.info(f"Found {len(devices)} active device(s) for phone {phone}")
    return devices


def fetch_equipment_by_sernum(sernum):
    """Look up a single device by serial number (None on miss/error).

    Uses $filter (not an OData key) so leading-zero serials like '00008' work."""
    if not sernum:
        return None
    try:
        records = _query(f"SERNUM eq '{sernum}'")
    except requests.exceptions.RequestException as e:
        logger.error(f"Priority API error (sernum {sernum}): {e}")
        return None
    return _to_device(records[0]) if records else None
