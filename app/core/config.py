from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql://chatuser:chatpass@localhost:5432/chatdb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 10080  # 7 days
    
    # External Integration
    INTEGRATION_URL: Optional[str] = None
    
    # Gemini API
    GEMINI_API_KEY: Optional[str] = None
    
    # Media Storage
    MEDIA_DIR: str = "./data/media"
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]  # Allow all origins for VM access
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
