"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Application
    APP_NAME: str = "SmartFU"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    DB_PASSWORD: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:3001", "http://localhost:3002"]
    
    # API Keys
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    # ML Models
    MODELS_PATH: str = "./models"
    ENABLE_MODEL_TRAINING: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Email (Optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "noreply@smartfu.com"
    
    # SMS (Optional - Twilio)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    
    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # Feature Flags
    ENABLE_AI_AGENTS: bool = True
    ENABLE_EMAIL_FOLLOWUPS: bool = False
    ENABLE_SMS_FOLLOWUPS: bool = False
    ENABLE_SIGNAL_DETECTION: bool = True
    
    # Monitoring
    SENTRY_DSN: str = ""
    ENABLE_ANALYTICS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    """
    return Settings()


settings = get_settings()
