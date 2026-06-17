# ============================================================================
# MARKETMIND AI - DEPENDENCY INJECTION ARCHITECTURE
# ============================================================================

from typing import AsyncGenerator
from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.models import User
from app.repositories.user import UserRepository
from jose import JWTError

security_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency wrapper yielding database session. Alias for get_db_session."""
    async for session in get_db_session():
        yield session


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    """Extracts and verifies JWT token from request header, yielding user UUID."""
    if not credentials:
        raise AuthenticationError("Authorization header missing")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload: missing sub")
        return user_id
    except JWTError:
        raise AuthenticationError("Invalid or expired access token")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id_str: str = Depends(get_current_user_id)
) -> User:
    """Resolves and loads User context model matching verified token sub UUID."""
    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid user identity format")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_uuid)
    if not user:
        raise AuthenticationError("User session context does not exist")
    return user
