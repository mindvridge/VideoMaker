"""
Test Celery worker configuration.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.celery
class TestWorkerConfiguration:
    """Test worker configuration."""

    def test_celery_app_creation(self):
        """Test Celery app is created properly."""
        from app.worker import celery_app

        assert celery_app is not None
        assert celery_app.main == "video_generation"

    def test_celery_broker_url(self):
        """Test Celery broker URL is set."""
        from app.worker import celery_app

        assert celery_app.conf.broker_url is not None
        assert "redis" in celery_app.conf.broker_url

    def test_celery_result_backend(self):
        """Test Celery result backend is set."""
        from app.worker import celery_app

        assert celery_app.conf.result_backend is not None

    def test_celery_serializer_settings(self):
        """Test Celery serializer settings."""
        from app.worker import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"

    def test_celery_worker_settings(self):
        """Test Celery worker settings."""
        from app.worker import celery_app

        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.worker_max_tasks_per_child == 10

    def test_celery_task_settings(self):
        """Test Celery task settings."""
        from app.worker import celery_app

        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True


@pytest.mark.celery
class TestVideoGenerationTaskClass:
    """Test VideoGenerationTask class."""

    def test_task_update_progress(self, mock_redis):
        """Test task progress update."""
        from app.tasks import VideoGenerationTask

        task = VideoGenerationTask()
        task.redis_client = mock_redis

        task.update_progress(
            task_id="test-123",
            progress=50,
            total=100,
            status="Generating",
            metadata={"step": 5}
        )

        # Check Redis was updated
        stored = mock_redis.get("task_progress:test-123")
        assert stored is not None

    def test_task_update_progress_calculates_percentage(self, mock_redis):
        """Test progress percentage calculation."""
        import json
        from app.tasks import VideoGenerationTask

        task = VideoGenerationTask()
        task.redis_client = mock_redis

        task.update_progress(
            task_id="test-123",
            progress=25,
            total=100,
            status="Processing"
        )

        stored = json.loads(mock_redis.get("task_progress:test-123"))
        assert stored["percentage"] == 25

    def test_task_update_progress_zero_total(self, mock_redis):
        """Test progress with zero total (edge case)."""
        import json
        from app.tasks import VideoGenerationTask

        task = VideoGenerationTask()
        task.redis_client = mock_redis

        task.update_progress(
            task_id="test-123",
            progress=0,
            total=0,  # Edge case
            status="Starting"
        )

        stored = json.loads(mock_redis.get("task_progress:test-123"))
        assert stored["percentage"] == 0


@pytest.mark.celery
class TestCleanupTask:
    """Test cleanup task."""

    @patch("app.tasks.Path")
    def test_cleanup_old_videos_success(self, mock_path):
        """Test successful cleanup of old videos."""
        from app.tasks import cleanup_old_videos
        import time

        # Mock file system
        mock_file = MagicMock()
        mock_file.stat.return_value.st_mtime = time.time() - (8 * 86400)  # 8 days old
        mock_file.stat.return_value.st_size = 1024 * 1024  # 1MB

        mock_path_instance = MagicMock()
        mock_path_instance.glob.return_value = [mock_file]
        mock_path.return_value = mock_path_instance

        result = cleanup_old_videos(days_old=7)

        assert result["success"] is True
        assert result["deleted_count"] >= 0

    @patch("app.tasks.Path")
    def test_cleanup_no_old_videos(self, mock_path):
        """Test cleanup when no old videos exist."""
        from app.tasks import cleanup_old_videos
        import time

        # Mock file system - recent file
        mock_file = MagicMock()
        mock_file.stat.return_value.st_mtime = time.time() - (1 * 86400)  # 1 day old
        mock_file.stat.return_value.st_size = 1024

        mock_path_instance = MagicMock()
        mock_path_instance.glob.return_value = [mock_file]
        mock_path.return_value = mock_path_instance

        result = cleanup_old_videos(days_old=7)

        assert result["success"] is True
        assert result["deleted_count"] == 0

    @patch("app.tasks.Path")
    def test_cleanup_failure(self, mock_path):
        """Test cleanup failure handling."""
        from app.tasks import cleanup_old_videos

        mock_path.side_effect = Exception("File system error")

        result = cleanup_old_videos(days_old=7)

        assert result["success"] is False
        assert "error" in result
