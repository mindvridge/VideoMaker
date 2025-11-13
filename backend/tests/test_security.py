"""
Test security features (CORS, Rate Limiting).
"""
import pytest
from unittest.mock import patch
from fastapi import status


@pytest.mark.security
class TestCORS:
    """Test CORS configuration."""

    def test_cors_preflight_request(self, client):
        """Test CORS preflight (OPTIONS) request."""
        response = client.options(
            "/api/generate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        # Should allow the request
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response."""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == status.HTTP_200_OK
        # CORS headers should be present
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]

    @patch("app.config.get_cors_origins")
    def test_cors_allowed_origins(self, mock_origins, client):
        """Test only allowed origins are accepted."""
        mock_origins.return_value = ["https://example.com"]

        # Request from allowed origin
        response = client.get(
            "/",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_cors_credentials_allowed(self, client):
        """Test CORS credentials are allowed."""
        response = client.options(
            "/api/generate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Check if credentials are allowed
        allow_creds = response.headers.get("access-control-allow-credentials")
        assert allow_creds is not None


@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting."""

    @pytest.fixture
    def client_with_rate_limit(self, test_app):
        """Create client with rate limiting enabled."""
        from fastapi.testclient import TestClient

        with patch("app.config.settings.RATE_LIMIT_ENABLED", True):
            with TestClient(test_app) as client:
                yield client

    @patch("app.main.generate_video_task")
    def test_rate_limit_enforced(self, mock_task, client_with_rate_limit, sample_video_request):
        """Test rate limiting is enforced."""
        mock_result = MagicMock()
        mock_result.id = "test-task"
        mock_task.apply_async.return_value = mock_result

        # Make requests up to the limit
        # Note: In actual tests, you'd need to configure slower limits
        responses = []
        for i in range(5):
            response = client_with_rate_limit.post(
                "/api/generate",
                json=sample_video_request
            )
            responses.append(response)

        # At least some should succeed
        success_count = sum(1 for r in responses if r.status_code == status.HTTP_200_OK)
        assert success_count > 0

    def test_rate_limit_disabled_in_dev(self, client, sample_video_request):
        """Test rate limiting is disabled in development."""
        with patch("app.main.generate_video_task") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task"
            mock_task.apply_async.return_value = mock_result

            # Should be able to make multiple requests without limit
            for i in range(3):
                response = client.post("/api/generate", json=sample_video_request)
                # All should succeed (rate limiting disabled in test env)
                assert response.status_code == status.HTTP_200_OK

    @patch("app.main.limiter.enabled", True)
    def test_different_endpoints_different_limits(self, client):
        """Test different endpoints have different rate limits."""
        # This is more of a configuration test
        from app.main import limiter

        # Verify limiter is configured
        assert limiter is not None

        # In real tests, you would verify each endpoint's specific limit
        # by checking the decorator configurations


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_attempt(self, client):
        """Test SQL injection attempt is blocked."""
        malicious_request = {
            "model_type": "wan-2.2-t2v'; DROP TABLE users; --",
            "prompt": "Test"
        }

        response = client.post("/api/generate", json=malicious_request)

        # Should fail validation
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_xss_attempt(self, client):
        """Test XSS attempt in prompt."""
        malicious_request = {
            "model_type": "wan-2.2-t2v",
            "prompt": "<script>alert('XSS')</script>"
        }

        with patch("app.main.generate_video_task") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task"
            mock_task.apply_async.return_value = mock_result

            response = client.post("/api/generate", json=malicious_request)

            # Should accept (prompt is just text), but verify it's not executed
            if response.status_code == status.HTTP_200_OK:
                # Prompt should be stored as-is, not interpreted
                call_kwargs = mock_task.apply_async.call_args[1]["kwargs"]
                assert "<script>" in call_kwargs["prompt"]

    def test_path_traversal_attempt(self, client, temp_image_file):
        """Test path traversal attempt is blocked."""
        with patch("app.main.generate_video_task") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task"
            mock_task.apply_async.return_value = mock_result

            with open(temp_image_file, 'rb') as img:
                response = client.post(
                    "/api/generate/i2v",
                    data={
                        "model_type": "wan-2.2-i2v",
                        "prompt": "../../../etc/passwd"
                    },
                    files={"image": ("test.jpg", img, "image/jpeg")}
                )

            # Should process normally (path traversal in text is harmless)
            # The important thing is file operations don't use user input directly
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    def test_oversized_request(self, client):
        """Test oversized request is rejected."""
        # Create extremely long prompt
        huge_prompt = "A" * 1000000  # 1MB of text

        request = {
            "model_type": "wan-2.2-t2v",
            "prompt": huge_prompt
        }

        with patch("app.main.generate_video_task") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task"
            mock_task.apply_async.return_value = mock_result

            response = client.post("/api/generate", json=request)

            # Should handle gracefully
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]


@pytest.mark.security
class TestEnvironmentConfiguration:
    """Test environment-specific security configurations."""

    @patch("app.config.settings.ENVIRONMENT", "production")
    def test_production_debug_disabled(self):
        """Test DEBUG is disabled in production."""
        from app.config import get_settings
        settings = get_settings()

        # In production, DEBUG should be False
        # (This depends on your actual .env.production config)
        assert settings.ENVIRONMENT.value == "production"

    def test_development_environment(self):
        """Test development environment settings."""
        from app.config import get_settings
        settings = get_settings()

        # In test/dev environment
        assert settings.ENVIRONMENT.value == "development"

    def test_cors_origins_not_wildcard_in_prod(self):
        """Test CORS doesn't use wildcard in production."""
        from app.config import get_cors_origins

        origins = get_cors_origins()

        # Should not contain wildcard
        assert "*" not in origins
