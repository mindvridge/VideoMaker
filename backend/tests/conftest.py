"""
Pytest configuration and fixtures.
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import fakeredis
from moto import mock_s3
import boto3

# Set test environment
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"


@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI application."""
    from app.main import app
    return app


@pytest.fixture(scope="function")
def client(test_app):
    """Create test client."""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def mock_redis():
    """Create mock Redis client."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    yield fake_redis
    fake_redis.flushall()


@pytest.fixture(scope="function")
def mock_celery_task():
    """Mock Celery task."""
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    mock_task.status = "PENDING"
    mock_task.result = None
    return mock_task


@pytest.fixture(scope="function")
def mock_s3():
    """Mock S3 client."""
    with mock_s3():
        # Create mock S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            region_name='us-east-1'
        )

        # Create test bucket
        s3_client.create_bucket(Bucket='test-bucket')

        yield s3_client


@pytest.fixture(scope="function")
def mock_gpu_model():
    """Mock GPU model."""
    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_model.dtype = "float32"
    return mock_model


@pytest.fixture(scope="function")
def sample_video_request():
    """Sample video generation request."""
    return {
        "model_type": "wan-2.2-t2v",
        "prompt": "A beautiful sunset over the ocean",
        "num_frames": 81,
        "height": 720,
        "width": 1280,
        "fps": 8,
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
        "upload_to_s3": False
    }


@pytest.fixture(scope="function")
def sample_task_result():
    """Sample task result."""
    return {
        "task_id": "test-task-id-123",
        "success": True,
        "video_path": "/tmp/test_video.mp4",
        "model_type": "wan-2.2-t2v",
        "prompt": "A beautiful sunset over the ocean",
        "params": {
            "num_frames": 81,
            "height": 720,
            "width": 1280,
            "fps": 8
        }
    }


@pytest.fixture(autouse=True)
def mock_model_loading(monkeypatch):
    """Automatically mock heavy model loading in all tests."""
    def mock_load(*args, **kwargs):
        return MagicMock()

    # Mock model loading to avoid loading actual models
    monkeypatch.setattr(
        "app.models.DiffusionPipeline.from_pretrained",
        mock_load
    )


@pytest.fixture(scope="function")
def temp_video_file(tmp_path):
    """Create temporary video file for testing."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return str(video_file)


@pytest.fixture(scope="function")
def temp_image_file(tmp_path):
    """Create temporary image file for testing."""
    from PIL import Image
    import io

    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    image_file = tmp_path / "test_image.jpg"
    image_file.write_bytes(img_bytes.read())
    return str(image_file)
