from pydantic import BaseModel, EmailStr
from uuid import UUID


class RegisterRequest(BaseModel):
    """Request to register a new user"""
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Request to login"""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response with token"""
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserResponse(BaseModel):
    """User information"""
    id: UUID
    email: str
    external_auth_id: str
    
    class Config:
        from_attributes = True
