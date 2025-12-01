import json
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis


class ChatCacheService:
    """채팅 히스토리 Redis 캐싱 서비스"""

    def __init__(self, redis_client: Redis, cache_ttl: int = 3600):
        """
        Args:
            redis_client: Redis 클라이언트
            cache_ttl: 캐시 유효 시간 (초), 기본 1시간
        """
        self.redis = redis_client
        self.cache_ttl = cache_ttl

    def _get_cache_key(self, user_id: int) -> str:
        """사용자 채팅 히스토리 캐시 키 생성"""
        return f"chat:history:user:{user_id}"

    async def get_chat_history(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Redis에서 사용자 채팅 히스토리 조회

        Args:
            user_id: 사용자 ID

        Returns:
            채팅 히스토리 리스트 (없으면 None)
        """
        cache_key = self._get_cache_key(user_id)
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None

        return None

    async def set_chat_history(self, user_id: int, chat_history: List[Dict[str, Any]]):
        """
        사용자 채팅 히스토리를 Redis에 캐싱

        Args:
            user_id: 사용자 ID
            chat_history: 채팅 히스토리 데이터
        """
        cache_key = self._get_cache_key(user_id)
        serialized_data = json.dumps(chat_history, ensure_ascii=False, default=str)

        await self.redis.set(
            cache_key,
            serialized_data,
            ex=self.cache_ttl
        )

    async def invalidate_cache(self, user_id: int):
        """
        사용자 채팅 히스토리 캐시 무효화

        Args:
            user_id: 사용자 ID
        """
        cache_key = self._get_cache_key(user_id)
        await self.redis.delete(cache_key)