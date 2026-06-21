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
            page.wait_for_timeout(4000)
            # IEEE: 문서번호(arnumber)로 stamp 뷰어를 직접 열면 PDF가 로드된다
            m = re.search(r"/document/(\d+)", page.url)
            if m and not saved:
                stamp = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"
                page.goto(stamp, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
                fr = page.query_selector("iframe")
                if fr and not saved:
                    src = fr.get_attribute("src") or ""
                    if ".pdf" in src.lower():
                        page.goto(src if src.startswith("http") else "https://ieeexplore.ieee.org" + src,
                                  wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(4000)
            # 폴백: 기존 PDF 버튼 셀렉터
            if not saved:
                link = page.query_selector("a[href*='stamp.jsp'], a[aria-label*='PDF'], a.pdf-btn-link")
                if link:
                    href = link.get_attribute("href") or ""
                    if href:
                        page.goto(href if href.startswith("http") else f"https://ieeexplore.ieee.org{href}",
                                  wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(4000)
            page.wait_for_timeout(2000)
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
