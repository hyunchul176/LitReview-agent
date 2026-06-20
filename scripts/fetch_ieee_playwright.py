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


def do_login():
    _need_pw()
    USER_DATA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(USER_DATA), headless=False, accept_downloads=True)
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


def do_fetch(target):
    _need_pw()
    USER_DATA.mkdir(exist_ok=True)   # 캠퍼스/VPN이면 빈 세션이어도 KAIST IP로 인증됨
    PAPERS_DIR.mkdir(exist_ok=True)
    name = ("ieee_paper" if target.strip().startswith("http") else norm_doi(target).replace("/", "_"))
    out = PAPERS_DIR / f"{name}.pdf"
    saved = {}

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(USER_DATA), headless=True, accept_downloads=True)
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
            # IEEE: PDF 버튼(stamp.jsp)으로 이동 시도
            link = page.query_selector("a[href*='stamp.jsp'], a[aria-label*='PDF'], a.pdf-btn-link")
            if link and not saved:
                href = link.get_attribute("href") or ""
                if href:
                    full = href if href.startswith("http") else f"https://ieeexplore.ieee.org{href}"
                    page.goto(full, wait_until="domcontentloaded", timeout=60000)
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
    args = ap.parse_args()

    if args.cmd == "login":
        do_login()
    else:
        do_fetch(args.target)


if __name__ == "__main__":
    main()
