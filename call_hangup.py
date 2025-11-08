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
        line = f"[{ts}] [call_update_vocal.py] {message}\n"
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
    statut = env.get("agi_arg_4") or "aucune_reponse_hors_horaires"
    audio_path = env.get("agi_arg_5")

    if poste is None or poste == "":
        poste_val = None
    else:
        poste_val = poste

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
        "poste_appel": poste_val,
        "statut_appel": statut,
        "duree_appel": duree_val
    }
    payload_str = json.dumps(payload_obj)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "asterisk-agi/1.0"
    }

    data = {
        "data": payload_str
    }

    files = {}
    audio_file = None
    if audio_path and os.path.exists(audio_path):
        try:
            audio_file = open(audio_path, "rb")
            files["files.message_vocal"] = (os.path.basename(audio_path), audio_file, "audio/wav")
        except Exception as e:
            _log(f"Cannot open audio file {audio_path}: {e}")

    try:
        _log(f"[call_hangup.py] REQUEST: PUT {url} payload={payload_obj} audio_path={audio_path}")
        request_kwargs = {
            "headers": headers,
            "data": data,
            "timeout": TIMEOUT,
            "verify": VERIFY_TLS
        }
        if files:
            request_kwargs["files"] = files
        r = requests.put(url, **request_kwargs)
        preview = r.text[:400].replace("\n", " ")
        _log(f"[call_hangup.py] RESPONSE: status={r.status_code} body_preview={preview}")
        _agi_verbose(f"PUT {url} -> {r.status_code}: {preview}")
        _agi_setvar("UPDATE_STATUS", r.status_code)
        _log(f"[call_hangup.py] UPDATE_STATUS: {r.status_code}")
    except Exception as e:
        _agi_verbose(f"HTTP error: {e}")
    finally:
        if audio_file:
            try:
                audio_file.close()
            except Exception:
                pass

    sys.exit(0)

if __name__ == "__main__":
    main()
