"""IEEE 등 키 없는 출판사: 브라우저 자동화 다운로드.

API 키를 안 주는 곳(IEEE 등)은 브라우저로 접근해 PDF를 받는다.

접근 방식 두 가지:
- 캠퍼스망 또는 KAIST VPN: KAIST IP로 인증되므로 로그인 없이 바로 풀텍스트가 열린다 (권장, 가장 간단).
- 그 외 외부망: 한 번 'login' 으로 로그인 세션을 만들어 .browser/ 에 저장해 재사용한다.

로그인 세션 만들기 (외부망에서만 필요):
  python scripts/fetch_ieee_playwright.py login
     → 창이 열리면 KAIST/IEEE 로그인. 끝나면 터미널에서 Enter.

받기 (DOI 또는 IEEE 문서 URL):
  python scripts/fetch_ieee_playwright.py fetch 10.1109/JSEN.2022.3156971
  python scripts/fetch_ieee_playwright.py fetch https://ieeexplore.ieee.org/document/9712345

주의:
- 로그인 세션은 사람마다 다르며 공유되지 않는다 (.browser/ 는 .gitignore).
- 기관 이용 약관을 지켜 짧은 시간에 과도하게 받지 않는다.
"""
from __future__ import annotations

import argparse
import re
import sys
import time

from _common import PAPERS_DIR, ROOT, norm_doi

USER_DATA = ROOT / ".browser"   # 로그인 세션 저장 (절대 커밋 금지)

try:
    from playwright.sync_api import sync_playwright
    HAVE_PW = True
except Exception:
    HAVE_PW = False


def _need_pw():
    if not HAVE_PW:
        print("[!] Playwright 미설치. 설치 후 다시 실행하세요:", file=sys.stderr)
        print("    pip install playwright && python -m playwright install chromium", file=sys.stderr)
        sys.exit(3)


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _ctx(p, headless):
    """IEEE 등의 봇 차단(HTTP 418)을 피하려 실제 브라우저처럼 보이게 설정 (인가된 본인 접근용)."""
    ctx = p.chromium.launch_persistent_context(
        str(USER_DATA), headless=headless, accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled"],
        user_agent=UA, viewport={"width": 1366, "height": 900}, locale="en-US")
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    return ctx


def do_login():
    _need_pw()
    USER_DATA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = _ctx(p, False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://ieeexplore.ieee.org/", wait_until="domcontentloaded")
        print("브라우저에서 KAIST/IEEE 로그인을 마친 뒤, 이 창에서 Enter 를 누르세요...")
        try:
            input()
        except EOFError:
            time.sleep(60)
        ctx.close()
    print(f"로그인 세션을 저장했습니다: {USER_DATA}")


def _article_url(target):
    t = target.strip()
    return t if t.startswith("http") else f"https://doi.org/{norm_doi(t)}"


def do_fetch(target, headless=False):
    _need_pw()
    USER_DATA.mkdir(exist_ok=True)   # 캠퍼스/VPN이면 빈 세션이어도 KAIST IP로 인증됨
    PAPERS_DIR.mkdir(exist_ok=True)
    name = ("ieee_paper" if target.strip().startswith("http") else norm_doi(target).replace("/", "_"))
    out = PAPERS_DIR / f"{name}.pdf"
    saved = {}

    with sync_playwright() as p:
        ctx = _ctx(p, headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # application/pdf 응답을 가로채 저장 (DOM 구조 변화에 강함)
        def on_response(resp):
            if saved:
                return
            try:
                if "application/pdf" in resp.headers.get("content-type", ""):
                    body = resp.body()
                    if body[:4] == b"%PDF":
                        out.write_bytes(body)
                        saved["size"] = len(body)
            except Exception:
                pass

        ctx.on("response", on_response)
        try:
            page.goto(_article_url(target), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            m = re.search(r"/document/(\d+)", page.url)
            if m:
                arn = m.group(1)
                stamp = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arn}"
                page.goto(stamp, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                if not saved:
                    # stamp 뷰어가 embed 한 PDF(getPDF.jsp) 주소를 찾아, 인증된 컨텍스트로 직접 받는다
                    pdf_url = ""
                    fr = page.query_selector("iframe, embed")
                    if fr:
                        src = fr.get_attribute("src") or ""
                        pdf_url = src if src.startswith("http") else (("https://ieeexplore.ieee.org" + src) if src else "")
                    if not pdf_url:
                        pdf_url = f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arn}&ref="
                    try:
                        r = ctx.request.get(pdf_url, headers={"Referer": stamp})
                        body = r.body()
                        if r.ok and body[:4] == b"%PDF":
                            out.write_bytes(body)
                            saved["size"] = len(body)
                    except Exception as ex:
                        print(f"  · 직접 다운로드 실패: {ex}", file=sys.stderr)
            page.wait_for_timeout(1500)
        except Exception as ex:
            print(f"  · 탐색 중 오류: {ex}", file=sys.stderr)
        finally:
            ctx.close()

    if saved:
        print(f"  · 다운로드 성공: {out}  ({saved['size'] // 1024} KB)")
    else:
        print("  · PDF를 못 받았습니다.")
        print("    캠퍼스망/KAIST VPN이면 보통 로그인 없이 받아집니다. 외부망이면 VPN을 켜거나 'login' 으로 세션을 만드세요.")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="IEEE 브라우저 기반 다운로드")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="로그인 세션 1회 생성")
    f = sub.add_parser("fetch", help="DOI/URL로 PDF 받기")
    f.add_argument("target", help="DOI 또는 IEEE 문서 URL")
    f.add_argument("--headless", action="store_true", help="창 없이 실행 (IEEE 등은 차단될 수 있음)")
    args = ap.parse_args()

    if args.cmd == "login":
        do_login()
    else:
        do_fetch(args.target, headless=args.headless)


if __name__ == "__main__":
    main()
