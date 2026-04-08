"""GitLab API를 통해 MR의 변경된 파일과 diff를 수집한다."""

import os
from pathlib import Path

import httpx

GITLAB_URL = os.environ.get("CI_SERVER_URL", "https://gitlab.com")
PRIVATE_TOKEN = os.environ.get("GITLAB_TOKEN", "")

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
    return {"PRIVATE-TOKEN": PRIVATE_TOKEN}


async def get_mr_changes(project_id: str, mr_iid: str) -> list[dict]:
    """MR의 변경된 파일 목록과 diff를 가져온다."""
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()

    data = resp.json()
    files = []

    for change in data.get("changes", []):
        diff = change.get("diff", "")
        if not diff:
            continue

        filename = change.get("new_path", change.get("old_path", ""))
        files.append(
            {
                "filename": filename,
                "patch": diff,
                "language": _detect_language(filename),
                "new_file": change.get("new_file", False),
                "deleted_file": change.get("deleted_file", False),
            }
        )

    return files
