"""IEEE 등 키 없는 곳 — 브라우저 자동화 다운로드 (골격).

API 키를 안 주는 출판사(IEEE 등)는 사용자의 로그인된 브라우저 세션으로 PDF를 받는다.
Playwright로 사용자 KAIST 로그인을 한 번 거친 뒤(세션 재사용), 본문 PDF를 papers/ 에 저장.

주의:
- 로그인 세션은 사람마다 다르며 공유되지 않는다. 각자 한 번 로그인한다.
- 기관 이용 약관을 지켜 과도한 자동 수집을 하지 않는다.

TODO:
- playwright 영구 컨텍스트(로그인 세션 저장)
- DOI/논문 페이지 → PDF 링크 → 저장
- library.json 갱신
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="IEEE 등 브라우저 기반 다운로드 (골격)")
    parser.add_argument("url_or_doi", help="논문 페이지 URL 또는 DOI")
    args = parser.parse_args()

    # TODO: 구현 (playwright)
    print(f"[fetch_ieee_playwright] (미구현) target={args.url_or_doi!r}")


if __name__ == "__main__":
    main()
