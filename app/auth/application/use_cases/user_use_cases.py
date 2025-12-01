from datetime import datetime, timezone
from typing import Optional, Tuple

from app.auth.application.services.google_oauth import GoogleOAuthService
from app.auth.application.services.token_service import TokenService, TokenPair
from app.auth.domain.entities.user import User
from app.auth.domain.repositories.user_repository import UserRepository


class UserUseCases:
    """회원 관련 유스케이스"""

    def __init__(
        self,
        user_repository: UserRepository,
        google_oauth_service: GoogleOAuthService,
        token_service: TokenService
    ):
        self.user_repository = user_repository
        self.google_oauth_service = google_oauth_service
        self.token_service = token_service

    async def login_with_google(self, code: str) -> Tuple[User, bool, TokenPair]:
        """Google OAuth 로그인 처리 (Authorization Code Flow)

        Args:
            code: Google OAuth Authorization Code

        Returns:
            Tuple[User, bool, TokenPair]: (회원 엔티티, 신규 가입 여부, 토큰 쌍)
        """
        # 1. Authorization code를 access token으로 교환
        access_token = await self.google_oauth_service.exchange_code_for_token(code)

        # 2. Access token으로 사용자 정보 조회
        payload = await self.google_oauth_service.get_user_info(access_token)
        google_id = payload.get("sub")

        user = await self.user_repository.find_by_google_id(google_id)
        is_new_user = False

        if user is None:
            user = User.from_google_payload(payload, access_token)
            saved_user = await self.user_repository.save(user)
            is_new_user = True
            user = saved_user
        else:
            user.update_from_google_payload(payload, access_token)
            saved_user = await self.user_repository.save(user)
            user = saved_user

        # 3. 자체 액세스/리프레시 토큰 발급
        tokens = await self._issue_tokens_for_user(user)
        return user, is_new_user, tokens

    async def get_user(self, user_id: int) -> Optional[User]:
        """회원 상세 조회"""
        return await self.user_repository.find_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 회원 조회"""
        return await self.user_repository.find_by_email(email)

    async def list_users(self, skip: int = 0, limit: int = 100):
        """회원 목록 조회"""
        return await self.user_repository.find_all(skip, limit)

    async def get_user_by_access_token(self, access_token: str) -> Optional[User]:
        """액세스 토큰으로 회원 조회"""
        return await self.user_repository.find_by_access_token(access_token)

    async def delete_user(self, user_id: int) -> bool:
        """회원 삭제"""
        return await self.user_repository.delete(user_id)

    async def dev_login(self, email: str, name: Optional[str] = None) -> Tuple[User, bool, TokenPair]:
        """개발용 로그인 (이메일 기반)

        Args:
            email: 사용자 이메일
            name: 사용자 이름 (선택)

        Returns:
            Tuple[User, bool, TokenPair]: (회원 엔티티, 신규 가입 여부, 토큰 쌍)
        """
        user = await self.user_repository.find_by_email(email)
        is_new_user = False

        if user is None:
            # 개발용 Google ID 생성 (dev-prefix)
            dev_google_id = f"dev-{email}"
            user = User(
                google_id=dev_google_id,
                email=email,
                name=name or email.split("@")[0],
                verified_email=True,
                access_token=f"dev-token-{email}",
                last_login_at=datetime.now(timezone.utc),
                metadata={"is_dev_user": True}
            )
            saved_user = await self.user_repository.save(user)
            is_new_user = True
            user = saved_user
        else:
            # 기존 사용자 업데이트
            user.last_login_at = datetime.now(timezone.utc)
            if name:
                user.name = name
            await self.user_repository.save(user)

        # 토큰 발급 (개발용)
        tokens = await self._issue_tokens_for_user(user)
        return user, is_new_user, tokens

    async def dev_signup(self, email: str, name: Optional[str] = None) -> Tuple[User, bool, TokenPair]:
        """개발용 회원가입 (이메일 기반)"""
        user = await self.user_repository.find_by_email(email)
        is_new_user = False

        if user is None:
            dev_google_id = f"dev-{email}"
            user = User(
                google_id=dev_google_id,
                email=email,
                name=name or email.split("@")[0],
                verified_email=True,
                access_token=f"dev-token-{email}",
                last_login_at=datetime.now(timezone.utc),
                metadata={"is_dev_user": True}
            )
            user = await self.user_repository.save(user)
            is_new_user = True
        else:
            user.last_login_at = datetime.now(timezone.utc)
            if name:
                user.name = name
            await self.user_repository.save(user)

        tokens = await self._issue_tokens_for_user(user)
        return user, is_new_user, tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """리프레시 토큰으로 새 토큰 발급"""
        tokens = await self.token_service.rotate_tokens(refresh_token)
        payload = await self.token_service.get_access_payload(tokens.access_token)

        if not payload:
            raise ValueError("토큰 페이로드를 찾을 수 없습니다.")

        user_id = payload.get("user_id")
        if user_id is None:
            raise ValueError("토큰에 사용자 정보가 없습니다.")

        user = await self.user_repository.find_by_id(user_id)
        if user:
            user.access_token = tokens.access_token
            await self.user_repository.save(user)

        return tokens

    async def _issue_tokens_for_user(self, user: User) -> TokenPair:
        """사용자용 액세스/리프레시 토큰 발급 및 저장"""
        payload = {"user_id": user.id, "email": user.email}
        tokens = await self.token_service.issue_tokens(payload)
        user.access_token = tokens.access_token
        await self.user_repository.save(user)
        return tokens
