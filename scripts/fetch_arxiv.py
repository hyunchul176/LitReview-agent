"""arXiv 검색·다운로드.

키 불필요. 검색어 또는 arXiv ID로 논문을 찾아 메타데이터를 보여주고,
--download 로 풀텍스트 PDF를 papers/ 에 저장, --add 로 library.json 에 등록.

사용 예:
  python scripts/fetch_arxiv.py "traffic flow forecasting graph neural network" --list 5
  python scripts/fetch_arxiv.py 2301.12345 --download --add
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET

import requests

from _common import PAPERS_DIR, add_paper, download_file, norm_doi

API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARX = "{http://arxiv.org/schemas/atom}"
TIMEOUT = 30
ARXIV_ID = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$", re.I)


def _query(params):
    r = requests.get(API, params=params, timeout=TIMEOUT, headers={"User-Agent": "research-agent"})
    r.raise_for_status()
    return ET.fromstring(r.text)


def _short_id(entry):
    raw = entry.findtext(f"{ATOM}id", "") or ""   # http://arxiv.org/abs/2301.12345v1
    return raw.rsplit("/abs/", 1)[-1] if "/abs/" in raw else raw.rsplit("/", 1)[-1]


def _pdf_url(entry, sid):
    for link in entry.findall(f"{ATOM}link"):
        if link.get("title") == "pdf":
            return link.get("href")
    return f"https://arxiv.org/pdf/{sid}"


def parse(entry):
    sid = _short_id(entry)
    authors = [a.findtext(f"{ATOM}name", "") for a in entry.findall(f"{ATOM}author")]
    return {
        "arxiv_id": sid,
        "title": " ".join((entry.findtext(f"{ATOM}title", "") or "").split()),
        "authors": [a for a in authors if a],
        "year": (entry.findtext(f"{ATOM}published", "") or "")[:4],
        "doi": norm_doi(entry.findtext(f"{ARX}doi", "") or ""),
        "pdf_url": _pdf_url(entry, sid),
    }


def _authors_str(authors, n=3):
    if not authors:
        return "(저자 미상)"
    return ", ".join(authors[:n]) + (f" 외 {len(authors) - n}명" if len(authors) > n else "")


def print_entry(e):
    print(f"  제목 : {e['title']}")
    print(f"  저자 : {_authors_str(e['authors'])}")
    print(f"  연도 : {e['year']}   arXiv: {e['arxiv_id']}   DOI: {e['doi'] or '(없음)'}")
    print(f"  PDF  : {e['pdf_url']}")


def _lib_entry(e):
    return {
        "arxiv_id": e["arxiv_id"], "doi": e["doi"], "title": e["title"],
        "year": e["year"], "venue": "arXiv", "oa_pdf": e["pdf_url"], "source": "arxiv",
    }


def download(e):
    PAPERS_DIR.mkdir(exist_ok=True)
    out = PAPERS_DIR / f"arxiv_{e['arxiv_id'].replace('/', '_')}.pdf"
    try:
        n = download_file(e["pdf_url"], out)
        print(f"  · 다운로드: {out}  ({n // 1024} KB)")
    except Exception as ex:
        print(f"  · 다운로드 실패: {ex}")


def main():
    ap = argparse.ArgumentParser(description="arXiv 검색·다운로드")
    ap.add_argument("query", help="검색어 또는 arXiv ID")
    ap.add_argument("--list", type=int, metavar="N", help="검색 결과 N개 나열")
    ap.add_argument("--download", action="store_true", help="PDF를 papers/ 에 저장")
    ap.add_argument("--add", action="store_true", help="library.json 에 등록")
    args = ap.parse_args()

    q = args.query.strip()
    try:
        if args.list and not ARXIV_ID.match(q):
            entries = _query({"search_query": f"all:{args.query}", "start": 0,
                              "max_results": args.list}).findall(f"{ATOM}entry")
            print(f"[arXiv] '{args.query}' 검색 결과 {len(entries)}편:\n")
            for i, en in enumerate(entries, 1):
                print(f"[{i}]")
                print_entry(parse(en))
                print()
            return

        root = _query({"id_list": q}) if ARXIV_ID.match(q) else \
            _query({"search_query": f"all:{args.query}", "start": 0, "max_results": 1})
        entries = root.findall(f"{ATOM}entry")
        if not entries:
            print("결과 없음.")
            return
        e = parse(entries[0])
        print("[arXiv] 논문:")
        print_entry(e)
        if args.add:
            added, total = add_paper(_lib_entry(e))
            print("  · library.json: " + (f"추가됨 (총 {total}편)" if added else "이미 있음 (중복 제외)"))
        if args.download:
            download(e)
    except requests.RequestException as ex:
        print(f"[네트워크 오류] {ex}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as ex:
        print(f"[파싱 오류] {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
