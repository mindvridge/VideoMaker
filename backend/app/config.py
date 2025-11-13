"""
Configuration management for the video generation application.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AI Video Generation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "video-gen-outputs"
    CLOUDFRONT_DOMAIN: Optional[str] = None

    # GPU Settings
    CUDA_VISIBLE_DEVICES: str = "0"
    ENABLE_CPU_OFFLOAD: bool = True
    USE_FP16: bool = False
    USE_BF16: bool = True

    # Model Settings
    MODELS_CACHE_DIR: str = "/root/.cache/huggingface"
    MAX_MODELS_IN_MEMORY: int = 1

    # Video Generation Defaults
    DEFAULT_NUM_FRAMES: int = 81
    DEFAULT_FPS: int = 8
    DEFAULT_HEIGHT: int = 720
    DEFAULT_WIDTH: int = 1280
    MAX_VIDEO_DURATION: int = 300  # seconds

    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}

    # Storage
    OUTPUT_DIR: str = "/tmp/video-outputs"
    PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour

    # FFmpeg Settings
    FFMPEG_PRESET: str = "medium"
    FFMPEG_CRF: int = 23
    FFMPEG_VIDEO_CODEC: str = "libx264"
    FFMPEG_AUDIO_CODEC: str = "aac"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create output directory if it doesn't exist
settings = get_settings()
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.MODELS_CACHE_DIR, exist_ok=True)
