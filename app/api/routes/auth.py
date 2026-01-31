from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.core.logging import get_logger

router = APIRouter(prefix="/v1/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    password_hash = hash_password(request.password)
    user = User(
        external_auth_id=request.email,  # Use email as external_auth_id for simple JWT
        email=request.email,
        password_hash=password_hash
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"User registered successfully", user_id=str(user.id), email=request.email)
    
    return AuthResponse(
        access_token=access_token,
        user_id=str(user.id)
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token"""
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"User logged in successfully", user_id=str(user.id), email=request.email)
    
    return AuthResponse(
        access_token=access_token,
        user_id=str(user.id)
    )
