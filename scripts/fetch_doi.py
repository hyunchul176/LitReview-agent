"""DOI 본문 다운로드: Elsevier / Wiley.

DOI를 받아 출판사를 판별하고(Crossref), 기관 API 키로 풀텍스트 PDF를 papers/ 에 받는다.
키는 .env 에서만 읽는다. 코드/로그에 키를 출력하지 않는다.
참고: 기관 라이선스라 보통 KAIST 망(또는 적절한 인증) 환경에서만 본문이 내려온다.

  Elsevier:  GET https://api.elsevier.com/content/article/doi/{DOI}   (헤더 X-ELS-APIKey, Accept: application/pdf)
  Wiley TDM: GET https://api.wiley.com/onlinelibrary/tdm/v1/articles/{DOI}   (헤더 Wiley-TDM-Client-Token)

사용 예:
  python scripts/fetch_doi.py 10.1016/j.trc.2020.102674          # 출판사 자동 판별
  python scripts/fetch_doi.py 10.1002/rob.21918 --publisher wiley --add
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

from _common import PAPERS_DIR, add_paper, norm_doi

ELSEVIER_KEY = os.getenv("ELSEVIER_API_KEY", "").strip()
WILEY_TOKEN = os.getenv("WILEY_TDM_TOKEN", "").strip()
TIMEOUT = 60


def crossref_meta(doi):
    """Crossref로 출판사/제목/연도 조회. {} 가능."""
    try:
        m = requests.get(f"https://api.crossref.org/works/{doi}", timeout=30,
                         headers={"User-Agent": "research-agent"}).json().get("message", {})
        dp = (m.get("issued", {}) or {}).get("date-parts") or [[None]]
        year = str(dp[0][0]) if dp and dp[0] and dp[0][0] else ""
        return {"title": (m.get("title") or [""])[0], "publisher": m.get("publisher") or "", "year": year}
    except Exception:
        return {}


def detect_publisher(pub_str):
    p = (pub_str or "").lower()
    if "elsevier" in p:
        return "elsevier"
    if "wiley" in p:
        return "wiley"
    return None


def fetch_elsevier(doi, out):
    if not ELSEVIER_KEY:
        return False, "ELSEVIER_API_KEY 미설정 (.env)"
    r = requests.get(f"https://api.elsevier.com/content/article/doi/{doi}", timeout=TIMEOUT,
                     headers={"X-ELS-APIKey": ELSEVIER_KEY, "Accept": "application/pdf"})
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        out.write_bytes(r.content)
        return True, f"{len(r.content) // 1024} KB"
    return False, f"HTTP {r.status_code} (권한/네트워크 확인 — KAIST 망 필요할 수 있음)"


def fetch_wiley(doi, out):
    if not WILEY_TOKEN:
        return False, "WILEY_TDM_TOKEN 미설정 (.env)"
    r = requests.get(f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}", timeout=TIMEOUT,
                     headers={"Wiley-TDM-Client-Token": WILEY_TOKEN}, allow_redirects=True)
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        out.write_bytes(r.content)
        return True, f"{len(r.content) // 1024} KB"
    return False, f"HTTP {r.status_code} (권한/네트워크 확인 — KAIST 망 필요할 수 있음)"


def main():
    ap = argparse.ArgumentParser(description="DOI 본문 다운로드 (Elsevier/Wiley)")
    ap.add_argument("doi")
    ap.add_argument("--publisher", choices=["elsevier", "wiley"], help="출판사 직접 지정")
    ap.add_argument("--add", action="store_true", help="성공 시 library.json 등록")
    args = ap.parse_args()

    doi = norm_doi(args.doi)
    meta = {} if args.publisher else crossref_meta(doi)
    pub = args.publisher or detect_publisher(meta.get("publisher"))
    print(f"[fetch_doi] DOI={doi}  출판사={pub or meta.get('publisher') or '판별 실패'}")

    if pub is None:
        print("  Elsevier/Wiley 로 판별되지 않았습니다. --publisher 로 지정하거나,")
        print("  IEEE 등 키 없는 곳은 fetch_ieee_playwright.py 를 사용하세요.")
        sys.exit(2)

    PAPERS_DIR.mkdir(exist_ok=True)
    out = PAPERS_DIR / f"{doi.replace('/', '_')}.pdf"
    ok, info = (fetch_elsevier if pub == "elsevier" else fetch_wiley)(doi, out)
    if ok:
        print(f"  · 다운로드 성공: {out}  ({info})")
        if args.add:
            added, total = add_paper({
                "doi": doi, "title": meta.get("title", ""), "year": meta.get("year", ""),
                "venue": meta.get("publisher", pub), "oa_pdf": None, "source": pub,
            })
            print("  · library.json: " + (f"추가됨 (총 {total}편)" if added else "이미 있음"))
    else:
        print(f"  · 다운로드 실패: {info}")
        sys.exit(1)


if __name__ == "__main__":
    main()
