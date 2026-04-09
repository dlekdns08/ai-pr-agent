"""GitHub App 인증 처리 — JWT 생성 및 Installation Token 발급."""

import os
import time

import httpx
import jwt

GITHUB_API = "https://api.github.com"

APP_ID = os.environ.get("GITHUB_APP_ID", "")
PRIVATE_KEY_PATH = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH", "/app/github-app.pem")


def _load_private_key() -> str:
    with open(PRIVATE_KEY_PATH) as f:
        return f.read()


def _create_jwt() -> str:
    """GitHub App JWT를 생성한다 (10분 유효)."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": APP_ID,
    }
    private_key = _load_private_key()
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Installation ID로 액세스 토큰을 발급받는다 (1시간 유효)."""
    token_jwt = _create_jwt()
    url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token_jwt}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()

    return resp.json()["token"]
