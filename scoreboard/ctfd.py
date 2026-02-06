import os
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("CTFD_BASE_URL")
OUT = os.getenv("CTFD_OUT")
if not BASE or not OUT:
    raise SystemExit("Thiếu biến .env: cần CTFD_BASE_URL và CTFD_OUT (xem .env.example)")
BASE = BASE.rstrip("/") + "/"
OUT = Path(OUT)

# Một số endpoint hay gặp
CANDIDATES = [
    "/api/v1/scoreboard",
    "/api/v1/scoreboard?count=1000",
    "/scoreboard?format=json",
    "/scores?format=json",
]

def looks_like_ctfd_scoreboard(obj) -> bool:
    """
    Heuristic nhận diện JSON scoreboard CTFd.
    Thường có dạng: {"success": true, "data": [...]}
    Mỗi entry thường có name/score/(pos|place|rank) ...
    """
    if not isinstance(obj, dict):
        return False
    if "data" not in obj:
        return False
    data = obj["data"]
    if not isinstance(data, list) or not data:
        return False
    if not isinstance(data[0], dict):
        return False

    keys = set(data[0].keys())
    # name + score là combo hay nhất
    return ("name" in keys or "team" in keys) and ("score" in keys or "points" in keys)

def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "scoreboard-fetch/1.0"})

    found = None
    for path in CANDIDATES:
        url = urljoin(BASE, path)
        try:
            r = s.get(url, timeout=20)
            ct = (r.headers.get("content-type") or "").lower()
            if "application/json" not in ct:
                # có server vẫn trả text/json
                if not re.search(r"json", ct):
                    continue
            obj = r.json()
            if looks_like_ctfd_scoreboard(obj):
                found = {"url": url, "data": obj}
                print("[+] Found scoreboard endpoint:", url)
                break
        except Exception:
            continue

    if not found:
        print("[-] Không tìm thấy endpoint JSON scoreboard trong danh sách thử.")
        print("   Gợi ý: thử mở /scoreboard trên trình duyệt, xem Network/XHR để biết endpoint thật.")
        return

    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[+] Saved:", OUT.resolve())

if __name__ == "__main__":
    main()
