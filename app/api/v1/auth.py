# ============================================================================
# MARKETMIND AI - AUTHENTICATION ROUTER
# ============================================================================

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models import User
from app.schemas.auth import UserRegister, UserLogin, UserOut, Token
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """Registers a new user analyst account.
    Validates email uniqueness and hashes passwords using bcrypt.
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_in)
    return user


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates credentials against database password hashes, returning a JWT token."""
    auth_service = AuthService(db)
    token_details = await auth_service.authenticate_user(login_data)
    return token_details


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Fetches details for the currently authenticated user profile."""
    return current_user
