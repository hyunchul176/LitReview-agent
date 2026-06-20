"""OpenAlex 조회·수집.

무료, API 키 불필요. .env 의 OPENALEX_EMAIL 을 넣으면 polite pool 로 더 빠르고 안정적.

기능:
  - DOI / OpenAlex ID / 검색어로 논문 메타데이터 조회
  - 인용 그래프 확장(--expand): 이 논문을 인용한 논문(forward) + 참고문헌 수(backward)
  - 무료 공개본(OA) PDF 위치 탐지, --download 로 papers/ 에 저장
  - --add 로 library.json 에 등록 (DOI / OpenAlex ID 기준 중복 제거)

사용 예:
  python scripts/fetch_openalex.py "NLOS UWB localization deep learning" --list 5
  python scripts/fetch_openalex.py 10.1109/JIOT.2020.1234567 --expand --add
  python scripts/fetch_openalex.py 10.1038/nature14539 --download
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv 미설치여도 동작 (키 없이 OpenAlex 가능)
    pass

# 윈도우 콘솔(cp949 등)에서 특수문자 출력 시 크래시 방지 — UTF-8 고정
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

API = "https://api.openalex.org"
ROOT = Path(__file__).resolve().parent.parent
PAPERS_DIR = ROOT / "papers"
LIBRARY = ROOT / "library.json"
EMAIL = os.getenv("OPENALEX_EMAIL", "").strip()
TIMEOUT = 30


def _params(extra=None):
    p = dict(extra or {})
    if EMAIL:
        p["mailto"] = EMAIL
    return p


def _get(url, params=None):
    ua = f"research-agent (mailto:{EMAIL})" if EMAIL else "research-agent"
    r = requests.get(url, params=_params(params), timeout=TIMEOUT, headers={"User-Agent": ua})
    r.raise_for_status()
    return r.json()


def _looks_like_doi(s: str) -> bool:
    return s.startswith("10.") or "doi.org/" in s or s.lower().startswith("doi:")


def _norm_doi(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:", "", s, flags=re.I)
    return s


def fetch_work(query: str):
    """DOI / OpenAlex ID / 검색어 → 단일 work(dict) 또는 None."""
    if query.startswith("https://openalex.org/") or re.match(r"^W\d+$", query):
        wid = query.rsplit("/", 1)[-1]
        return _get(f"{API}/works/{wid}")
    if _looks_like_doi(query):
        return _get(f"{API}/works/doi:{_norm_doi(query)}")
    results = _get(f"{API}/works", {"search": query, "per_page": 1}).get("results", [])
    return results[0] if results else None


def search_works(query: str, limit: int):
    return _get(f"{API}/works", {"search": query, "per_page": limit}).get("results", [])


def _authors(work, n=3):
    names = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])]
    names = [x for x in names if x]
    if len(names) > n:
        return ", ".join(names[:n]) + f" 외 {len(names) - n}명"
    return ", ".join(names) if names else "(저자 미상)"


def _venue(work):
    src = (work.get("primary_location") or {}).get("source") or {}
    return src.get("display_name") or "(출처 미상)"


def _oa_pdf(work):
    best = work.get("best_oa_location") or {}
    return best.get("pdf_url") or (work.get("open_access") or {}).get("oa_url")


def _doi_of(work):
    d = work.get("doi") or ""
    return _norm_doi(d) if d else ""


def _wid(work):
    return (work.get("id") or "").rsplit("/", 1)[-1]


def print_work(work):
    print(f"  제목 : {work.get('display_name', '(제목 없음)')}")
    print(f"  저자 : {_authors(work)}")
    print(f"  연도 : {work.get('publication_year', '?')}   출처: {_venue(work)}")
    print(f"  DOI  : {_doi_of(work) or '(없음)'}")
    print(f"  인용수: {work.get('cited_by_count', '?')}   참고문헌: {len(work.get('referenced_works', []))}편")
    if (work.get("open_access") or {}).get("is_oa"):
        print(f"  무료본: 있음 → {_oa_pdf(work) or '(PDF 링크 미확인)'}")
    else:
        print("  무료본: 없음 (기관 키/브라우저 필요)")


def expand(work, limit=5):
    wid = _wid(work)
    if not wid:
        return
    print(f"\n  ↑ 이 논문을 인용한 논문 (forward, 인용수 상위 {limit}편):")
    try:
        data = _get(f"{API}/works", {"filter": f"cites:{wid}", "per_page": limit, "sort": "cited_by_count:desc"})
        results = data.get("results", [])
        for w in results:
            print(f"    - [{w.get('publication_year', '?')}] {w.get('display_name', '')[:78]}  doi:{_doi_of(w) or '-'}")
        if not results:
            print("    (없음)")
    except Exception as e:
        print(f"    (조회 실패: {e})")
    print(f"  ↓ 참고문헌(backward): {len(work.get('referenced_works', []))}편 — 스노우볼링 시드로 사용 가능")


def load_library():
    if LIBRARY.exists():
        try:
            return json.loads(LIBRARY.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema": 1, "papers": []}


def add_to_library(work):
    lib = load_library()
    papers = lib.setdefault("papers", [])
    wid, doi = _wid(work), _doi_of(work)
    for p in papers:
        if (doi and p.get("doi") == doi) or (wid and p.get("openalex_id") == wid):
            print("  · library.json: 이미 있음 (중복 제외)")
            return
    papers.append({
        "openalex_id": wid,
        "doi": doi,
        "title": work.get("display_name", ""),
        "year": work.get("publication_year"),
        "venue": _venue(work),
        "oa_pdf": _oa_pdf(work),
        "source": "openalex",
    })
    LIBRARY.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  · library.json: 추가됨 (총 {len(papers)}편)")


def download_pdf(work):
    pdf = _oa_pdf(work)
    if not pdf:
        print("  · 다운로드: 무료 PDF 없음 — 건너뜀 (기관 키/브라우저 필요)")
        return
    PAPERS_DIR.mkdir(exist_ok=True)
    out = PAPERS_DIR / f"{_wid(work) or 'work'}.pdf"
    try:
        r = requests.get(pdf, timeout=TIMEOUT, headers={"User-Agent": "research-agent"})
        r.raise_for_status()
        out.write_bytes(r.content)
        print(f"  · 다운로드: {out}  ({len(r.content) // 1024} KB)")
    except Exception as e:
        print(f"  · 다운로드 실패: {e}")


def main():
    ap = argparse.ArgumentParser(description="OpenAlex 조회·수집")
    ap.add_argument("query", help="DOI, OpenAlex ID, 또는 검색어")
    ap.add_argument("--list", type=int, metavar="N", help="검색 결과를 N개 나열 (단건 조회 대신)")
    ap.add_argument("--expand", action="store_true", help="인용 그래프 확장 (forward/backward)")
    ap.add_argument("--add", action="store_true", help="library.json 에 등록")
    ap.add_argument("--download", action="store_true", help="무료 PDF가 있으면 papers/ 에 저장")
    args = ap.parse_args()

    if not EMAIL:
        print("[!] OPENALEX_EMAIL 미설정 — 동작은 하지만 .env 에 넣으면 더 안정적", file=sys.stderr)

    try:
        if args.list:
            works = search_works(args.query, args.list)
            print(f"[OpenAlex] '{args.query}' 검색 결과 {len(works)}편:\n")
            for i, w in enumerate(works, 1):
                print(f"[{i}]")
                print_work(w)
                print()
            return
        work = fetch_work(args.query)
        if not work:
            print("결과 없음.")
            return
        print("[OpenAlex] 논문:")
        print_work(work)
        if args.expand:
            expand(work)
        if args.add:
            add_to_library(work)
        if args.download:
            download_pdf(work)
    except requests.HTTPError as e:
        print(f"[HTTP 오류] {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[네트워크 오류] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
