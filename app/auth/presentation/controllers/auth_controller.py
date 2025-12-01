from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.auth.application.services.google_oauth import GoogleOAuthError
from app.auth.application.use_cases.user_use_cases import UserUseCases
from app.auth.domain.entities.user import User
from app.auth.presentation.schemas.auth_schemas import (
    DevLoginRequest,
    DevLoginResponse,
    DevSignupRequest,
    GoogleLoginRequest,
    GoogleLoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserSchema,
)
from app.core.config import settings
from app.shared.dependencies import get_user_use_cases


class AuthController:
    """인증 및 회원 컨트롤러"""

    def __init__(self):
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self._register_routes()

    def _register_routes(self):
        """라우트 등록"""

        @self.router.post("/dev/signup", response_model=DevLoginResponse)
        async def dev_signup(
            request: DevSignupRequest,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            """개발용 회원가입 + 토큰 발급 (access + refresh)"""
            if settings.environment not in ["development", "dev", "local"]:
                raise HTTPException(
                    status_code=403,
                    detail="개발용 회원가입은 개발 환경에서만 사용 가능합니다."
                )

            try:
                user, is_new, tokens = await user_use_cases.dev_signup(request.email, request.name)
                return DevLoginResponse(
                    user=self._to_user_schema(user),
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token,
                    is_new_user=is_new
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"개발 회원가입 처리 중 오류: {str(e)}")

        @self.router.post("/dev/login", response_model=DevLoginResponse)
        async def dev_login(
            request: DevLoginRequest,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            """개발용 로그인 (이메일 기반, 개발 환경에서만 사용)"""
            if settings.environment not in ["development", "dev", "local"]:
                raise HTTPException(
                    status_code=403,
                    detail="개발용 로그인은 개발 환경에서만 사용 가능합니다."
                )

            try:
                user, is_new, tokens = await user_use_cases.dev_login(request.email, request.name)
                return DevLoginResponse(
                    user=self._to_user_schema(user),
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token,
                    is_new_user=is_new
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"개발 로그인 처리 중 오류: {str(e)}")

        @self.router.post("/google", response_model=GoogleLoginResponse)
        async def google_login(
            request: GoogleLoginRequest,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            """Google OAuth 로그인 (Authorization Code Flow)"""
            try:
                user, is_new, tokens = await user_use_cases.login_with_google(request.code)
                return GoogleLoginResponse(
                    user=self._to_user_schema(user),
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token,
                    is_new_user=is_new
                )
            except GoogleOAuthError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Google 로그인 처리 중 오류: {str(e)}")

        @self.router.post("/dev/refresh", response_model=RefreshTokenResponse)
        async def refresh_tokens(
            request: RefreshTokenRequest,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            """리프레시 토큰으로 액세스/리프레시 재발급"""
            try:
                tokens = await user_use_cases.refresh_tokens(request.refresh_token)
                return RefreshTokenResponse(
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token
                )
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"리프레시 토큰 오류: {str(e)}")

        @self.router.get("/users/{user_id}", response_model=UserSchema)
        async def get_user(
            user_id: int,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            user = await user_use_cases.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
            return self._to_user_schema(user)

        @self.router.get("/users", response_model=List[UserSchema])
        async def list_users(
            skip: int = 0,
            limit: int = 100,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            users = await user_use_cases.list_users(skip, limit)
            return [self._to_user_schema(user) for user in users]

        @self.router.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            user_use_cases: UserUseCases = Depends(get_user_use_cases)
        ):
            deleted = await user_use_cases.delete_user(user_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
            return {"message": "회원이 삭제되었습니다."}

    def _to_user_schema(self, user: User) -> UserSchema:
        """도메인 엔티티를 스키마로 변환"""
        return UserSchema(
            id=user.id,
            email=user.email,
            name=user.name,
            given_name=user.given_name,
            family_name=user.family_name,
            picture=user.picture,
            locale=user.locale,
            verified_email=user.verified_email,
            last_login_at=user.last_login_at
        )
