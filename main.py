"""AI PR Review Agent - GitHub Actions에서 실행되는 코드 리뷰 에이전트.

PR과 push(커밋) 이벤트 모두 지원한다.
"""

import asyncio
import json
import os
import sys

from diff_collector import get_pr_files, get_commit_files
from review_agent import review_all_files
from commenter import post_pr_review, post_commit_comment


async def handle_pull_request(owner: str, repo: str, event: dict) -> None:
    """PR 이벤트를 처리한다."""
    pr = event.get("pull_request", {})
    pr_number = str(pr.get("number", ""))
    commit_sha = pr.get("head", {}).get("sha", "")

    if not pr_number:
        print("ERROR: PR 번호를 읽을 수 없습니다.")
        sys.exit(1)

    print(f"PR: #{pr_number}")

    files = await get_pr_files(owner, repo, pr_number)
    print(f"  {len(files)}개 파일 발견")

    if not files:
        print("변경된 코드 파일이 없습니다. 리뷰를 건너뜁니다.")
        return

    print("AI 리뷰 실행 중...")
    issues = await review_all_files(files)
    print(f"  {len(issues)}건의 이슈 발견")

    print("PR에 리뷰 결과 게시 중...")
    await post_pr_review(owner, repo, pr_number, commit_sha, issues)
    print("완료!")


async def handle_push(owner: str, repo: str, event: dict) -> None:
    """push 이벤트를 처리한다. 각 커밋에 대해 리뷰를 실행한다."""
    commits = event.get("commits", [])

    if not commits:
        print("커밋이 없습니다. 리뷰를 건너뜁니다.")
        return

    for commit in commits:
        sha = commit.get("id", "")
        message = commit.get("message", "").split("\n")[0]
        print(f"\n커밋: {sha[:7]} - {message}")

        files = await get_commit_files(owner, repo, sha)
        print(f"  {len(files)}개 파일 발견")

        if not files:
            print("  변경된 코드 파일이 없습니다. 건너뜁니다.")
            continue

        print("  AI 리뷰 실행 중...")
        issues = await review_all_files(files)
        print(f"  {len(issues)}건의 이슈 발견")

        if issues:
            print("  커밋에 리뷰 결과 게시 중...")
            await post_commit_comment(owner, repo, sha, issues)

    print("\n완료!")


async def main() -> None:
    github_event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    event_name = os.environ.get("REVIEW_EVENT", "")

    if not github_event_path:
        print("ERROR: GITHUB_EVENT_PATH가 설정되지 않았습니다.")
        print("이 스크립트는 GitHub Actions에서 실행해야 합니다.")
        sys.exit(1)

    if not os.environ.get("GITHUB_TOKEN"):
        print("ERROR: GITHUB_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    with open(github_event_path) as f:
        event = json.load(f)

    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo_full:
        print("ERROR: GITHUB_REPOSITORY가 설정되지 않았습니다.")
        sys.exit(1)

    owner, repo = repo_full.split("/", 1)
    print(f"레포: {owner}/{repo} ({event_name})")

    if event_name == "pull_request":
        await handle_pull_request(owner, repo, event)
    elif event_name == "push":
        await handle_push(owner, repo, event)
    else:
        print(f"지원하지 않는 이벤트: {event_name}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
