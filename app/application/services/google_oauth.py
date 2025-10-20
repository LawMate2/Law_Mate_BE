from typing import Any, Dict

import httpx


class GoogleOAuthError(Exception):
    """Google OAuth 처리 중 오류"""


class GoogleOAuthService:
    """Google OAuth 사용자 정보 조회 서비스"""

    USER_INFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Google 사용자 정보 조회"""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.USER_INFO_ENDPOINT, headers=headers)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Google 사용자 정보 요청 중 오류가 발생했습니다.") from exc

        if response.status_code != 200:
            raise GoogleOAuthError(
                f"Google 사용자 정보 조회 실패 (status: {response.status_code})"
            )

        payload = response.json()
        if "sub" not in payload or "email" not in payload:
            raise GoogleOAuthError("Google 사용자 정보가 올바르지 않습니다.")

        return payload
