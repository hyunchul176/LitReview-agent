"""여러 리뷰 카드를 한 페이지에 모은 '토픽 페이지' 생성 (사이드바 TOC 포함).

같은 주제의 카드들을 한 페이지에 쌓고, 왼쪽 사이드바에 카드 목차(TOC)를 단다.
주제가 완전히 다르면 토픽을 나눠 각각 페이지로 만들고, 대시보드에서 카테고리로 진입하게 한다.

입력은 이미 생성된 카드 HTML들(make_card.py 산출물). 카드의 <article class="paper" id=...> 를
그대로 추출해 재사용하므로 그림·하이라이트·인용이 유지된다 (assets/card.css·card.js 공유).

사용 예:
  python scripts/make_topic_page.py --topic "시공간 GNN 교통량 예측" \
      research/dcrnn.html research/stgcn.html research/gwnet.html
  python scripts/make_topic_page.py --topic "VLA 휴머노이드 운전" --out research/topic-vla.html \
      research/openvla.html research/humdrive.html
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from _common import ROOT

RESEARCH = ROOT / "research"


def extract(card_path: Path):
    t = card_path.read_text(encoding="utf-8")
    m = re.search(r'<article class="paper".*?</article>', t, re.S)
    art = m.group(0) if m else ""
    cid = (re.search(r'id="([^"]+)"', art) or [None, card_path.stem])[1]
    h1 = re.search(r"<h1>(.*?)</h1>", art, re.S)
    title = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else card_path.stem
    ven = re.search(r'<span class="tag tag-venue">(.*?)</span>', art, re.S)
    venue = re.sub(r"<[^>]+>", "", ven.group(1)).strip() if ven else ""
    return cid, title, venue, art


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", s).strip("-").lower()
    return (s or "topic")[:50]


def main():
    ap = argparse.ArgumentParser(description="토픽 페이지(여러 카드 + 사이드바 TOC) 생성")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--out")
    ap.add_argument("cards", nargs="+")
    args = ap.parse_args()

    items = [extract(Path(c)) for c in args.cards]
    toc_items = []
    for cid, title, venue, _ in items:
        vspan = f'<span class="tv">{html.escape(venue)}</span>' if venue else ""
        toc_items.append(f'<li><a href="#{cid}"><span class="tt">{html.escape(title)}</span>{vspan}</a></li>')
    toc = "".join(toc_items)
    blocks = "\n".join(f'<div class="cardblock">{art}</div>' for _, _, _, art in items)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(args.topic)} · 리뷰 카드</title>
<link rel="stylesheet" href="assets/card.css">
<script>(function(){{try{{var t=localStorage.getItem('theme')||((window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light');document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}}})();</script>
<style>
  .tlayout{{display:flex;align-items:flex-start;gap:1.6rem;max-width:1140px;margin:0 auto;padding:1.4rem 1.2rem 4rem;}}
  .tsidebar{{flex:none;width:236px;position:sticky;top:1rem;align-self:flex-start;}}
  .tsidebar .topic{{font-size:1.05rem;font-weight:800;color:var(--ink);line-height:1.35;margin-bottom:.2rem;}}
  .tsidebar .kick{{font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700;}}
  .toclabel{{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint);font-weight:700;margin:1rem 0 .5rem;}}
  .ttoc{{list-style:none;margin:0;padding:0;border-left:2px solid var(--line);}}
  .ttoc a{{display:block;padding:.4rem .7rem;margin-left:-2px;border-left:2px solid transparent;text-decoration:none;}}
  .ttoc .tt{{display:block;font-size:.85rem;color:var(--ink-soft);font-weight:600;line-height:1.35;}}
  .ttoc .tv{{display:block;font-size:.72rem;color:var(--ink-faint);font-style:italic;}}
  .ttoc a:hover .tt{{color:var(--accent);}}
  .ttoc a.active{{border-left-color:var(--accent);}}
  .ttoc a.active .tt{{color:var(--accent);font-weight:800;}}
  .tcontent{{flex:1;min-width:0;}}
  .tcontent > .cardblock{{margin-bottom:1.4rem;}}
  .tcontent .paper{{scroll-margin-top:1rem;}}
  .tbar{{display:flex;justify-content:flex-end;margin-bottom:.8rem;}}
  @media(max-width:820px){{.tlayout{{flex-direction:column;}}.tsidebar{{position:static;width:100%;}}.ttoc{{display:flex;flex-wrap:wrap;gap:.3rem;border-left:none;}}.ttoc a{{border:1px solid var(--line);border-radius:7px;}}.ttoc .tv{{display:none;}}}}
</style>
</head>
<body>
<div class="tlayout">
  <aside class="tsidebar">
    <div class="kick">Literature · 토픽</div>
    <div class="topic">{html.escape(args.topic)}</div>
    <div class="toclabel">리뷰 카드 {len(items)}</div>
    <ul class="ttoc">{toc}</ul>
    <button class="theme-toggle" type="button" style="margin-top:1rem;">☾ 다크 모드</button>
  </aside>
  <main class="tcontent">
    <div class="tbar"></div>
    {blocks}
  </main>
</div>
<div class="lightbox" id="lightbox"><span class="lightbox-close">×</span><img alt=""><div class="lightbox-cap"></div></div>
<script src="assets/card.js"></script>
<script>
  (function(){{
    var links=[].slice.call(document.querySelectorAll('.ttoc a'));
    var map={{}},secs=[];
    links.forEach(function(a){{var id=a.getAttribute('href').slice(1);map[id]=a;var s=document.getElementById(id);if(s)secs.push(s);}});
    if('IntersectionObserver' in window && secs.length){{
      var ob=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{links.forEach(function(l){{l.classList.remove('active');}});if(map[e.target.id])map[e.target.id].classList.add('active');}}}});}},{{rootMargin:'-15% 0px -75% 0px'}});
      secs.forEach(function(s){{ob.observe(s);}});
    }}
  }})();
</script>
</body>
</html>
"""
    out = Path(args.out) if args.out else RESEARCH / f"topic-{slugify(args.topic)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"토픽 페이지 생성: {out}  (카드 {len(items)}개, 사이드바 TOC)")


if __name__ == "__main__":
    main()
