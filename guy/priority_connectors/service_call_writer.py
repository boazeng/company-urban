"""Priority Cloud OData service-call writer for Guy's bot engine.

Ported from urbangroup's 300-service-call agent, stripped of urbangroup
path/dotenv/CLI coupling. Creates a real service call (קריאת שירות) in Priority,
finds open calls for a device, and appends notes to an existing call.

Wired into the engine via BOT_SERVICE_CALL_WRITER_MODULE behind
SERVICE_CALL_WRITER_ENABLED (see agents/bot_engine/integrations.py). Credentials
come from the Lambda environment: PRIORITY_URL_REAL / PRIORITY_USERNAME /
PRIORITY_PASSWORD.

Exposes the interface the engine expects:
  create_service_call(data) -> dict   (includes DOCNO)
  find_open_service_calls(sernum) -> list
  append_note_to_service_call(docno, note) -> bool
"""

import os
import json
import base64
import logging
from datetime import datetime, timezone, timedelta

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("guy.priority.servicecall")

# Israel Standard Time = UTC+2. Priority treats datetimes as local time, so we
# send Israeli local time with the Z suffix Priority expects.
_ISRAEL_TZ = timezone(timedelta(hours=2))

PRIORITY_URL = (os.getenv("PRIORITY_URL_REAL") or os.getenv("PRIORITY_URL", "")).rstrip("/")
PRIORITY_USERNAME = os.getenv("PRIORITY_USERNAME", "")
PRIORITY_PASSWORD = os.getenv("PRIORITY_PASSWORD", "")


def _auth():
    return HTTPBasicAuth(PRIORITY_USERNAME, PRIORITY_PASSWORD)


def _israel_now():
    return datetime.now(_ISRAEL_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")


def customer_exists(custname):
    url = f"{PRIORITY_URL}/CUSTOMERS('{custname}')"
    headers = {"Accept": "application/json", "OData-Version": "4.0"}
    try:
        return requests.get(url, headers=headers, auth=_auth(), timeout=10).status_code == 200
    except Exception:
        return False


def sernum_exists(sernum):
    """$filter (not key URL) so leading zeros/dashes like '008-501' work."""
    url = f"{PRIORITY_URL}/SERNUMBERS"
    params = {"$filter": f"SERNUM eq '{sernum}'", "$select": "SERNUM"}
    headers = {"Accept": "application/json", "OData-Version": "4.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, auth=_auth(), timeout=10)
        return len(resp.json().get("value", [])) > 0
    except Exception:
        return False


def find_open_service_calls(sernum):
    """Open service calls for a device serial → list of {DOCNO, CALLSTATUSCODE, STARTDATE, CDES}."""
    url = f"{PRIORITY_URL}/DOCUMENTS_Q"
    params = {
        "$filter": f"SERNUM eq '{sernum}' and ACTIVEFLAG eq 'Y'",
        "$select": "DOCNO,CALLSTATUSCODE,STARTDATE,CDES",
        "$top": "5",
    }
    headers = {"Accept": "application/json", "OData-Version": "4.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, auth=_auth(), timeout=10)
        if resp.status_code != 200:
            logger.warning(f"find_open_service_calls HTTP {resp.status_code} for {sernum}")
            return []
        return resp.json().get("value", [])
    except Exception as e:
        logger.warning(f"find_open_service_calls failed for {sernum}: {e}")
        return []


def append_note_to_service_call(docno, note_text):
    """Append a note to an existing call's fault text (and attach as a file). bool."""
    base_url = f"{PRIORITY_URL}/DOCUMENTS_Q(DOCNO='{docno}',TYPE='Q')"
    headers = {"Content-Type": "application/json", "Accept": "application/json", "OData-Version": "4.0"}

    existing_html = ""
    try:
        resp = requests.get(f"{base_url}/DOCTEXT_Q_2_SUBFORM", headers=headers, auth=_auth(), timeout=10)
        if resp.status_code == 200:
            existing_html = resp.json().get("TEXT", "")
    except Exception as e:
        logger.warning(f"Failed to read existing text for {docno}: {e}")

    note_html = "<br>".join(line for line in note_text.split("\n") if line.strip())
    combined = (existing_html.rstrip() + '<br><b>---</b><br>' + note_html) if existing_html else note_html

    try:
        resp = requests.post(f"{base_url}/DOCTEXT_Q_2_SUBFORM", json={"TEXT": combined},
                             headers=headers, auth=_auth(), timeout=15)
        if resp.status_code not in (200, 201):
            logger.warning(f"Failed to update fault text for {docno}: {resp.status_code}")
            return False
    except Exception as e:
        logger.warning(f"Failed to update fault text for {docno}: {e}")
        return False

    try:  # best-effort file attachment for the audit trail
        encoded = base64.b64encode(note_text.encode("utf-8")).decode("ascii")
        requests.post(f"{base_url}/EXTFILES_SUBFORM", json={
            "EXTFILEDES": "עדכון מהבוט",
            "EXTFILENAME": f"data:text/plain;base64,{encoded}",
            "SUFFIX": ".txt",
        }, headers=headers, auth=_auth(), timeout=15)
    except Exception:
        pass
    return True


def create_service_call(service_call_data):
    """Create a service call in Priority (DOCUMENTS_Q). Returns the response dict (with DOCNO).

    Validates the customer/serial against Priority (falls back to 99999 / skips
    SERNUM when not found), sets Israeli STARTDATE, and writes the fault text.
    """
    url = f"{PRIORITY_URL}/DOCUMENTS_Q"
    headers = {"Content-Type": "application/json", "Accept": "application/json", "OData-Version": "4.0"}

    branchname = service_call_data.get("branchname", "001")
    custname = service_call_data.get("custname", "99999")
    if not custname or custname == "99999" or not customer_exists(custname):
        custname = "99999"

    body = {"CUSTNAME": custname, "BRANCHNAME": branchname, "STARTDATE": _israel_now()}

    callstatus = service_call_data.get("callstatuscode", "")
    if callstatus:
        body["CALLSTATUSCODE"] = callstatus

    for dynamo_key, priority_key in [
        ("technicianlogin", "TECHNICIANLOGIN"),
        ("contact_name", "NAME"),
        ("phone", "PHONENUM"),
        ("partname", "PARTNAME"),
    ]:
        val = service_call_data.get(dynamo_key, "")
        if val:
            body[priority_key] = val

    sernum = service_call_data.get("sernum", "")
    if sernum and sernum_exists(sernum):
        body["SERNUM"] = sernum

    if service_call_data.get("is_system_down"):
        body["BREAKSTART"] = _israel_now()

    fault_desc = service_call_data.get("fault_text", "") or service_call_data.get("description", "")
    details_parts = []
    if fault_desc:
        details_parts.append(fault_desc[:22])
    location = service_call_data.get("location", "")
    if location:
        details_parts.append(location)
    if details_parts:
        body["DETAILS"] = " | ".join(details_parts)

    text_parts = [service_call_data.get(k, "") for k in ("fault_text", "internal_notes")]
    text_parts = [t for t in text_parts if t]
    if not text_parts and service_call_data.get("description"):
        text_parts.append(service_call_data["description"])
    if text_parts:
        body["DOCTEXT_Q_2_SUBFORM"] = {"TEXT": "\n".join(text_parts)}

    logger.info(f"Sending service call to Priority: {json.dumps(body, ensure_ascii=False)}")
    response = requests.post(url, json=body, headers=headers, auth=_auth())
    if response.status_code >= 400:
        try:
            err = response.json().get("FORM", {}).get("InterfaceErrors", {}).get("text", "")
        except Exception:
            err = response.text[:300]
        logger.error(f"Priority API error {response.status_code}: {err}")
        raise RuntimeError(err or f"Priority API error {response.status_code}")

    result = response.json()
    logger.info(f"Service call created: DOCNO={result.get('DOCNO', '')}")
    return result
