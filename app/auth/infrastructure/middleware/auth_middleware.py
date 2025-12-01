"""인증 미들웨어 및 의존성"""
from typing import Optional

from fastapi import Depends, HTTPException, Header, status

from app.auth.application.use_cases.user_use_cases import UserUseCases
from app.auth.application.services.token_service import TokenService
from app.auth.domain.entities.user import User
from app.shared.dependencies import get_user_use_cases, get_token_service


# 공개 엔드포인트 (인증 불필요)
PUBLIC_ENDPOINTS = [
    "/",
    "/health",
    "/architecture",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/google",
    "/auth/dev/login",
    "/auth/dev/signup",
]


async def get_current_user(
    authorization: Optional[str] = Header(None),
    user_use_cases: UserUseCases = Depends(get_user_use_cases),
    token_service: TokenService = Depends(get_token_service)
) -> User:
    """현재 로그인한 사용자 정보 가져오기

    Authorization 헤더에서 토큰을 추출하여 사용자 조회
    형식: "Bearer {access_token}" 또는 "{access_token}"
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Bearer 토큰 파싱
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    # 개발용 토큰 처리
    if token.startswith("dev-token-"):
        email = token.replace("dev-token-", "")
        user = await user_use_cases.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        return user

    # Redis 기반 액세스 토큰 처리
    payload = await token_service.get_access_payload(token)
    if payload:
        user_id = payload.get("user_id")
        if user_id is not None:
            user = await user_use_cases.get_user(user_id)
            if user:
                return user

    # DB에 저장된 토큰(구 Google 토큰 등) 처리
    user = await user_use_cases.get_user_by_access_token(token)
    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    user_use_cases: UserUseCases = Depends(get_user_use_cases),
    token_service: TokenService = Depends(get_token_service)
) -> Optional[User]:
    """선택적으로 현재 사용자 정보 가져오기 (인증 선택)"""
    if not authorization:
        return None

    try:
        return await get_current_user(
            authorization=authorization,
            user_use_cases=user_use_cases,
            token_service=token_service
        )
    except HTTPException:
        return None
