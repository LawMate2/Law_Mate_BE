from typing import List, Optional
from sqlalchemy.orm import Session

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...db.models import User as UserModel


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy 기반 회원 저장소"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def save(self, user: User) -> User:
        """회원 저장/업데이트"""
        if user.id is None:
            db_user = UserModel(
                google_id=user.google_id,
                email=user.email,
                name=user.name,
                given_name=user.given_name,
                family_name=user.family_name,
                picture=user.picture,
                locale=user.locale,
                verified_email=user.verified_email,
                access_token=user.access_token,
                last_login_at=user.last_login_at,
                metadata=user.metadata
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            user.id = db_user.id
            user.created_at = db_user.created_at
            user.updated_at = db_user.updated_at
        else:
            db_user = self.db.query(UserModel).filter(
                UserModel.id == user.id
            ).first()
            if db_user:
                db_user.name = user.name
                db_user.given_name = user.given_name
                db_user.family_name = user.family_name
                db_user.picture = user.picture
                db_user.locale = user.locale
                db_user.verified_email = user.verified_email
                db_user.access_token = user.access_token
                db_user.last_login_at = user.last_login_at
                db_user.metadata = user.metadata
                self.db.commit()
                self.db.refresh(db_user)
                user.updated_at = db_user.updated_at

        return user

    async def find_by_id(self, user_id: int) -> Optional[User]:
        """ID로 회원 조회"""
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_domain(db_user) if db_user else None

    async def find_by_google_id(self, google_id: str) -> Optional[User]:
        """Google ID로 회원 조회"""
        db_user = self.db.query(UserModel).filter(UserModel.google_id == google_id).first()
        return self._to_domain(db_user) if db_user else None

    async def find_by_email(self, email: str) -> Optional[User]:
        """이메일로 회원 조회"""
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._to_domain(db_user) if db_user else None

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """회원 목록 조회"""
        db_users = self.db.query(UserModel).offset(skip).limit(limit).all()
        return [self._to_domain(db_user) for db_user in db_users]

    async def delete(self, user_id: int) -> bool:
        """회원 삭제"""
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False

    def _to_domain(self, db_user: UserModel) -> User:
        """DB 모델을 도메인 엔티티로 변환"""
        return User(
            id=db_user.id,
            google_id=db_user.google_id,
            email=db_user.email,
            name=db_user.name,
            given_name=db_user.given_name,
            family_name=db_user.family_name,
            picture=db_user.picture,
            locale=db_user.locale,
            verified_email=db_user.verified_email,
            access_token=db_user.access_token,
            last_login_at=db_user.last_login_at,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            metadata=db_user.metadata or {}
        )
