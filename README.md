# AI PR Review Agent

GitHub PR이 열리면 자동으로 코드 리뷰를 수행하는 AI 에이전트입니다.

## 아키텍처

```text
PR opened/synchronized
    ↓
GitHub Actions (self-hosted runner)
    ↓
Diff 수집 (GitHub API)
    ↓
4개 검사기 병렬 실행 (Claude API)
├── 버그 탐지기    - NPE, 경계값, 타입 오류
├── 보안 검사기    - SQL injection, XSS, 하드코딩 시크릿
├── 스타일 검사기  - 네이밍, 복잡도, 중복 코드
└── 성능 분석기    - N+1 쿼리, 무한루프, 메모리 누수
    ↓
결과 집계 (중복 제거 + 심각도 정렬)
    ↓
PR 코멘트 작성 (인라인 + 요약)
```

## 기술 스택

- **Runtime**: Python 3.12
- **AI**: Claude API (claude-sonnet-4-6)
- **CI/CD**: GitHub Actions + Self-hosted Runner
- **패키지 관리**: uv

## 프로젝트 구조

```text
ai-pr-agent/
├── main.py              # 엔트리포인트
├── diff_collector.py    # GitHub API로 PR diff 수집
├── review_agent.py      # Claude 4개 검사기 병렬 실행
├── commenter.py         # PR에 인라인 코멘트 + 요약 게시
├── .github/workflows/
│   └── ai-review.yml    # GitHub Actions workflow
├── pyproject.toml
└── uv.lock
```

## 설정 방법

### 1. Self-hosted Runner 등록

리눅스 서버에 GitHub Actions Runner를 설치하고 레포에 등록합니다.

### 2. Secret 등록

GitHub 레포 → Settings → Secrets and variables → Actions:

| Name                | 설명          |
|---------------------|---------------|
| `ANTHROPIC_API_KEY` | Claude API 키 |

> `GITHUB_TOKEN`은 Actions가 자동 제공하므로 별도 등록 불필요

### 3. 사용

PR을 열거나 새 커밋을 푸시하면 자동으로 AI 리뷰가 실행됩니다.

## 리뷰 결과 예시

PR에 다음과 같은 코멘트가 자동으로 달립니다:

- 인라인 코멘트: 문제가 있는 라인에 직접 코멘트
- 요약 노트: 전체 이슈 수와 심각도별 분류
