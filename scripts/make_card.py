"""정독 카드(HTML) 생성.

정독가(reader)가 추출한 6파트 내용(JSON)을 일관된 HTML 카드로 만들어 research/ 에 저장한다.
형식을 스크립트가 고정하므로, 누가 어떤 논문을 정독해도 카드 모양이 같다.

JSON 스키마 (대부분 생략 가능):
{
  "title": "...", "authors": ["..."], "year": "2017", "venue": "ICLR (arXiv)",
  "doi": "", "arxiv_id": "1707.01926", "url": "https://...",
  "tags": ["..."], "highlights": ["핵심 한 문장", ...],
  "background": "...",      # 연구 배경
  "contribution": "...",    # 무엇을 했나
  "method": "...",          # 방법론 상세
  "results": "...",         # 결과
  "limitations": "...",     # 한계
  "relation": "..."         # 본 연구와의 관계 (가장 중요, 빨강 강조)
}
각 섹션 값은 문자열(빈 줄로 문단 구분) 또는 문자열 리스트(불릿)로 줄 수 있다.

사용 예:
  python scripts/make_card.py --input card.json
  python scripts/make_card.py --input card.json --out research/dcrnn.html
  cat card.json | python scripts/make_card.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from _common import ROOT

RESEARCH_DIR = ROOT / "research"

SECTIONS = [
    ("background", "연구 배경"),
    ("contribution", "무엇을 했나"),
    ("method", "방법론 상세"),
    ("results", "결과"),
    ("limitations", "한계"),
    ("relation", "본 연구와의 관계"),
]

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<style>
  :root{--navy-900:#0c1f3d;--navy-700:#1d3a5f;--navy-600:#2f5a8a;--navy-800:#13294b;--ink:#17202d;--muted:#5d6878;--line:#e3e9f2;--red:#d12f3c;--red-050:#fdeef0;--font:"Pretendard Variable",Pretendard,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;}
  *{box-sizing:border-box;}
  body{margin:0;background:#f4f7fc;color:var(--ink);font-family:var(--font);line-height:1.72;font-size:16px;-webkit-font-smoothing:antialiased;}
  .card{max-width:820px;margin:32px auto;background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 16px 40px -28px rgba(12,31,61,.5);}
  .head{background:linear-gradient(135deg,var(--navy-900),var(--navy-700));color:#fff;padding:30px 34px;}
  .head h1{margin:0 0 10px;font-size:23px;line-height:1.32;font-weight:800;letter-spacing:-.01em;}
  .meta{font-size:13.5px;color:#c4d2e6;line-height:1.65;}
  .meta a{color:#9ecbff;text-decoration:none;}
  .tags{margin-top:13px;display:flex;flex-wrap:wrap;gap:6px;}
  .tag{font-size:11.5px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:#dde7f5;padding:3px 10px;border-radius:999px;}
  .body{padding:8px 34px 30px;}
  .hl{background:var(--red-050);border:1px solid #f3c9cd;border-radius:11px;padding:14px 18px;margin:22px 0 6px;}
  .hl .lbl{font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:#a81b27;margin-bottom:7px;}
  .hl ul{margin:0;padding-left:18px;}
  .hl li{margin-bottom:5px;font-size:14.5px;color:#5c2a30;}
  section{margin-top:24px;}
  h2{font-size:16px;color:var(--navy-800);font-weight:750;margin:0 0 8px;display:flex;align-items:center;gap:9px;}
  h2::before{content:"";width:4px;height:16px;background:var(--navy-600);border-radius:3px;}
  section.relation{background:#fbfcfe;border:1px solid var(--line);border-left:4px solid var(--red);border-radius:11px;padding:16px 20px 6px;margin-top:28px;}
  section.relation h2{color:var(--red);}
  section.relation h2::before{display:none;}
  p{margin:0 0 10px;}
  ul{margin:0 0 10px;padding-left:20px;}
  li{margin-bottom:5px;}
  .empty{color:var(--muted);font-style:italic;}
  footer{padding:16px 34px 24px;border-top:1px solid var(--line);color:var(--muted);font-size:12px;}
</style>
</head>
<body>
<article class="card">
  <div class="head">
    <h1>__TITLE__</h1>
    <div class="meta">__META__</div>
    __TAGS__
  </div>
  <div class="body">
    __HIGHLIGHTS__
    __SECTIONS__
  </div>
  <footer>정독 카드 · 연구 아이디어 &amp; 문헌조사 에이전트</footer>
</article>
</body>
</html>
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def render_content(val) -> str:
    if not val:
        return '<p class="empty">(내용 없음)</p>'
    if isinstance(val, list):
        items = "".join(f"<li>{esc(x)}</li>" for x in val if str(x).strip())
        return f"<ul>{items}</ul>" if items else '<p class="empty">(내용 없음)</p>'
    paras = re.split(r"\n\s*\n", str(val).strip())
    rendered = "".join(f"<p>{esc(p.strip())}</p>" for p in paras if p.strip())
    return rendered or '<p class="empty">(내용 없음)</p>'


def render_meta(d) -> str:
    parts = []
    authors = d.get("authors") or []
    if authors:
        parts.append(esc(", ".join(authors[:6]) + (" 외" if len(authors) > 6 else "")))
    yv = " · ".join(x for x in [str(d.get("year") or "").strip(), str(d.get("venue") or "").strip()] if x)
    if yv:
        parts.append(esc(yv))
    links = []
    if d.get("doi"):
        links.append(f'<a href="https://doi.org/{esc(d["doi"])}">DOI: {esc(d["doi"])}</a>')
    if d.get("arxiv_id"):
        links.append(f'<a href="https://arxiv.org/abs/{esc(d["arxiv_id"])}">arXiv: {esc(d["arxiv_id"])}</a>')
    if d.get("url"):
        links.append(f'<a href="{esc(d["url"])}">원문 링크</a>')
    if links:
        parts.append(" · ".join(links))
    return "<br>".join(parts) or "(서지정보 없음)"


def render_tags(d) -> str:
    tags = [t for t in (d.get("tags") or []) if str(t).strip()]
    if not tags:
        return ""
    return '<div class="tags">' + "".join(f'<span class="tag">{esc(t)}</span>' for t in tags) + "</div>"


def render_highlights(d) -> str:
    hs = [h for h in (d.get("highlights") or []) if str(h).strip()]
    if not hs:
        return ""
    items = "".join(f"<li>{esc(h)}</li>" for h in hs)
    return f'<div class="hl"><div class="lbl">핵심</div><ul>{items}</ul></div>'


def render_sections(d) -> str:
    out = []
    for key, label in SECTIONS:
        cls = "relation" if key == "relation" else ""
        out.append(f'<section class="{cls}"><h2>{esc(label)}</h2>{render_content(d.get(key))}</section>')
    return "\n    ".join(out)


def slugify(d) -> str:
    base = d.get("arxiv_id") or d.get("doi") or d.get("title") or "card"
    s = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", str(base)).strip("-").lower()
    return (s or "card")[:60]


def main():
    ap = argparse.ArgumentParser(description="정독 카드(HTML) 생성")
    ap.add_argument("--input", help="JSON 경로 (없으면 stdin)")
    ap.add_argument("--out", help="출력 HTML 경로 (기본: research/<slug>.html)")
    args = ap.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)

    if not d.get("title"):
        print("[!] title 이 없습니다 — '(제목 없음)'으로 생성합니다.", file=sys.stderr)

    out_html = (TEMPLATE
                .replace("__TITLE__", esc(d.get("title") or "(제목 없음)"))
                .replace("__META__", render_meta(d))
                .replace("__TAGS__", render_tags(d))
                .replace("__HIGHLIGHTS__", render_highlights(d))
                .replace("__SECTIONS__", render_sections(d)))

    out = Path(args.out) if args.out else RESEARCH_DIR / f"{slugify(d)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_html, encoding="utf-8")
    print(f"정독 카드 생성: {out}")


if __name__ == "__main__":
    main()
