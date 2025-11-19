from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class GoogleLoginRequest(BaseModel):
    """Google OAuth 로그인 요청"""

    access_token: str = Field(..., min_length=1, description="Google OAuth Access Token")


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
    is_new_user: bool
