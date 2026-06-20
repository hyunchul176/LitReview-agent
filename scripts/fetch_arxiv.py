"""arXiv 검색·다운로드 (골격).

주어진 검색어나 arXiv ID로 논문을 찾아 메타데이터를 반환하고,
필요하면 풀텍스트 PDF를 papers/ 에 저장한다. arXiv는 API 키가 필요 없다.

참고: http://export.arxiv.org/api/query  ·  PDF: https://arxiv.org/pdf/<id>

TODO:
- arXiv API로 검색 (Atom feed 파싱)
- PDF 다운로드 → papers/<id>.pdf
- library.json 갱신 (DOI/arXiv id 기준 중복 제거)
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="arXiv 검색·다운로드 (골격)")
    parser.add_argument("query", help="검색어 또는 arXiv ID")
    parser.add_argument("--download", action="store_true", help="PDF까지 받기")
    args = parser.parse_args()

    # TODO: 구현
    print(f"[fetch_arxiv] (미구현) query={args.query!r} download={args.download}")


if __name__ == "__main__":
    main()
