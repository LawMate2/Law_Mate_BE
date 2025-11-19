from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.user import User


class UserRepository(ABC):
    """회원 저장소 인터페이스"""

    @abstractmethod
    async def save(self, user: User) -> User:
        """회원 저장"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]:
        """ID로 회원 조회"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_google_id(self, google_id: str) -> Optional[User]:
        """Google ID로 회원 조회"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """이메일로 회원 조회"""
        raise NotImplementedError

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """회원 목록 조회"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """회원 삭제"""
        raise NotImplementedError
