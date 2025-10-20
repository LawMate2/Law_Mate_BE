from typing import Optional, Tuple

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ..services.google_oauth import GoogleOAuthService


class UserUseCases:
    """회원 관련 유스케이스"""

    def __init__(
        self,
        user_repository: UserRepository,
        google_oauth_service: GoogleOAuthService
    ):
        self.user_repository = user_repository
        self.google_oauth_service = google_oauth_service

    async def login_with_google(self, access_token: str) -> Tuple[User, bool]:
        """Google OAuth 로그인 처리

        Returns:
            Tuple[User, bool]: (회원 엔티티, 신규 가입 여부)
        """
        payload = await self.google_oauth_service.get_user_info(access_token)
        google_id = payload.get("sub")

        user = await self.user_repository.find_by_google_id(google_id)
        is_new_user = False

        if user is None:
            user = User.from_google_payload(payload, access_token)
            saved_user = await self.user_repository.save(user)
            is_new_user = True
            return saved_user, is_new_user

        user.update_from_google_payload(payload, access_token)
        saved_user = await self.user_repository.save(user)
        return saved_user, is_new_user

    async def get_user(self, user_id: int) -> Optional[User]:
        """회원 상세 조회"""
        return await self.user_repository.find_by_id(user_id)

    async def list_users(self, skip: int = 0, limit: int = 100):
        """회원 목록 조회"""
        return await self.user_repository.find_all(skip, limit)

    async def delete_user(self, user_id: int) -> bool:
        """회원 삭제"""
        return await self.user_repository.delete(user_id)
