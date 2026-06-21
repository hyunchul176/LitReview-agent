"""리뷰 카드(HTML) 생성 — 고도화 버전.

정독가(reader)가 추출한 내용(JSON)을 research/assets/card.css·card.js 를 쓰는 일관된 카드로 만든다.
figure(클릭 확대), 본문 하이라이트(.mark), 영어 인용(.qt), 그림 상호참조(.figref), 다크모드를 지원한다.

JSON 스키마 (대부분 생략 가능):
{
  "title": "...", "authors": ["..."], "year": 2018, "venue": "ICLR",
  "doi": "", "arxiv_id": "1707.01926", "url": "https://...",
  "tags": ["traffic forecasting", "GNN"], "role": "기반 문헌",
  "citation": "F. Author et al. <b>Venue (2018)</b>. doi:...",   // 생략 시 위 필드로 자동 생성
  "tldr": "한눈에 ... <span class='mark'>핵심</span> ...",
  "figures": [
    {"id": "fig1", "src": "images/dcrnn_fig1.png", "label": "Fig 1 · ICC",
     "caption": "캡션(HTML 가능). (클릭 시 확대)", "alt": "스크린리더용 설명"}
  ],
  "attrs": [ {"label": "접근", "value": "인스턴스=문항 ..."} ],
  "background": "...", "contribution": "...", "method": "...|[목록]",
  "results": "...", "limitations": "...", "relation": "본 연구와의 관계 ..."
}

본문(tldr/각 섹션/relation/attr value/figure caption/citation)에는 신뢰된 작성자가 만든 HTML 조각을 그대로 넣을 수 있다(이스케이프하지 않음):
  - 하이라이트:  <span class="mark">핵심 문장</span>
  - 영어 인용:   <span class="qt">"verbatim quote"</span> <span class="qt-loc">(§4 본문)</span>   (qt-loc은 qt의 형제 span, 중첩 아님)
  - 그림 참조:   <a class="figref" href="#fig1">Fig. 1</a>   (href는 반드시 "#" + figures의 id 값)
  - 강조/이탤릭: <b>..</b> <i>..</i>
title/authors/tags/figure label·alt 는 자동 이스케이프된다.

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
SECTIONS_MAIN = [
    ("background", "연구 배경"),
    ("contribution", "무엇을 했나"),
    ("method", "방법론 상세"),
    ("results", "결과"),
    ("limitations", "한계"),
]

DOC = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<link rel="stylesheet" href="assets/card.css">
<script>(function(){try{var t=localStorage.getItem('theme')||((window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light');document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
</head>
<body>
<div class="review-wrap">
  <div class="topbar"><button class="theme-toggle" type="button">☾ 다크 모드</button></div>
  <article class="paper" id="__SLUG__">
    __ARTICLE__
  </article>
  <footer>리뷰 카드 · 연구 아이디어 &amp; 문헌조사 에이전트</footer>
</div>
<div class="lightbox" id="lightbox"><span class="lightbox-close">×</span><img alt=""><div class="lightbox-cap"></div></div>
<script src="assets/card.js"></script>
</body>
</html>
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def strip_tags(s) -> str:
    return re.sub(r"<[^>]+>", "", str(s or ""))


def render_prose(val) -> str:
    """raw HTML 통과 (신뢰된 작성자). 리스트면 <ul>, 문자열이면 빈 줄로 문단 분리."""
    if not val:
        return '<p class="empty">(내용 없음)</p>'
    if isinstance(val, list):
        items = "".join(f"<li>{x}</li>" for x in val if str(x).strip())
        return f"<ul>{items}</ul>" if items else '<p class="empty">(내용 없음)</p>'
    paras = re.split(r"\n\s*\n", str(val).strip())
    return "".join(f"<p>{p.strip()}</p>" for p in paras if p.strip()) or '<p class="empty">(내용 없음)</p>'


def build_citation(d) -> str:
    bits = []
    authors = d.get("authors") or []
    if authors:
        bits.append(esc(", ".join(authors)))
    vy = " ".join(x for x in [esc(d.get("venue") or ""), str(d.get("year") or "").strip()] if x).strip()
    if vy:
        bits.append(vy)
    links = []
    if d.get("doi"):
        links.append(f'doi:<a href="https://doi.org/{esc(d["doi"])}">{esc(d["doi"])}</a>')
    if d.get("arxiv_id"):
        links.append(f'<a href="https://arxiv.org/abs/{esc(d["arxiv_id"])}">arXiv:{esc(d["arxiv_id"])}</a>')
    if d.get("url") and not links:
        links.append(f'<a href="{esc(d["url"])}">원문</a>')
    if links:
        bits.append(" · ".join(links))
    return ". ".join(bits)


def tag_row(d) -> str:
    tags = []
    if d.get("venue"):
        tags.append(f'<span class="tag tag-venue">{esc(d["venue"])}</span>')
    if d.get("year"):
        tags.append(f'<span class="tag">{esc(str(d["year"]))}</span>')
    for t in (d.get("tags") or []):
        if str(t).strip():
            tags.append(f'<span class="tag">{esc(t)}</span>')
    return f'<div class="tag-row">{"".join(tags)}</div>' if tags else ""


def figures_block(d) -> str:
    figs = d.get("figures") or []
    if not figs:
        return ""
    items = []
    for i, f in enumerate(figs):
        fid = esc(f.get("id") or f"fig{i + 1}")
        src = esc(f.get("src") or "")
        label = esc(f.get("label") or f"Fig {i + 1}")
        cap = f.get("caption") or ""
        alt = esc(f.get("alt") or strip_tags(cap))
        items.append(
            f'<figure class="paper-figure anchor-fig" id="{fid}">'
            f'<div class="fig-label">{label}</div>'
            f'<img src="{src}" alt="{alt}">'
            f'<div class="paper-figure-caption">{cap}</div></figure>'
        )
    return '<div class="paper-figs">' + "".join(items) + "</div>"


def attrs_block(d) -> str:
    attrs = d.get("attrs") or []
    if not attrs:
        return ""
    cells = []
    for a in attrs:
        cells.append(
            f'<div class="attr"><div class="attr-label">{esc(a.get("label") or "")}</div>'
            f'<div class="attr-value">{a.get("value") or ""}</div></div>'
        )
    return '<div class="attrs">' + "".join(cells) + "</div>"


def sections_block(d) -> str:
    out = []
    for key, label in SECTIONS_MAIN:
        out.append(f'<div class="paper-section"><div class="paper-section-label">{label}</div>{render_prose(d.get(key))}</div>')
    out.append(f'<div class="paper-section relevance"><div class="paper-section-label">본 연구와의 관계</div>{render_prose(d.get("relation"))}</div>')
    return "\n    ".join(out)


def build_article(d) -> str:
    parts = []
    tr = tag_row(d)
    if tr:
        parts.append(tr)
    parts.append(f"<h1>{esc(d.get('title') or '(제목 없음)')}</h1>")
    cit = d.get("citation") or build_citation(d)
    if cit:
        parts.append(f'<div class="citation">{cit}</div>')
    if d.get("role"):
        parts.append(f'<div class="p-role">{esc(d["role"])}</div>')
    if d.get("tldr"):
        parts.append(f'<div class="tldr"><span class="tldr-label">한눈에</span>{d["tldr"]}</div>')
    figs = figures_block(d)
    if figs:
        parts.append(figs)
    at = attrs_block(d)
    if at:
        parts.append(at)
    parts.append(sections_block(d))
    return "\n    ".join(parts)


def slugify(d) -> str:
    base = d.get("arxiv_id") or d.get("doi") or d.get("title") or "card"
    s = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", str(base)).strip("-").lower()
    return (s or "card")[:60]


def main():
    ap = argparse.ArgumentParser(description="리뷰 카드(HTML) 생성")
    ap.add_argument("--input", help="JSON 경로 (없으면 stdin)")
    ap.add_argument("--out", help="출력 HTML 경로 (기본: research/<slug>.html)")
    args = ap.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)

    out_html = (DOC
                .replace("__TITLE__", esc(d.get("title") or "(제목 없음)"))
                .replace("__SLUG__", slugify(d))
                .replace("__ARTICLE__", build_article(d)))

    out = Path(args.out) if args.out else RESEARCH_DIR / f"{slugify(d)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_html, encoding="utf-8")

    # 간단 검수(lint): 깨진 figref / 그림 파일 존재 / 본문 인용 유무
    fig_ids = {(f.get("id") or f"fig{i + 1}") for i, f in enumerate(d.get("figures") or [])}
    warns = []
    for tag in re.findall(r'<a\b[^>]*class="figref"[^>]*>', out_html):
        ref = re.search(r'href="#?([^"]+)"', tag)
        if ref and ref.group(1).lstrip("#") not in fig_ids:
            warns.append("figref '#%s' 에 맞는 figure id 없음" % ref.group(1))
    for f in d.get("figures") or []:
        src = f.get("src") or ""
        if src and not src.startswith("http") and not (out.parent / src).exists():
            warns.append("그림 파일 없음: " + src)
    if out_html.count('class="qt"') == 0:
        warns.append("본문 인용(.qt) 없음 — 핵심 문장 1개 권장")

    print(f"리뷰 카드 생성: {out}")
    for w in warns:
        print("  · [검수] " + w)


if __name__ == "__main__":
    main()
