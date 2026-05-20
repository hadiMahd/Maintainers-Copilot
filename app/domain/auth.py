"""Authentication domain models."""

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class UserRead(BaseModel):
    """User response."""

    id: str
    email: str
    role: str
    is_active: bool


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class AuthContext(BaseModel):
    """Authenticated user context for dependency injection."""

    user_id: str
    email: str
    role: str


class AdminInvitationCreate(BaseModel):
    """Admin invitation creation request."""

    email: EmailStr
    expires_in_seconds: int | None = None


class AdminInvitationRead(BaseModel):
    """Admin invitation response."""

    id: str
    invitee_email: str
    status: str
    expires_at: str


class AdminInvitationAccept(BaseModel):
    """Admin invitation acceptance request."""

    token: str
