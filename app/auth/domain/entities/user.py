from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class User:
    """Google OAuth 회원 도메인 엔티티"""

    google_id: str
    email: str
    id: Optional[int] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    verified_email: Optional[bool] = None
    access_token: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_google_payload(cls, payload: Dict[str, Any], access_token: str) -> "User":
        """Google 사용자 정보에서 User 엔티티 생성"""
        return cls(
            google_id=payload.get("sub"),
            email=payload.get("email"),
            name=payload.get("name"),
            given_name=payload.get("given_name"),
            family_name=payload.get("family_name"),
            picture=payload.get("picture"),
            locale=payload.get("locale"),
            verified_email=payload.get("email_verified"),
            access_token=access_token,
            last_login_at=datetime.now(timezone.utc),
            metadata={
                "hd": payload.get("hd"),
                "profile": payload.get("profile"),
            }
        )

    def update_from_google_payload(self, payload: Dict[str, Any], access_token: str) -> None:
        """Google 사용자 정보로 엔티티 갱신"""
        self.name = payload.get("name")
        self.given_name = payload.get("given_name")
        self.family_name = payload.get("family_name")
        self.picture = payload.get("picture")
        self.locale = payload.get("locale")
        self.verified_email = payload.get("email_verified")
        self.access_token = access_token
        self.last_login_at = datetime.now(timezone.utc)

        hd = payload.get("hd")
        profile = payload.get("profile")
        if hd:
            self.metadata["hd"] = hd
        if profile:
            self.metadata["profile"] = profile
