"""
Test API endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import status


@pytest.mark.api
class TestBasicEndpoints:
    """Test basic API endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns application info."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "supported_models" in data
        assert len(data["supported_models"]) > 0

    def test_health_check_healthy(self, client, mock_redis):
        """Test health check when all services are healthy."""
        with patch("app.main.redis_client", mock_redis):
            with patch("app.main.celery_app.control.inspect") as mock_inspect:
                mock_inspect.return_value.active.return_value = {"worker1": []}

                response = client.get("/health")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "healthy"
                assert data["redis"] == "connected"
                assert data["celery"] == "connected"

    def test_health_check_degraded(self, client):
        """Test health check when Redis is down."""
        with patch("app.main.redis_client.ping", side_effect=Exception("Connection failed")):
            response = client.get("/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "degraded"
            assert data["redis"] == "disconnected"

    def test_list_models(self, client):
        """Test listing available models."""
        response = client.get("/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

        # Check model structure
        model = data["models"][0]
        assert "id" in model
        assert "name" in model
        assert "type" in model


@pytest.mark.api
class TestVideoGenerationEndpoint:
    """Test video generation endpoint."""

    @patch("app.main.generate_video_task")
    def test_generate_video_success(self, mock_task, client, sample_video_request):
        """Test successful video generation request."""
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = "test-task-123"
        mock_task.apply_async.return_value = mock_result

        response = client.post("/api/generate", json=sample_video_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "submitted"
        assert "message" in data

        # Verify task was called with correct parameters
        mock_task.apply_async.assert_called_once()
        call_kwargs = mock_task.apply_async.call_args[1]["kwargs"]
        assert call_kwargs["model_type"] == sample_video_request["model_type"]
        assert call_kwargs["prompt"] == sample_video_request["prompt"]

    def test_generate_video_invalid_model(self, client):
        """Test video generation with invalid model type."""
        invalid_request = {
            "model_type": "invalid-model",
            "prompt": "Test prompt",
            "num_frames": 81,
            "height": 720,
            "width": 1280,
            "fps": 8
        }

        response = client.post("/api/generate", json=invalid_request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid model type" in response.json()["detail"]

    def test_generate_video_missing_prompt(self, client):
        """Test video generation without prompt."""
        invalid_request = {
            "model_type": "wan-2.2-t2v",
            "num_frames": 81
        }

        response = client.post("/api/generate", json=invalid_request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_generate_video_invalid_parameters(self, client):
        """Test video generation with invalid parameters."""
        invalid_request = {
            "model_type": "wan-2.2-t2v",
            "prompt": "Test",
            "num_frames": 1000,  # Too high
            "height": 5000,  # Too high
            "width": 5000,  # Too high
            "fps": 100  # Too high
        }

        response = client.post("/api/generate", json=invalid_request)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestImageToVideoEndpoint:
    """Test image-to-video generation endpoint."""

    @patch("app.main.generate_video_task")
    def test_i2v_generation_success(self, mock_task, client, temp_image_file):
        """Test successful I2V generation."""
        mock_result = MagicMock()
        mock_result.id = "test-i2v-task-123"
        mock_task.apply_async.return_value = mock_result

        with open(temp_image_file, 'rb') as img:
            response = client.post(
                "/api/generate/i2v",
                data={
                    "model_type": "wan-2.2-i2v",
                    "prompt": "Beautiful animation",
                    "num_frames": "81",
                    "height": "720",
                    "width": "1280",
                    "fps": "8"
                },
                files={"image": ("test.jpg", img, "image/jpeg")}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-i2v-task-123"
        assert data["status"] == "submitted"

    def test_i2v_with_t2v_model(self, client, temp_image_file):
        """Test I2V endpoint with T2V model should fail."""
        with open(temp_image_file, 'rb') as img:
            response = client.post(
                "/api/generate/i2v",
                data={
                    "model_type": "wan-2.2-t2v",  # T2V model
                    "prompt": "Test",
                },
                files={"image": ("test.jpg", img, "image/jpeg")}
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not support image-to-video" in response.json()["detail"]

    def test_i2v_without_image(self, client):
        """Test I2V endpoint without image."""
        response = client.post(
            "/api/generate/i2v",
            data={
                "model_type": "wan-2.2-i2v",
                "prompt": "Test"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestTaskStatusEndpoint:
    """Test task status endpoint."""

    @patch("app.main.AsyncResult")
    @patch("app.main.get_task_progress")
    def test_get_task_status_pending(self, mock_progress, mock_async_result, client):
        """Test getting status of pending task."""
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.successful.return_value = False
        mock_result.failed.return_value = False
        mock_async_result.return_value = mock_result

        mock_progress.return_value = {
            "progress": 0,
            "total": 100,
            "percentage": 0,
            "status": "Initializing"
        }

        response = client.get("/api/status/test-task-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "pending"
        assert data["progress"]["percentage"] == 0

    @patch("app.main.AsyncResult")
    @patch("app.main.get_task_progress")
    def test_get_task_status_success(self, mock_progress, mock_async_result, client, sample_task_result):
        """Test getting status of successful task."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.successful.return_value = True
        mock_result.result = sample_task_result
        mock_async_result.return_value = mock_result

        mock_progress.return_value = {
            "progress": 100,
            "total": 100,
            "percentage": 100,
            "status": "Completed"
        }

        response = client.get("/api/status/test-task-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "success"
        assert data["result"] == sample_task_result

    @patch("app.main.AsyncResult")
    @patch("app.main.get_task_progress")
    def test_get_task_status_failed(self, mock_progress, mock_async_result, client):
        """Test getting status of failed task."""
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_result.successful.return_value = False
        mock_result.failed.return_value = True
        mock_result.info = Exception("Generation failed")
        mock_async_result.return_value = mock_result

        response = client.get("/api/status/test-task-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "failure"
        assert data["error"] is not None


@pytest.mark.api
class TestTaskCancellation:
    """Test task cancellation endpoint."""

    @patch("app.main.cancel_task")
    def test_cancel_task_success(self, mock_cancel, client):
        """Test successful task cancellation."""
        mock_cancel.return_value = {
            "success": True,
            "message": "Task cancelled"
        }

        response = client.delete("/api/task/test-task-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        mock_cancel.assert_called_once_with("test-task-id")

    @patch("app.main.cancel_task")
    def test_cancel_task_failure(self, mock_cancel, client):
        """Test task cancellation failure."""
        mock_cancel.return_value = {
            "success": False,
            "error": "Task not found"
        }

        response = client.delete("/api/task/test-task-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
