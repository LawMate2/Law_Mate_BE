from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class GoogleLoginRequest(BaseModel):
    """Google OAuth 로그인 요청 (Authorization Code Flow)"""

    code: str = Field(..., min_length=1, description="Google OAuth Authorization Code")


class UserSchema(BaseModel):
    """회원 응답 스키마"""

    id: int
    email: str
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[HttpUrl] = None
    locale: Optional[str] = None
    verified_email: Optional[bool] = None
    last_login_at: Optional[datetime] = None


class GoogleLoginResponse(BaseModel):
    """Google OAuth 로그인 응답"""

    user: UserSchema
    access_token: str
    refresh_token: Optional[str] = None
    is_new_user: bool
    token_type: str = "bearer"


class DevLoginRequest(BaseModel):
    """개발용 로그인 요청"""

    email: str = Field(..., min_length=1, description="사용자 이메일")
    name: Optional[str] = Field(default=None, description="사용자 이름")


class DevSignupRequest(BaseModel):
    """개발용 회원가입 요청"""

    email: str = Field(..., min_length=1, description="사용자 이메일")
    name: Optional[str] = Field(default=None, description="사용자 이름")


class TokenPairResponse(BaseModel):
    """액세스/리프레시 토큰 쌍"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class DevLoginResponse(BaseModel):
    """개발용 로그인 응답"""

    user: UserSchema
    access_token: str
    refresh_token: str
    is_new_user: bool
    message: str = "개발 환경 로그인 (프로덕션에서는 비활성화됨)"
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """리프레시 토큰 요청"""

    refresh_token: str = Field(..., min_length=10, description="리프레시 토큰")


class RefreshTokenResponse(TokenPairResponse):
    """리프레시 토큰 재발급 응답"""

    pass
