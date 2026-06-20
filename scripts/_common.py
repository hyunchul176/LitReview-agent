"""공용 헬퍼: 경로, library.json 입출력, 다운로드, 인코딩.

모든 fetch 스크립트가 공유한다. (python 이 스크립트 폴더를 sys.path 에 자동 추가하므로 `import _common` 가능)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 윈도우 콘솔(cp949 등)에서 특수문자 출력 시 크래시 방지 — UTF-8 고정
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv 미설치여도 키 없는 채널은 동작
    pass

ROOT = Path(__file__).resolve().parent.parent
PAPERS_DIR = ROOT / "papers"
LIBRARY = ROOT / "library.json"


def norm_doi(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:", "", s, flags=re.I)
    return s


def load_library() -> dict:
    if LIBRARY.exists():
        try:
            return json.loads(LIBRARY.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema": 1, "papers": []}


def save_library(lib: dict) -> None:
    LIBRARY.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _match(a: dict, b: dict) -> bool:
    for key in ("doi", "arxiv_id", "openalex_id"):
        if a.get(key) and a.get(key) == b.get(key):
            return True
    return False


def add_paper(entry: dict):
    """library.json 에 등록(중복 제거). (added: bool, total: int) 반환."""
    lib = load_library()
    papers = lib.setdefault("papers", [])
    for p in papers:
        if _match(entry, p):
            return False, len(papers)
    papers.append(entry)
    save_library(lib)
    return True, len(papers)


def download_file(url: str, dest: Path, headers=None, timeout: int = 60) -> int:
    """url 을 dest 로 저장하고 받은 바이트 수를 반환."""
    import requests
    r = requests.get(url, headers=headers or {"User-Agent": "research-agent"},
                     timeout=timeout, stream=True, allow_redirects=True)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                n += len(chunk)
    return n
