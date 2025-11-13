"""
Test Celery tasks.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.tasks import generate_video_task, get_task_progress, cancel_task
from app.models import ModelType


@pytest.mark.celery
class TestGenerateVideoTask:
    """Test video generation task."""

    @patch("app.tasks.model_manager.generate_video")
    @patch("app.tasks.video_storage.upload_video")
    def test_generate_video_task_success(self, mock_upload, mock_generate, temp_video_file):
        """Test successful video generation."""
        # Mock video generation
        mock_generate.return_value = temp_video_file

        # Mock S3 upload
        mock_upload.return_value = {
            "success": True,
            "s3_url": "https://s3.amazonaws.com/bucket/video.mp4",
            "cdn_url": "https://cdn.example.com/video.mp4",
            "presigned_url": "https://presigned.url",
            "object_key": "videos/test.mp4"
        }

        # Execute task
        result = generate_video_task(
            model_type="wan-2.2-t2v",
            prompt="Test prompt",
            num_frames=81,
            height=720,
            width=1280,
            fps=8,
            upload_to_s3=True
        )

        # Verify result
        assert result["success"] is True
        assert result["video_path"] == temp_video_file
        assert result["s3_url"] is not None
        assert result["presigned_url"] is not None

        # Verify model_manager was called
        mock_generate.assert_called_once()

        # Verify upload was called
        mock_upload.assert_called_once()

    @patch("app.tasks.model_manager.generate_video")
    def test_generate_video_task_without_upload(self, mock_generate, temp_video_file):
        """Test video generation without S3 upload."""
        mock_generate.return_value = temp_video_file

        result = generate_video_task(
            model_type="wan-2.2-t2v",
            prompt="Test prompt",
            upload_to_s3=False
        )

        assert result["success"] is True
        assert result["video_path"] == temp_video_file
        assert "s3_url" not in result

    @patch("app.tasks.model_manager.generate_video")
    def test_generate_video_task_failure(self, mock_generate):
        """Test video generation failure."""
        mock_generate.side_effect = Exception("Generation failed")

        with pytest.raises(Exception, match="Generation failed"):
            generate_video_task(
                model_type="wan-2.2-t2v",
                prompt="Test prompt"
            )

    def test_generate_video_invalid_model_type(self):
        """Test video generation with invalid model type."""
        with pytest.raises(ValueError):
            generate_video_task(
                model_type="invalid-model",
                prompt="Test prompt"
            )


@pytest.mark.celery
class TestTaskProgress:
    """Test task progress tracking."""

    @patch("app.tasks.redis_client")
    def test_get_task_progress_exists(self, mock_redis):
        """Test getting existing task progress."""
        import json

        mock_redis.get.return_value = json.dumps({
            "task_id": "test-123",
            "progress": 50,
            "total": 100,
            "percentage": 50,
            "status": "Generating frames"
        })

        progress = get_task_progress("test-123")

        assert progress is not None
        assert progress["task_id"] == "test-123"
        assert progress["percentage"] == 50
        assert progress["status"] == "Generating frames"

    @patch("app.tasks.redis_client")
    def test_get_task_progress_not_exists(self, mock_redis):
        """Test getting non-existent task progress."""
        mock_redis.get.return_value = None

        progress = get_task_progress("non-existent")

        assert progress is None

    @patch("app.tasks.redis_client")
    def test_get_task_progress_invalid_json(self, mock_redis):
        """Test getting task progress with invalid JSON."""
        mock_redis.get.return_value = "invalid json"

        progress = get_task_progress("test-123")

        assert progress is None


@pytest.mark.celery
class TestTaskCancellation:
    """Test task cancellation."""

    @patch("app.tasks.celery_app.control.revoke")
    @patch("app.tasks.redis_client")
    def test_cancel_task_success(self, mock_redis, mock_revoke):
        """Test successful task cancellation."""
        result = cancel_task("test-task-id")

        assert result["success"] is True
        assert "message" in result

        # Verify revoke was called
        mock_revoke.assert_called_once_with("test-task-id", terminate=True)

        # Verify Redis was updated
        mock_redis.setex.assert_called_once()

    @patch("app.tasks.celery_app.control.revoke")
    def test_cancel_task_failure(self, mock_revoke):
        """Test task cancellation failure."""
        mock_revoke.side_effect = Exception("Revoke failed")

        result = cancel_task("test-task-id")

        assert result["success"] is False
        assert "error" in result
