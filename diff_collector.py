"""GitHub API를 통해 PR의 변경된 파일과 diff를 수집한다."""

import os
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

LANGUAGE_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
}


def _detect_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return LANGUAGE_MAP.get(ext, "unknown")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


async def get_pr_files(owner: str, repo: str, pr_number: str) -> list[dict]:
    """PR의 변경된 파일 목록과 patch(diff)를 가져온다."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()

    files = []
    for f in resp.json():
        patch = f.get("patch", "")
        if not patch:
            continue

        files.append(
            {
                "filename": f["filename"],
                "patch": patch,
                "language": _detect_language(f["filename"]),
                "status": f.get("status", ""),  # added, modified, removed
                "additions": f.get("additions", 0),
            }
        )

    return files
