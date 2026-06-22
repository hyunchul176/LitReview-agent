"""현황 대시보드 생성: research/index.html.

상태 파일들을 읽어 한 장짜리 현황 페이지를 만든다 (에이전트가 작업 후 다시 실행해 갱신).
  - workspace/idea.md       → 지금 좁히는 아이디어
  - library.json            → 모은 논문
  - research/topic-*.html    → 토픽(카테고리) 페이지 — 카테고리 타일로 보여주고 클릭 시 진입
  - workspace/blockers.md    → 미해결 막힘

리뷰 카드는 토픽 페이지(make_topic_page.py) 안에 모여 있으므로, 대시보드는 개별 카드가 아니라
'토픽'을 카테고리 타일로 나열한다 (주제가 다르면 카테고리로 갈라 클릭 진입).

사용: python scripts/build_dashboard.py   (열기: research/index.html)
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

from _common import ROOT

RESEARCH = ROOT / "research"
WS = ROOT / "workspace"
LIBRARY = ROOT / "library.json"


def read(p: Path, default=""):
    return p.read_text(encoding="utf-8") if p.exists() else default


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", str(s or ""))


def parse_idea():
    t = read(WS / "idea.md")
    m = re.search(r"##\s*지금.*?\n(.*?)(?:\n##|\Z)", t, re.S)
    lines = []
    for l in (m.group(1).strip() if m else "").splitlines():
        l = l.strip()
        if not l or l.startswith("<!--"):
            continue
        lines.append(html.escape(re.sub(r"^[-*]\s*", "", l).replace("**", "")))
    return lines


def parse_blockers():
    t = read(WS / "blockers.md")
    res = []
    for b in re.findall(r"###\s*(.+?)(?=\n###|\Z)", t, re.S):
        first = b.strip().splitlines()[0].strip()
        if first:
            res.append(html.escape(first))
    return res


def topic_meta(p: Path):
    t = read(p)
    nm = re.search(r'<div class="topic">(.*?)</div>', t, re.S)
    name = strip_tags(nm.group(1)).strip() if nm else p.stem
    titles = [strip_tags(x).strip() for x in re.findall(r'<span class="tt">(.*?)</span>', t, re.S)]
    if not titles:  # 토픽 페이지가 아니어도 카드 article 수로 추정
        titles = [strip_tags(x).strip() for x in re.findall(r"<h1>(.*?)</h1>", t, re.S)]
    img = re.search(r'src="(images/[^"]+)"', t)
    return name, titles, (img.group(1) if img else None)


def paper_link(p):
    if p.get("arxiv_id"):
        return f"https://arxiv.org/abs/{p['arxiv_id']}"
    if p.get("doi"):
        return f"https://doi.org/{p['doi']}"
    return p.get("oa_pdf") or "#"


def main():
    lib = json.loads(read(LIBRARY, '{"papers":[]}'))
    papers = lib.get("papers", [])
    topics = sorted(RESEARCH.glob("topic-*.html"))
    metas = [(p, *topic_meta(p)) for p in topics]
    total_cards = sum(len(t[2]) for t in metas)
    idea = parse_idea()
    blockers = parse_blockers()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    idea_html = ("".join(f"<div>{l}</div>" for l in idea)
                 if idea else '<div class="muted">아직 좁힌 아이디어가 없습니다. 큰 주제를 던져 시작하세요.</div>')

    if metas:
        tiles = []
        for p, name, titles, img in metas:
            thumb = (f'<img src="{img}" alt="">' if img else '<div class="noimg">그림 없음</div>')
            lis = "".join(f"<li>{html.escape(x)}</li>" for x in titles[:5])
            more = f'<li class="more">+ {len(titles) - 5}편</li>' if len(titles) > 5 else ""
            tiles.append(
                f'<a class="dcard" href="{p.name}">{thumb}<div class="cbody">'
                f'<div class="t">{html.escape(name)}</div>'
                f'<div class="sub">리뷰 카드 {len(titles)}편</div>'
                f'<ul class="mini">{lis}{more}</ul></div></a>'
            )
        topics_html = '<div class="cardgrid">' + "".join(tiles) + "</div>"
    else:
        topics_html = '<div class="muted">아직 만든 토픽 페이지가 없습니다. (정독 후 make_topic_page.py 로 주제별로 묶으세요)</div>'

    if papers:
        rows = []
        for p in papers:
            t = html.escape(p.get("title") or "(제목 없음)")
            meta = " · ".join(str(x) for x in [p.get("year"), p.get("venue"), p.get("source")] if x)
            rows.append(f'<li><a href="{paper_link(p)}" target="_blank" rel="noopener">{t}</a>'
                        f'<span class="pmeta">{html.escape(meta)}</span></li>')
        papers_html = '<ul class="plist">' + "".join(rows) + "</ul>"
    else:
        papers_html = '<div class="muted">아직 모은 논문이 없습니다.</div>'

    blk_html = ('<ul class="blk">' + "".join(f"<li>🚧 {b}</li>" for b in blockers) + "</ul>"
                if blockers else '<div class="muted">막힌 일 없음 ✓</div>')

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>리서치 에이전트 · 현황</title>
<link rel="stylesheet" href="assets/card.css">
<script>(function(){{try{{var t=localStorage.getItem('theme')||((window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light');document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}}})();</script>
<style>
  .dash{{max-width:1000px;margin:0 auto;padding:1.8rem 1.4rem 4rem;}}
  .dtop{{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;}}
  .dtop h1{{font-size:1.7rem;margin:.1rem 0;}}
  .dtop .sub{{color:var(--ink-faint);font-size:.85rem;}}
  .stats{{display:flex;gap:.8rem;flex-wrap:wrap;margin:1.3rem 0 1.8rem;}}
  .stat{{flex:1;min-width:120px;background:var(--paper-2);border:1px solid var(--line);border-radius:12px;padding:.9rem 1.1rem;}}
  .stat .n{{font-size:1.9rem;font-weight:800;color:var(--accent);line-height:1;}}
  .stat .l{{font-size:.8rem;color:var(--ink-faint);font-weight:700;margin-top:.3rem;}}
  .dsec{{margin:1.8rem 0;}}
  .dsec h2{{font-size:1.15rem;color:var(--ink);border-bottom:2px solid var(--line);padding-bottom:.4rem;margin-bottom:.9rem;}}
  .idea{{background:var(--paper-2);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:1rem 1.2rem;line-height:1.8;}}
  .cardgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.9rem;}}
  .dcard{{background:var(--paper-2);border:1px solid var(--line);border-radius:10px;overflow:hidden;text-decoration:none;color:inherit;display:flex;flex-direction:column;transition:border-color .15s,box-shadow .15s,transform .15s;}}
  .dcard:hover{{border-color:var(--accent);box-shadow:0 4px 16px var(--shadow);transform:translateY(-2px);}}
  .dcard img{{width:100%;height:120px;object-fit:contain;background:#fff;border-bottom:1px solid var(--line);padding:5px;}}
  .dcard .noimg{{height:120px;display:grid;place-items:center;color:var(--ink-faint);font-size:.8rem;background:var(--paper);border-bottom:1px solid var(--line);}}
  .dcard .cbody{{padding:.7rem .9rem;}}
  .dcard .t{{font-size:1rem;font-weight:800;line-height:1.35;}}
  .dcard .sub{{font-size:.78rem;color:var(--accent);font-weight:700;margin:.15rem 0 .4rem;}}
  .dcard .mini{{list-style:none;margin:0;padding:0;}}
  .dcard .mini li{{font-size:.8rem;color:var(--ink-soft);line-height:1.45;padding-left:.7rem;position:relative;}}
  .dcard .mini li::before{{content:"·";position:absolute;left:0;color:var(--ink-faint);}}
  .dcard .mini li.more{{color:var(--ink-faint);font-style:italic;}}
  .plist{{list-style:none;margin:0;padding:0;}}
  .plist li{{padding:.55rem 0;border-bottom:1px solid var(--line);}}
  .plist li:last-child{{border-bottom:none;}}
  .plist a{{color:var(--accent);text-decoration:none;font-weight:600;}}
  .plist .pmeta{{display:block;color:var(--ink-faint);font-size:.8rem;margin-top:.15rem;}}
  .blk{{list-style:none;margin:0;padding:0;}}
  .blk li{{background:var(--paper-2);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:.55rem .8rem;margin-bottom:.5rem;font-size:.9rem;}}
  .muted{{color:var(--ink-faint);font-style:italic;}}
</style>
</head>
<body>
<div class="dash">
  <div class="dtop">
    <div>
      <div class="kicker" style="color:var(--accent);font-weight:700;font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;">Research Agent · Status</div>
      <h1>리서치 에이전트 현황</h1>
      <div class="sub">갱신: {now}</div>
    </div>
    <button class="theme-toggle" type="button">☾ 다크 모드</button>
  </div>

  <div class="stats">
    <div class="stat"><div class="n">{len(metas)}</div><div class="l">토픽</div></div>
    <div class="stat"><div class="n">{total_cards}</div><div class="l">리뷰 카드</div></div>
    <div class="stat"><div class="n">{len(papers)}</div><div class="l">모은 논문</div></div>
    <div class="stat"><div class="n">{len(blockers)}</div><div class="l">미해결 막힘</div></div>
  </div>

  <div class="dsec"><h2>지금 좁히는 아이디어</h2><div class="idea">{idea_html}</div></div>
  <div class="dsec"><h2>토픽 ({len(metas)}) — 클릭하면 그 주제의 리뷰 카드</h2>{topics_html}</div>
  <div class="dsec"><h2>모은 논문 ({len(papers)})</h2>{papers_html}</div>
  <div class="dsec"><h2>막힘 (Blockers)</h2>{blk_html}</div>
</div>
<script src="assets/card.js"></script>
</body>
</html>
"""
    out = RESEARCH / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"대시보드 생성: {out}")
    print(f"  토픽 {len(metas)} · 리뷰 카드 {total_cards} · 논문 {len(papers)} · 막힘 {len(blockers)}")


if __name__ == "__main__":
    main()
