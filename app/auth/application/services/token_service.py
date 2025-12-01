import json
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional

from redis.asyncio import Redis


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class TokenService:
    """개발용 액세스/리프레시 토큰 관리 서비스 (Redis)"""

    def __init__(
        self,
        redis_client: Redis,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ):
        self.redis = redis_client
        self.access_ttl_seconds = access_ttl_seconds
        self.refresh_ttl_seconds = refresh_ttl_seconds

    @staticmethod
    def _access_key(token: str) -> str:
        return f"access:{token}"

    @staticmethod
    def _refresh_key(token: str) -> str:
        return f"refresh:{token}"

    def _serialize(self, payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _deserialize(self, value: Optional[str]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    async def issue_tokens(self, payload: Dict[str, Any]) -> TokenPair:
        """액세스/리프레시 토큰 생성 후 Redis에 저장"""
        access_token = f"acc-{secrets.token_urlsafe(32)}"
        refresh_token = f"ref-{secrets.token_urlsafe(48)}"

        serialized = self._serialize(payload)

        await self.redis.set(
            self._access_key(access_token),
            serialized,
            ex=self.access_ttl_seconds,
        )
        await self.redis.set(
            self._refresh_key(refresh_token),
            serialized,
            ex=self.refresh_ttl_seconds,
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def get_access_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """액세스 토큰으로 페이로드 조회"""
        data = await self.redis.get(self._access_key(token))
        return self._deserialize(data)

    async def rotate_tokens(self, refresh_token: str) -> TokenPair:
        """리프레시 토큰으로 새 토큰 재발급"""
        data = await self.redis.get(self._refresh_key(refresh_token))
        payload = self._deserialize(data)

        if payload is None:
            raise ValueError("유효하지 않은 리프레시 토큰입니다.")

        # 이전 리프레시 토큰 폐기
        await self.redis.delete(self._refresh_key(refresh_token))

        # 새 토큰 발급
        return await self.issue_tokens(payload)

    async def revoke_tokens(self, access_token: str, refresh_token: str) -> None:
        """토큰 쌍 폐기"""
        await self.redis.delete(
            self._access_key(access_token),
            self._refresh_key(refresh_token),
        )
