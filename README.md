# 연구 아이디어 탐색 & 문헌조사 에이전트

큰 아이디어를 던지면 대화로 좁혀주고, 여러 논문 DB를 한꺼번에 뒤져 풀텍스트 PDF까지 모아, 핵심을 정리한 **리뷰 카드(HTML)**로 돌려주는 Claude Code 작업공간입니다. 받아서 본인 키만 넣으면 바로 씁니다.

> 📄 시각적 팀 가이드: 클론 후 `docs/team-guide.html` 를 브라우저로 여세요 (한/영 토글, 전체 흐름도, 리뷰 카드 예시).

## 이게 뭔가요
새 앱이 아니라 **Claude Code 위에서 도는 연구 에이전트**입니다. 네 부품으로 이뤄져 있어요:

| 부품 | 정체 | 하는 일 |
|---|---|---|
| 🧠 뇌 | `CLAUDE.md` | 행동 규칙. 켤 때마다 자동으로 읽힘 |
| 🔧 전문 기사 | `.claude/agents/` | 사서·정독가·종합가 (무거운 일 전담) |
| ⚙️ 엔진 | `scripts/` | 검색·다운로드 등 실제 작업 |
| 📦 기억 | `workspace/`, `library.json` | 아이디어·논문 목록·노트 누적 |

## 폴더 구조
```
research-agent/
├── CLAUDE.md              # 뇌 — 행동 규칙
├── .claude/agents/        # 사서·정독가·종합가
├── scripts/               # 검색·다운로드 스크립트
├── workspace/             # 아이디어·노트·막힘 기록
│   ├── idea.md
│   ├── notes/
│   └── blockers.md
├── papers/                # 받은 PDF (git 제외)
├── research/              # 리뷰 카드(HTML) 출력
├── library.json           # 수집 논문 목록
└── .env                   # 본인 키 (git 제외)
```

## 설치
```bash
# 1~3. 받고 준비물 설치
git clone <repo-url> && cd research-agent
pip install -r requirements.txt
python -m playwright install chromium

# 4. 본인 키 입력 (값은 각자, 절대 커밋 금지)
cp .env.example .env        # 그다음 .env 열어서 키 채우기

# 5. 실행
claude
```

## 키 입력 (`.env`)
`.env.example`을 복사해 본인 키를 채웁니다. 값은 공유되지 않으며 각자 자기 것을 넣습니다.
- `ELSEVIER_API_KEY` — KAIST 제공 (Elsevier·ScienceDirect 본문)
- `WILEY_TDM_TOKEN` — KAIST 제공 (Wiley 본문)
- `SPRINGER_API_KEY` — 선택
- `OPENALEX_EMAIL` — 키가 아님. 본인 이메일 (응답 속도용)

> IEEE처럼 키를 안 주는 곳은 본인 KAIST 로그인이 필요합니다 (브라우저). 사람마다 달라 공유되지 않습니다.

## 쓰는 법
1. **아이디어 던지기** — "요즘 X에 관심이 생겼어. 큰 틀에서 보자." → 대화로 주제를 좁힙니다.
2. **문헌조사** — 좁혀지면 arXiv·OpenAlex로 찾고, LeapSpace용 영어 질문 초안을 받습니다.
3. **LeapSpace** — 받은 질문을 LeapSpace에 넣고, 답변(DOI 포함)을 복사해 붙여넣으면 본문을 자동 수집합니다.
4. **리뷰 카드** — 모은 논문을 정독해 `research/`에 HTML 카드로 정리합니다.

## 주의
- **키는 절대 커밋하지 않습니다.** `.env`는 `.gitignore`에 있습니다.
- 같은 논문이 여러 경로로 들어와도 DOI 기준으로 자동 정리됩니다.
- 기관 라이선스 약관을 지켜, 짧은 시간에 과도하게 받지 않습니다.

## 상태
검색·수집·리뷰 카드·figure 추출·현황 대시보드까지 구현되어 있습니다.
- `scripts/`: `fetch_openalex` · `fetch_arxiv` · `fetch_doi` · `fetch_ieee_playwright` · `extract_figures` · `make_card` · `build_dashboard`
- arXiv·OpenAlex는 무료·키 불필요. IEEE·Elsevier·Wiley 실제 다운로드는 KAIST 망 또는 기관 인증이 필요합니다.
