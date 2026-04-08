"""AI PR Review Agent - GitLab CI 파이프라인에서 실행되는 코드 리뷰 에이전트."""

import asyncio
import os
import sys
import urllib.parse

from diff_collector import get_mr_changes
from review_agent import review_all_files
from commenter import post_review


async def main() -> None:
    # GitLab CI 환경변수에서 프로젝트/MR 정보 읽기
    project_id = os.environ.get("CI_PROJECT_ID", "")
    mr_iid = os.environ.get("CI_MERGE_REQUEST_IID", "")
    commit_sha = os.environ.get("CI_COMMIT_SHA", "")

    if not project_id or not mr_iid:
        print("ERROR: CI_PROJECT_ID 또는 CI_MERGE_REQUEST_IID가 설정되지 않았습니다.")
        print("이 스크립트는 GitLab CI merge request 파이프라인에서 실행해야 합니다.")
        sys.exit(1)

    if not os.environ.get("GITLAB_TOKEN"):
        print("ERROR: GITLAB_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    # URL-encoded project ID 처리 (CI_PROJECT_ID는 숫자지만 안전하게)
    project_id = urllib.parse.quote(str(project_id), safe="")

    print(f"프로젝트: {project_id}, MR: !{mr_iid}")

    # 1) Diff 수집
    print("변경 파일 수집 중...")
    files = await get_mr_changes(project_id, mr_iid)
    print(f"  {len(files)}개 파일 발견")

    if not files:
        print("변경된 코드 파일이 없습니다. 리뷰를 건너뜁니다.")
        return

    # 2) 리뷰 실행
    print("AI 리뷰 실행 중...")
    issues = await review_all_files(files)
    print(f"  {len(issues)}건의 이슈 발견")

    # 3) MR에 코멘트 작성
    print("MR에 리뷰 결과 게시 중...")
    await post_review(project_id, mr_iid, issues, commit_sha)
    print("완료!")


if __name__ == "__main__":
    asyncio.run(main())
