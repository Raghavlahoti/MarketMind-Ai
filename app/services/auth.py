# ============================================================================
# MARKETMIND AI - AUTHENTICATION SERVICE IMPLEMENTATION
# ============================================================================

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ValidationError, AuthenticationError
from app.core.security import hash_password, verify_password, create_access_token
from app.models import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserRegister, UserLogin
from app.services.base import BaseService


class AuthService(BaseService):
    """Orchestrates security and user profiles access workflows."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)

    async def register_user(self, user_in: UserRegister) -> User:
        """Ensures email uniqueness, hashes password, and persists user record."""
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ValidationError(message=f"Email '{user_in.email}' is already registered")

        hashed = hash_password(user_in.password)
        new_user = User(
            email=user_in.email,
            password_hash=hashed,
            first_name=user_in.first_name,
            last_name=user_in.last_name
        )
        
        await self.user_repo.create(new_user)
        return new_user

    async def authenticate_user(self, login_data: UserLogin) -> Dict[str, Any]:
        """Validates credentials and yields signed JWT token payload details."""
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise AuthenticationError(message="Invalid email or password")

        if not verify_password(login_data.password, user.password_hash):
            raise AuthenticationError(message="Invalid email or password")

        access_token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
