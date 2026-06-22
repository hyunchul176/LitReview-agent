"""후보 논문 선별(curation) 체크리스트 생성.

검색으로 모은 후보를 분야별로 분류한 JSON을 받아, 사람이 취사선택할 수 있는
HTML 체크리스트(research/shortlist.html)를 만든다. 관련 없는 후보는 미리 체크 해제 +
"제외 추천" 표시. 사용자는 체크 정리 후 "선택 복사"로 확정 목록을 받아 에이전트에 붙여넣는다.

검색 → (이 단계: 분류·선별) → 확정된 것만 수집·정독.

JSON 스키마:
{
  "query": "검색어/주제", "idea": "현재 좁힌 아이디어(선택)",
  "categories": [
    {"name": "VLA 모델 (방법)",
     "papers": [
       {"title": "...", "authors": "Kim et al.", "year": 2024, "venue": "arXiv",
        "source": "arxiv", "id": "2406.09246", "url": "https://...",
        "note": "왜 관련 있는지 한 줄", "exclude": false}
     ]}
  ]
}
- id: DOI 또는 arXiv id (선택 복사 시 이 값이 줄바꿈으로 모임)
- exclude: true 면 기본 체크 해제 + "제외 추천" 표시(엉뚱한 보고서·무관 서베이 등)

사용 예:
  python scripts/make_shortlist.py --input shortlist.json
  python scripts/make_shortlist.py --input shortlist.json --out research/shortlist.html
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from _common import ROOT

RESEARCH = ROOT / "research"


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def main():
    ap = argparse.ArgumentParser(description="후보 논문 선별 체크리스트 생성")
    ap.add_argument("--input", help="JSON 경로 (없으면 stdin)")
    ap.add_argument("--out", help="출력 HTML (기본: research/shortlist.html)")
    args = ap.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    d = json.loads(raw)
    cats = d.get("categories", [])
    total = sum(len(c.get("papers", [])) for c in cats)
    rec = sum(1 for c in cats for p in c.get("papers", []) if not p.get("exclude"))

    rows = []
    for c in cats:
        items = []
        for p in c.get("papers", []):
            ex = bool(p.get("exclude"))
            pid = esc(p.get("id") or "")
            title = esc(p.get("title") or "(제목 없음)")
            if p.get("url"):
                title = f'<a href="{esc(p["url"])}" target="_blank" rel="noopener">{title}</a>'
            meta = " · ".join(esc(x) for x in [p.get("authors"), p.get("year"), p.get("venue"), p.get("source"), p.get("id")] if x)
            tag = '<span class="extag">제외 추천</span>' if ex else ""
            summary = f'<span class="rsum"><b>내용</b> {esc(p.get("summary"))}</span>' if p.get("summary") else ""
            note = f'<span class="rnote"><b>판단</b> {esc(p.get("note"))}</span>' if p.get("note") else ""
            items.append(
                f'<label class="row{" ex" if ex else ""}">'
                f'<input type="checkbox" class="cb" data-id="{pid}"{"" if ex else " checked"}>'
                f'<span class="rmain"><span class="rtitle">{title}{tag}</span>'
                f'<span class="rmeta">{meta}</span>{summary}{note}</span></label>'
            )
        rows.append(f'<section class="cat"><h2>{esc(c.get("name"))} <span class="n">{len(c.get("papers", []))}</span></h2>{"".join(items)}</section>')

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>후보 논문 선별</title>
<style>
  :root{{--paper:#f7f5f0;--paper2:#fffdf8;--ink:#1f2328;--soft:#4a5159;--faint:#79828c;--line:#e2ddd2;--acc:#8a3324;--accbg:#f3e7e3;--red:#9a2f2f;--redbg:#f4e2e0;
    --sans:"Pretendard Variable",Pretendard,"Noto Sans KR","Malgun Gothic",-apple-system,sans-serif;}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6;font-size:16px;}}
  .wrap{{max-width:860px;margin:0 auto;padding:1.8rem 1.4rem 4rem;}}
  header{{background:var(--paper2);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:12px;padding:1.1rem 1.3rem;margin-bottom:1.1rem;}}
  header .kick{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);font-weight:700;}}
  header h1{{font-size:1.45rem;margin:.25rem 0 .5rem;}}
  header .q{{font-size:.92rem;color:var(--soft);}}
  header .hint{{font-size:.86rem;color:var(--faint);margin-top:.5rem;}}
  .bar{{position:sticky;top:0;z-index:5;background:var(--paper);padding:.7rem 0;display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line);margin-bottom:.6rem;}}
  .btn{{font:600 .9rem var(--sans);padding:.5rem .9rem;border-radius:8px;border:1px solid var(--acc);background:var(--acc);color:#fff;cursor:pointer;}}
  .btn.ghost{{background:var(--paper2);color:var(--soft);border-color:var(--line);}}
  .cat{{margin:1.2rem 0;}}
  .cat h2{{font-size:1.05rem;color:var(--ink);border-bottom:2px solid var(--line);padding-bottom:.35rem;}}
  .cat h2 .n{{font-size:.78rem;color:var(--faint);font-weight:600;}}
  .row{{display:flex;gap:.7rem;align-items:flex-start;padding:.7rem .8rem;border:1px solid var(--line);border-radius:10px;margin:.45rem 0;background:var(--paper2);cursor:pointer;}}
  .row.ex{{opacity:.62;background:var(--paper);}}
  .row .cb{{margin-top:.25rem;width:18px;height:18px;flex:none;accent-color:var(--acc);}}
  .rtitle{{font-weight:700;font-size:.98rem;}}
  .rtitle a{{color:var(--ink);text-decoration:none;}}
  .rtitle a:hover{{color:var(--acc);}}
  .extag{{font-size:.68rem;font-weight:800;color:var(--red);background:var(--redbg);border:1px solid #e7c9c5;border-radius:5px;padding:.05rem .4rem;margin-left:.45rem;vertical-align:middle;}}
  .rmeta{{display:block;font-size:.8rem;color:var(--faint);margin-top:.15rem;}}
  .rsum{{display:block;font-size:.88rem;color:var(--ink);margin-top:.35rem;line-height:1.55;}}
  .rnote{{display:block;font-size:.86rem;color:var(--soft);margin-top:.3rem;font-style:italic;}}
  .rsum b,.rnote b{{display:inline-block;font-style:normal;font-size:.66rem;font-weight:800;letter-spacing:.04em;color:#fff;background:var(--acc);border-radius:4px;padding:.05rem .35rem;margin-right:.4rem;vertical-align:middle;}}
  .rnote b{{background:var(--faint);}}
  textarea#out{{width:100%;height:90px;margin-top:.7rem;border:1px solid var(--line);border-radius:8px;padding:.6rem;font:13px/1.5 ui-monospace,Consolas,monospace;display:none;}}
  .toast{{font-size:.85rem;color:var(--acc);font-weight:700;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kick">후보 선별 · Curation</div>
    <h1>이 논문들 중 정리할 것을 골라주세요</h1>
    <div class="q"><b>검색:</b> {esc(d.get("query"))}{("<br><b>아이디어:</b> " + esc(d.get("idea"))) if d.get("idea") else ""}</div>
    <div class="hint">관련 없는 건 체크를 해제하세요. <b>제외 추천</b>은 기본 해제돼 있습니다. 다 고른 뒤 <b>선택 복사</b>를 눌러 에이전트에 붙여넣으면, 그 논문만 수집·정독합니다.</div>
  </header>
  <div class="bar">
    <button class="btn" onclick="copySel()">✓ 선택한 <span id="cnt">{rec}</span>편 복사</button>
    <button class="btn ghost" onclick="all(true)">모두 선택</button>
    <button class="btn ghost" onclick="all(false)">모두 해제</button>
    <span class="toast" id="toast"></span>
  </div>
  <textarea id="out" readonly></textarea>
  {"".join(rows)}
</div>
<script>
  var cbs=function(){{return Array.prototype.slice.call(document.querySelectorAll('.cb'));}};
  function upd(){{document.getElementById('cnt').textContent=cbs().filter(function(c){{return c.checked;}}).length;}}
  function all(v){{cbs().forEach(function(c){{c.checked=v;}});upd();}}
  function copySel(){{
    var ids=cbs().filter(function(c){{return c.checked;}}).map(function(c){{return c.dataset.id;}}).filter(Boolean);
    var text=ids.join('\\n');
    var ta=document.getElementById('out');ta.style.display='block';ta.value=text;ta.focus();ta.select();
    try{{ta.setSelectionRange(0,text.length);}}catch(e){{}}
    var toast=document.getElementById('toast');
    var ok=function(){{toast.textContent=ids.length+'편 복사됨 — 에이전트에 붙여넣으세요';}};
    var manual=function(){{toast.textContent=ids.length+'편 선택됨 — 아래 칸을 Ctrl+C로 복사하세요';}};
    var did=false; try{{did=document.execCommand('copy');}}catch(e){{}}
    if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(text).then(ok,function(){{if(did){{ok();}}else{{manual();}}}});}}
    else{{if(did){{ok();}}else{{manual();}}}}
  }}
  document.addEventListener('change',function(e){{if(e.target.classList.contains('cb'))upd();}});
  upd();
</script>
</body>
</html>
"""
    out = Path(args.out) if args.out else RESEARCH / "shortlist.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"후보 선별 체크리스트 생성: {out}")
    print(f"  총 {total}편 · 추천(기본 선택) {rec}편 · 제외 추천 {total - rec}편")


if __name__ == "__main__":
    main()
