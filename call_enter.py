#!/var/lib/asterisk/agi-bin/HNO/myenv/bin/python3
import sys
import json
import requests
import re
import os
import datetime
from dotenv import load_dotenv
import base64

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
LOG_PATH = os.path.join(BASE_DIR, "logs", "app.log")

load_dotenv(ENV_PATH)

BACKEND_URL = os.getenv("BACKEND_URL", "https://2511-onde.positif.ma")
API_BASE = f"{BACKEND_URL}/backend/api/cas-entrants/incoming-call"
TOKEN = os.getenv("BACKEND_TOKEN")
VERIFY_TLS = True
TIMEOUT = 5

def _log(message):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}\n"
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass

def _read_agi_env():
    env = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if line == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            env[k.strip()] = v.strip()
    return env

def _agi_cmd(cmd: str):
    sys.stdout.write(cmd + "\n")
    sys.stdout.flush()
    try:
        resp = sys.stdin.readline().strip()
    except Exception:
        resp = ""
    return resp

def _agi_verbose(msg: str, level: int = 1):
    safe = msg.replace('"', '\\"')
    return _agi_cmd(f'VERBOSE "{safe}" {level}')

def _agi_setvar(name: str, value):
    return _agi_cmd(f"SET VARIABLE {name} {value}")

def _agi_exec(app: str, options: str = ""):
    if options:
        return _agi_cmd(f"EXEC {app} {options}")
    else:
        return _agi_cmd(f"EXEC {app}")

def main():
    env = _read_agi_env()
    caller = env.get("agi_callerid") or env.get("agi_calleridnum") or ""
    caller = str(caller).strip()
#    caller = "0664705771"
    payload = {"data": {"tel": caller}}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "asterisk-agi/1.0",
    }
    try:
        _log(f"[call_enter.py]: POST {API_BASE} payload={payload}")
        r = requests.post(API_BASE, headers=headers, json=payload, timeout=TIMEOUT, verify=VERIFY_TLS)
        preview = r.text[:400].replace("\n", " ")
        _log(f"[call_enter.py]: RESPONSE status={r.status_code} body_preview={preview}")
        _agi_verbose(f"POST {API_BASE} -> {r.status_code}: {preview}")
        case_id = None
        caller_name = ""
        try:
            data = r.json()
            case_id = data.get("id")
            caller_name = data.get("nom") or ""
        except Exception:
            case_id = None
            caller_name = ""
        if caller_name is not None:
            b64_name = base64.b64encode(caller_name.encode("utf-8")).decode("ascii")
            resp = _agi_setvar("CALLER_NAME", str(b64_name))

        if case_id is not None:
            _log(f"[call_enter.py]: CASE_ID {case_id}")
            resp = _agi_setvar("CALL_IDENTIFIER", str(case_id))
            _agi_verbose(f"SET VARIABLE resp: {resp}")
            chk = _agi_cmd("GET VARIABLE CALL_IDENTIFIER")
            m = re.search(r"\((.*)\)", chk)
            val = m.group(1) if m else ""
            _agi_verbose(f"GET VARIABLE CALL_IDENTIFIER -> {chk} | value={val}")
        else:
            _log("[call_enter.py]: CASE_ID None")
            _agi_verbose("No caseId in response")

    except Exception as e:
        _agi_verbose(f"HTTP error: {e}")

if __name__ == "__main__":
    main()
    sys.exit(0)
