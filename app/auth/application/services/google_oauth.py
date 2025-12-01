from typing import Any, Dict

import httpx


class GoogleOAuthError(Exception):
    """Google OAuth 처리 중 오류"""


class GoogleOAuthService:
    """Google OAuth 사용자 정보 조회 서비스"""

    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USER_INFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        timeout: float = 5.0
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.timeout = timeout

    async def exchange_code_for_token(self, code: str) -> str:
        """Authorization code를 access token으로 교환"""
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.TOKEN_ENDPOINT, data=data)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Google 토큰 교환 요청 중 오류가 발생했습니다.") from exc

        if response.status_code != 200:
            error_detail = response.json().get("error_description", "알 수 없는 오류")
            raise GoogleOAuthError(
                f"Google 토큰 교환 실패 (status: {response.status_code}): {error_detail}"
            )

        token_data = response.json()
        if "access_token" not in token_data:
            raise GoogleOAuthError("액세스 토큰을 받지 못했습니다.")

        return token_data["access_token"]

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
