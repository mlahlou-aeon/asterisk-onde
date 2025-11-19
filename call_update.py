#!/var/lib/asterisk/agi-bin/HNO/myenv/bin/python3
import sys
import json
import requests
import re
import os
import datetime
from dotenv import load_dotenv

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
        line = f"[{ts}] [call_update.py] {message}\n"
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
        return sys.stdin.readline().strip()
    except Exception:
        return ""

def _agi_verbose(msg: str, level: int = 1):
    safe = msg.replace('"', '\\"')
    return _agi_cmd(f'VERBOSE "{safe}" {level}')

def _agi_getvar(name: str):
    resp = _agi_cmd(f'GET VARIABLE {name}')
    m = re.search(r"\((.*)\)", resp)
    return m.group(1) if m else ""

def _agi_setvar(name: str, value):
    safe = str(value).replace('"', '\\"')
    return _agi_cmd(f'SET VARIABLE {name} "{safe}"')

def main():
    env = _read_agi_env()
    call_id = env.get("agi_arg_1") or _agi_getvar("CALL_IDENTIFIER")
    poste = env.get("agi_arg_2")
    duree_raw = env.get("agi_arg_3")
    statut = env.get("agi_arg_4") or "termine"

    _log(f"[call_update.py] statut is '{statut}'")

    if duree_raw is None or duree_raw == "":
        duree_val = None
    else:
        try:
            duree_val = int(str(duree_raw))
        except Exception:
            duree_val = 0

    if not call_id:
        _agi_verbose("Missing CALL_IDENTIFIER")
        sys.exit(0)

    url = f"{API_BASE}/{call_id}"
    payload_obj = {
        "poste_appel": poste,
        "statut_appel": statut,
        "duree_appel": duree_val
    }
    payload_str = json.dumps(payload_obj)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "asterisk-agi/1.0"
    }
    files = {
        "data": (None, payload_str, "application/json")
    }

    try:
        _log(f"REQUEST: PUT {url} payload={payload_obj}")
        r = requests.put(url, headers=headers, files=files, timeout=TIMEOUT, verify=VERIFY_TLS)
        preview = r.text[:400].replace("\n", " ")
        _log(f"RESPONSE: status={r.status_code} body_preview={preview}")
        _agi_verbose(f"PUT {url} -> {r.status_code}: {preview}")
        _agi_setvar("UPDATE_STATUS", r.status_code)
        _log(f"UPDATE_STATUS: {r.status_code}")
    except Exception as e:
        _agi_verbose(f"HTTP error: {e}")

    sys.exit(0)

if __name__ == "__main__":
    main()
