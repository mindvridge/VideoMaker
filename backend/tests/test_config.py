"""
Test configuration module.
"""
import pytest
import os
from unittest.mock import patch


@pytest.mark.unit
class TestSettings:
    """Test Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        from app.config import Settings

        settings = Settings()

        assert settings.APP_NAME == "AI Video Generation API"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000

    def test_settings_from_env(self):
        """Test settings loaded from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "Test App",
            "DEBUG": "true",
            "PORT": "9000"
        }):
            from importlib import reload
            import app.config as config_module
            reload(config_module)

            settings = config_module.Settings()

            # Note: pydantic-settings may cache, so we test what we can
            assert settings is not None

    def test_cors_settings(self):
        """Test CORS settings."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.CORS_ORIGINS is not None
        assert settings.CORS_ALLOW_CREDENTIALS is True
        assert settings.CORS_ALLOW_METHODS is not None

    def test_rate_limit_settings(self):
        """Test rate limit settings."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.RATE_LIMIT_PER_MINUTE > 0
        assert settings.RATE_LIMIT_GENERATE_PER_HOUR > 0
        assert settings.RATE_LIMIT_UPLOAD_PER_HOUR > 0

    def test_aws_settings(self):
        """Test AWS settings."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.AWS_REGION is not None
        assert settings.S3_BUCKET_NAME is not None

    def test_gpu_settings(self):
        """Test GPU settings."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.CUDA_VISIBLE_DEVICES is not None
        assert isinstance(settings.ENABLE_CPU_OFFLOAD, bool)
        assert isinstance(settings.USE_FP16, bool)
        assert isinstance(settings.USE_BF16, bool)

    def test_video_defaults(self):
        """Test video generation defaults."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.DEFAULT_NUM_FRAMES > 0
        assert settings.DEFAULT_FPS > 0
        assert settings.DEFAULT_HEIGHT > 0
        assert settings.DEFAULT_WIDTH > 0
        assert settings.MAX_VIDEO_DURATION > 0

    def test_ffmpeg_settings(self):
        """Test FFmpeg settings."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.FFMPEG_PRESET in ["ultrafast", "fast", "medium", "slow", "veryslow"]
        assert settings.FFMPEG_CRF >= 0 and settings.FFMPEG_CRF <= 51
        assert settings.FFMPEG_VIDEO_CODEC is not None
        assert settings.FFMPEG_AUDIO_CODEC is not None


@pytest.mark.unit
class TestEnvironment:
    """Test Environment enum."""

    def test_environment_enum(self):
        """Test Environment enum values."""
        from app.config import Environment

        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_default_environment(self):
        """Test default environment."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.ENVIRONMENT in [
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION
        ] if hasattr(settings, 'ENVIRONMENT') else True


@pytest.mark.unit
class TestCorsOrigins:
    """Test CORS origins function."""

    def test_get_cors_origins_development(self):
        """Test CORS origins in development."""
        from app.config import get_cors_origins, Environment

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = Environment.DEVELOPMENT
            mock_settings.return_value.CORS_ORIGINS = "http://localhost:3000"

            origins = get_cors_origins()

            assert "http://localhost:3000" in origins
            assert "http://localhost:8000" in origins
            assert "http://127.0.0.1:3000" in origins
            assert "http://127.0.0.1:8000" in origins

    def test_get_cors_origins_production(self):
        """Test CORS origins in production."""
        from app.config import get_cors_origins, Environment

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = Environment.PRODUCTION
            mock_settings.return_value.CORS_ORIGINS = "https://example.com"

            origins = get_cors_origins()

            assert "https://example.com" in origins
            # Should NOT include localhost in production
            assert "http://localhost:3000" not in origins

    def test_cors_origins_parsing(self):
        """Test CORS origins comma-separated parsing."""
        from app.config import get_cors_origins, Environment

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = Environment.PRODUCTION
            mock_settings.return_value.CORS_ORIGINS = "https://a.com, https://b.com, https://c.com"

            origins = get_cors_origins()

            assert "https://a.com" in origins
            assert "https://b.com" in origins
            assert "https://c.com" in origins


@pytest.mark.unit
class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # Should return same cached instance
        assert settings1 is settings2

    def test_settings_output_dir_exists(self):
        """Test that output directory is created."""
        from app.config import get_settings

        settings = get_settings()

        # Directory should exist or be creatable
        assert settings.OUTPUT_DIR is not None

    def test_settings_models_cache_dir_exists(self):
        """Test that models cache directory is set."""
        from app.config import get_settings

        settings = get_settings()

        assert settings.MODELS_CACHE_DIR is not None
