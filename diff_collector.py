"""GitHub API를 통해 PR 또는 커밋의 변경된 파일과 diff를 수집한다."""

from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"

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


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _parse_files(raw_files: list[dict]) -> list[dict]:
    """GitHub API 응답에서 파일 정보를 추출한다."""
    files = []
    for f in raw_files:
        patch = f.get("patch", "")
        if not patch:
            continue
        files.append(
            {
                "filename": f["filename"],
                "patch": patch,
                "language": _detect_language(f["filename"]),
                "status": f.get("status", ""),
                "additions": f.get("additions", 0),
            }
        )
    return files


async def get_pr_files(
    owner: str, repo: str, pr_number: int, token: str
) -> list[dict]:
    """PR의 변경된 파일 목록과 patch(diff)를 가져온다."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(token))
        resp.raise_for_status()

    return _parse_files(resp.json())


async def get_commit_files(
    owner: str, repo: str, commit_sha: str, token: str
) -> list[dict]:
    """커밋의 변경된 파일 목록과 patch(diff)를 가져온다."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{commit_sha}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(token))
        resp.raise_for_status()

    data = resp.json()
    return _parse_files(data.get("files", []))
