"""Claude를 이용한 병렬 코드 리뷰 에이전트."""

import asyncio
import json
import re

from anthropic import AsyncAnthropic

client = AsyncAnthropic()

REVIEW_PROMPTS = {
    "bug": (
        "다음 코드 diff에서 버그를 찾아주세요.\n"
        "집중할 것: NullPointerException, 경계값 오류, 잘못된 타입 캐스팅, "
        "비동기 race condition, 리소스 미해제.\n"
        "발견한 버그만 보고하고, 없으면 빈 리스트를 반환하세요."
    ),
    "security": (
        "다음 코드 diff에서 보안 취약점을 찾아주세요.\n"
        "집중할 것: SQL injection, XSS, 하드코딩된 시크릿, 인증 누락, "
        "권한 검증 부재, path traversal.\n"
        "심각도(critical/high/medium/low)와 함께 보고하세요."
    ),
    "style": (
        "다음 코드 diff에서 스타일 문제를 찾아주세요.\n"
        "집중할 것: 함수가 너무 긴 경우(50줄+), 불명확한 변수명, "
        "중복 코드, 불필요한 복잡도, 매직 넘버."
    ),
    "performance": (
        "다음 코드 diff에서 성능 문제를 찾아주세요.\n"
        "집중할 것: N+1 쿼리, 루프 내 중복 연산, 메모리 누수 가능성, "
        "불필요한 동기 블로킹, 비효율적 자료구조 사용."
    ),
}

MAX_PATCH_LENGTH = 3000


def _parse_json(text: str) -> dict:
    """Claude 응답에서 JSON을 추출한다."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"issues": []}


async def _run_single_check(
    check_type: str, filename: str, patch: str, language: str
) -> list[dict]:
    """단일 검사기를 실행한다."""
    prompt = (
        f"언어: {language}\n"
        f"파일: {filename}\n\n"
        f"{REVIEW_PROMPTS[check_type]}\n\n"
        f"diff:\n```\n{patch[:MAX_PATCH_LENGTH]}\n```\n\n"
        'JSON 형식으로 반환:\n'
        '{"issues": [{"line": <줄번호>, "severity": "high|medium|low", '
        '"message": "<설명>", "suggestion": "<수정 제안>"}]}'
    )

    resp = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    result = _parse_json(resp.content[0].text)
    issues = result.get("issues", [])

    # 검사 유형 태그 추가
    for issue in issues:
        issue["type"] = check_type
        issue["filename"] = filename

    return issues


async def review_file(filename: str, patch: str, language: str) -> list[dict]:
    """파일 하나에 대해 4개 검사기를 병렬 실행한다."""
    tasks = [
        _run_single_check(check_type, filename, patch, language)
        for check_type in REVIEW_PROMPTS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_issues = []
    for result in results:
        if isinstance(result, Exception):
            continue
        all_issues.extend(result)

    return _deduplicate(all_issues)


def _deduplicate(issues: list[dict]) -> list[dict]:
    """같은 라인에 대한 중복 이슈를 제거한다. 심각도가 높은 것을 우선한다."""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    seen: dict[tuple, dict] = {}

    for issue in issues:
        key = (issue.get("filename"), issue.get("line"))
        existing = seen.get(key)
        if existing is None:
            seen[key] = issue
        else:
            existing_sev = severity_order.get(existing.get("severity", "low"), 3)
            new_sev = severity_order.get(issue.get("severity", "low"), 3)
            if new_sev < existing_sev:
                seen[key] = issue

    return list(seen.values())


async def review_all_files(files: list[dict]) -> list[dict]:
    """모든 파일을 병렬로 리뷰한다."""
    tasks = [
        review_file(f["filename"], f["patch"], f["language"])
        for f in files
        if not f.get("deleted_file")
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_issues = []
    for result in results:
        if isinstance(result, Exception):
            continue
        all_issues.extend(result)

    # 심각도 순 정렬
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

    return all_issues
