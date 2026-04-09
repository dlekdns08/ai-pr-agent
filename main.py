"""AI PR Review Agent — GitHub App Webhook 서버.

모든 레포의 PR/push 이벤트를 수신하여 AI 코드 리뷰를 수행한다.
"""

import hashlib
import hmac
import logging
import os

from fastapi import FastAPI, Request, HTTPException

from diff_collector import get_pr_files, get_commit_files
from review_agent import review_all_files
from commenter import post_pr_review, post_commit_comment
from github_app import get_installation_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI PR Review Agent")

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def _verify_signature(body: bytes, signature: str) -> bool:
    """GitHub webhook 서명을 검증한다."""
    if not WEBHOOK_SECRET:
        return True  # 개발 환경용
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.body()

    # 서명 검증
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    # Installation token 발급
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        return {"status": "skipped", "reason": "no installation id"}

    token = await get_installation_token(installation_id)

    if event == "pull_request":
        await _handle_pr(payload, token)
    elif event == "push":
        await _handle_push(payload, token)
    else:
        return {"status": "skipped", "reason": f"unhandled event: {event}"}

    return {"status": "ok"}


async def _handle_pr(payload: dict, token: str) -> None:
    """PR 이벤트를 처리한다."""
    action = payload.get("action", "")
    if action not in ("opened", "synchronize"):
        return

    pr = payload["pull_request"]
    repo = payload["repository"]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    pr_number = pr["number"]
    commit_sha = pr["head"]["sha"]

    logger.info(f"PR 리뷰: {owner}/{repo_name}#{pr_number}")

    files = await get_pr_files(owner, repo_name, pr_number, token)
    logger.info(f"  {len(files)}개 파일 발견")

    if not files:
        return

    issues = await review_all_files(files)
    logger.info(f"  {len(issues)}건의 이슈 발견")

    await post_pr_review(owner, repo_name, pr_number, commit_sha, issues, token)
    logger.info("  PR 리뷰 게시 완료")


async def _handle_push(payload: dict, token: str) -> None:
    """push 이벤트를 처리한다."""
    repo = payload["repository"]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    commits = payload.get("commits", [])

    for commit in commits:
        sha = commit["id"]
        message = commit["message"].split("\n")[0]
        logger.info(f"커밋 리뷰: {owner}/{repo_name}@{sha[:7]} - {message}")

        files = await get_commit_files(owner, repo_name, sha, token)
        logger.info(f"  {len(files)}개 파일 발견")

        if not files:
            continue

        issues = await review_all_files(files)
        logger.info(f"  {len(issues)}건의 이슈 발견")

        if issues:
            await post_commit_comment(owner, repo_name, sha, issues, token)
            logger.info("  커밋 코멘트 게시 완료")


@app.get("/health")
async def health():
    return {"status": "ok"}
