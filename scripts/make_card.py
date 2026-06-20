"""정독 카드(HTML) 생성 헬퍼 (골격).

정독가(reader)가 추출한 6파트 내용(JSON)을 일관된 HTML 카드로 감싸 research/ 에 쓴다.
6파트: 연구배경 / 무엇을했나 / 방법론상세 / 결과 / 한계 / 본연구와의관계

TODO:
- 입력 JSON(또는 stdin) → HTML 템플릿 채우기
- research/<slug>.html 로 저장
- (선택) PDF에서 주요 figure 추출해 카드에 삽입
"""
import argparse


HTML_TEMPLATE = """<!-- 정독 카드 템플릿 (골격). 화이트/네이비/레드 스타일은 추후 통일. -->
<article class="paper-card">
  <h2>{title}</h2>
  <section><h3>연구 배경</h3>{background}</section>
  <section><h3>무엇을 했나</h3>{contribution}</section>
  <section><h3>방법론 상세</h3>{method}</section>
  <section><h3>결과</h3>{results}</section>
  <section><h3>한계</h3>{limitations}</section>
  <section><h3>본 연구와의 관계</h3>{relation}</section>
</article>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="정독 카드 HTML 생성 (골격)")
    parser.add_argument("--input", help="6파트 내용이 담긴 JSON 경로")
    parser.add_argument("--out", help="출력 HTML 경로 (research/...)")
    args = parser.parse_args()

    # TODO: 구현
    print(f"[make_card] (미구현) input={args.input!r} out={args.out!r}")


if __name__ == "__main__":
    main()
