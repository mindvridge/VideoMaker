"""
Test video storage and S3 integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.storage import VideoStorage


@pytest.mark.unit
class TestVideoStorage:
    """Test VideoStorage class."""

    @pytest.fixture
    def storage(self, mock_s3):
        """Create VideoStorage instance with mocked S3."""
        with patch("app.storage.boto3.client", return_value=mock_s3):
            return VideoStorage()

    def test_initialization(self, storage):
        """Test storage initialization."""
        assert storage.s3_client is not None
        assert storage.bucket_name == "test-bucket"

    def test_check_bucket_exists(self, storage, mock_s3):
        """Test checking if bucket exists."""
        result = storage.check_bucket_exists()
        assert result is True

    def test_check_bucket_not_exists(self, storage):
        """Test checking non-existent bucket."""
        storage.bucket_name = "non-existent-bucket"
        result = storage.check_bucket_exists()
        assert result is False

    @patch("app.storage.subprocess.run")
    def test_optimize_video_with_ffmpeg(self, mock_run, storage, temp_video_file):
        """Test video optimization with FFmpeg."""
        # Mock successful FFmpeg execution
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="FFmpeg output"
        )

        output_path = storage.optimize_video_with_ffmpeg(temp_video_file)

        assert output_path.endswith("_optimized.mp4")
        mock_run.assert_called_once()

        # Check FFmpeg command
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert temp_video_file in cmd

    @patch("app.storage.subprocess.run")
    def test_optimize_video_ffmpeg_failure(self, mock_run, storage, temp_video_file):
        """Test FFmpeg failure returns original file."""
        # Mock FFmpeg failure
        mock_run.side_effect = Exception("FFmpeg failed")

        output_path = storage.optimize_video_with_ffmpeg(temp_video_file)

        # Should return original path on failure
        assert output_path == temp_video_file

    def test_upload_video_success(self, storage, temp_video_file):
        """Test successful video upload to S3."""
        with patch.object(storage, 'optimize_video_with_ffmpeg', return_value=temp_video_file):
            result = storage.upload_video(
                temp_video_file,
                optimize=False,
                metadata={"test": "metadata"}
            )

        assert result["success"] is True
        assert "object_key" in result
        assert "s3_url" in result
        assert "presigned_url" in result
        assert result["bucket"] == "test-bucket"

    def test_upload_video_with_optimization(self, storage, temp_video_file):
        """Test video upload with optimization."""
        with patch.object(storage, 'optimize_video_with_ffmpeg', return_value=temp_video_file):
            result = storage.upload_video(
                temp_video_file,
                optimize=True
            )

        assert result["success"] is True

    def test_generate_presigned_url(self, storage):
        """Test presigned URL generation."""
        object_key = "videos/test_video.mp4"

        url = storage.generate_presigned_url(object_key, expiration=3600)

        assert url is not None
        assert isinstance(url, str)
        assert "test-bucket" in url

    def test_delete_video(self, storage, mock_s3):
        """Test video deletion from S3."""
        object_key = "videos/test_video.mp4"

        # Upload a test file first
        mock_s3.put_object(
            Bucket="test-bucket",
            Key=object_key,
            Body=b"test content"
        )

        # Delete it
        result = storage.delete_video(object_key)

        assert result is True

        # Verify it's deleted
        try:
            mock_s3.head_object(Bucket="test-bucket", Key=object_key)
            assert False, "Object should be deleted"
        except:
            pass  # Expected

    def test_list_videos(self, storage, mock_s3):
        """Test listing videos from S3."""
        # Upload some test videos
        for i in range(3):
            mock_s3.put_object(
                Bucket="test-bucket",
                Key=f"videos/test_{i}.mp4",
                Body=b"test content"
            )

        videos = storage.list_videos(prefix="videos/", max_keys=10)

        assert len(videos) == 3
        assert all("key" in v for v in videos)
        assert all("size" in v for v in videos)
        assert all("last_modified" in v for v in videos)
        assert all("url" in v for v in videos)

    def test_list_videos_empty(self, storage):
        """Test listing videos when bucket is empty."""
        videos = storage.list_videos(prefix="videos/")

        assert videos == []

    def test_upload_video_custom_key(self, storage, temp_video_file):
        """Test video upload with custom object key."""
        custom_key = "custom/path/my_video.mp4"

        with patch.object(storage, 'optimize_video_with_ffmpeg', return_value=temp_video_file):
            result = storage.upload_video(
                temp_video_file,
                object_key=custom_key,
                optimize=False
            )

        assert result["success"] is True
        assert result["object_key"] == custom_key

    def test_cloudfront_url_generation(self, storage, temp_video_file):
        """Test CloudFront URL generation when domain is configured."""
        storage.cloudfront_domain = "test-cdn.cloudfront.net"

        with patch.object(storage, 'optimize_video_with_ffmpeg', return_value=temp_video_file):
            result = storage.upload_video(
                temp_video_file,
                optimize=False
            )

        assert result["success"] is True
        assert result["cdn_url"] is not None
        assert "test-cdn.cloudfront.net" in result["cdn_url"]


@pytest.mark.integration
class TestVideoStorageIntegration:
    """Integration tests for video storage."""

    @pytest.fixture
    def storage_with_real_s3(self, mock_s3):
        """Create storage with mocked S3 for integration tests."""
        with patch("app.storage.boto3.client", return_value=mock_s3):
            return VideoStorage()

    def test_full_upload_flow(self, storage_with_real_s3, temp_video_file):
        """Test complete upload flow."""
        storage = storage_with_real_s3

        # Upload
        with patch.object(storage, 'optimize_video_with_ffmpeg', return_value=temp_video_file):
            upload_result = storage.upload_video(
                temp_video_file,
                optimize=False,
                metadata={"source": "test"}
            )

        assert upload_result["success"] is True
        object_key = upload_result["object_key"]

        # List and verify
        videos = storage.list_videos()
        assert len(videos) > 0
        assert any(v["key"] == object_key for v in videos)

        # Generate presigned URL
        url = storage.generate_presigned_url(object_key)
        assert url is not None

        # Delete
        delete_result = storage.delete_video(object_key)
        assert delete_result is True
