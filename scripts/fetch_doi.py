"""DOI 기반 본문 다운로드 — Elsevier / Wiley (골격).

DOI를 받아 출판사를 판별하고, KAIST 제공 API 키로 풀텍스트 PDF를 papers/ 에 받는다.
키는 .env 에서만 읽는다. 코드/로그에 키를 출력하지 않는다.

- Elsevier:  https://api.elsevier.com/content/article/doi/<DOI>  (헤더 X-ELS-APIKey)
- Wiley TDM: https://api.wiley.com/onlinelibrary/tdm/v1/articles/<DOI>  (헤더 Wiley-TDM-Client-Token)

TODO:
- DOI → 출판사 판별 (prefix 또는 crossref)
- 출판사별 엔드포인트 호출 → PDF 저장
- library.json 갱신
- 실패 시 사유를 명확히 반환 (사서가 blocker로 올릴 수 있게)
"""
import argparse
import os

from dotenv import load_dotenv

load_dotenv()
ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY", "")
WILEY_TDM_TOKEN = os.getenv("WILEY_TDM_TOKEN", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="DOI 본문 다운로드: Elsevier/Wiley (골격)")
    parser.add_argument("doi", help="다운로드할 논문 DOI")
    args = parser.parse_args()

    # TODO: 구현
    print(f"[fetch_doi] (미구현) doi={args.doi!r} "
          f"elsevier_key={'set' if ELSEVIER_API_KEY else 'MISSING'} "
          f"wiley_token={'set' if WILEY_TDM_TOKEN else 'MISSING'}")


if __name__ == "__main__":
    main()
