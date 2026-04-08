"""AI PR Review Agent - GitHub Actions에서 실행되는 코드 리뷰 에이전트."""

import asyncio
import json
import os
import sys

from diff_collector import get_pr_files
from review_agent import review_all_files
from commenter import post_review


async def main() -> None:
    # GitHub Actions 환경변수에서 정보 읽기
    github_event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    if not github_event_path:
        print("ERROR: GITHUB_EVENT_PATH가 설정되지 않았습니다.")
        print("이 스크립트는 GitHub Actions에서 실행해야 합니다.")
        sys.exit(1)

    if not github_token:
        print("ERROR: GITHUB_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    # 이벤트 페이로드에서 PR 정보 추출
    with open(github_event_path) as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    pr_number = str(pr.get("number", ""))
    commit_sha = pr.get("head", {}).get("sha", "")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")  # owner/repo

    if not pr_number or not repo_full:
        print("ERROR: PR 정보를 읽을 수 없습니다.")
        sys.exit(1)

    owner, repo = repo_full.split("/", 1)
    print(f"레포: {owner}/{repo}, PR: #{pr_number}")

    # 1) Diff 수집
    print("변경 파일 수집 중...")
    files = await get_pr_files(owner, repo, pr_number)
    print(f"  {len(files)}개 파일 발견")

    if not files:
        print("변경된 코드 파일이 없습니다. 리뷰를 건너뜁니다.")
        return

    # 2) 리뷰 실행
    print("AI 리뷰 실행 중...")
    issues = await review_all_files(files)
    print(f"  {len(issues)}건의 이슈 발견")

    # 3) PR에 코멘트 작성
    print("PR에 리뷰 결과 게시 중...")
    await post_review(owner, repo, pr_number, commit_sha, issues)
    print("완료!")


if __name__ == "__main__":
    asyncio.run(main())
