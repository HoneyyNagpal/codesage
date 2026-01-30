from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "CodeSage Analyzer"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/codesage"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # LLM Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "anthropic"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.3
    
    # Analysis Configuration
    MAX_FILE_SIZE_MB: int = 10
    MAX_CONCURRENT_ANALYSES: int = 5
    ANALYSIS_TIMEOUT_SECONDS: int = 600
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 3600
    ENABLE_FILE_CACHE: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
    ]
    
    # File paths
    TEMP_DIR: str = "/tmp/codesage"
    REPO_CACHE_DIR: str = "/tmp/codesage/repos"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Create required directories
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.REPO_CACHE_DIR, exist_ok=True)