# ============================================================================
# MARKETMIND AI - AUTHENTICATION SCHEMAS
# ============================================================================

import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema validating incoming registration requests."""
    email: EmailStr = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Cryptographically secure password")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema validating credentials on authentication requests."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Schema representing user profiles returned to clients."""
    id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema representing JWT access tokens issued upon login."""
    access_token: str
    token_type: str = "bearer"
