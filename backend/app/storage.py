"""
AWS S3 Storage Manager for video uploads and CDN distribution.
"""
import os
import subprocess
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from .config import get_settings

settings = get_settings()


class VideoStorage:
    """
    Manages video storage on AWS S3 with CloudFront CDN.
    Handles uploads, FFmpeg optimization, and presigned URL generation.
    """

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.cloudfront_domain = settings.CLOUDFRONT_DOMAIN

        logger.info(f"Initialized VideoStorage with bucket: {self.bucket_name}")

    def optimize_video_with_ffmpeg(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = "medium",
        crf: int = 23,
        scale: Optional[str] = None
    ) -> str:
        """
        Optimize video using FFmpeg.

        Args:
            input_path: Path to input video
            output_path: Path to output video (optional)
            preset: FFmpeg preset (ultrafast, fast, medium, slow, veryslow)
            crf: Constant Rate Factor (0-51, lower is better quality)
            scale: Scale filter (e.g., "1280:720", "-2:720")

        Returns:
            Path to optimized video
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_optimized{ext}"

        logger.info(f"Optimizing video with FFmpeg: {input_path}")

        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", settings.FFMPEG_VIDEO_CODEC,
            "-preset", preset,
            "-crf", str(crf),
            "-movflags", "+faststart",  # Enable streaming
            "-pix_fmt", "yuv420p",  # Compatibility
        ]

        # Add scale filter if specified
        if scale:
            cmd.extend(["-vf", f"scale={scale}"])

        # Add audio codec if audio exists
        cmd.extend([
            "-c:a", settings.FFMPEG_AUDIO_CODEC,
            "-b:a", "128k",
            "-y",  # Overwrite output file
            output_path
        ])

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Video optimized successfully: {output_path}")
            logger.debug(f"FFmpeg output: {result.stderr}")

            # Get file sizes
            input_size = os.path.getsize(input_path) / (1024 * 1024)
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            compression_ratio = (1 - output_size / input_size) * 100

            logger.info(
                f"Optimization results - "
                f"Input: {input_size:.2f}MB, "
                f"Output: {output_size:.2f}MB, "
                f"Compression: {compression_ratio:.1f}%"
            )

            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg optimization failed: {e.stderr}")
            # Return original path if optimization fails
            return input_path

        except Exception as e:
            logger.error(f"Video optimization failed: {str(e)}")
            return input_path

    def upload_video(
        self,
        file_path: str,
        object_key: Optional[str] = None,
        optimize: bool = True,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Upload video to S3.

        Args:
            file_path: Path to video file
            object_key: S3 object key (optional, will be auto-generated)
            optimize: Whether to optimize video with FFmpeg before upload
            metadata: Optional metadata to attach to S3 object

        Returns:
            Dictionary with upload information
        """
        try:
            # Optimize video if requested
            upload_path = file_path
            if optimize:
                logger.info("Optimizing video before upload...")
                upload_path = self.optimize_video_with_ffmpeg(
                    file_path,
                    preset=settings.FFMPEG_PRESET,
                    crf=settings.FFMPEG_CRF
                )

            # Generate object key if not provided
            if object_key is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = Path(upload_path).name
                object_key = f"videos/{timestamp}_{filename}"

            # Prepare metadata
            extra_args = {
                'ContentType': 'video/mp4',
                'CacheControl': 'max-age=31536000',  # Cache for 1 year
            }
            if metadata:
                extra_args['Metadata'] = metadata

            # Upload to S3
            logger.info(f"Uploading video to S3: {object_key}")
            file_size = os.path.getsize(upload_path) / (1024 * 1024)
            logger.info(f"File size: {file_size:.2f}MB")

            self.s3_client.upload_file(
                upload_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )

            # Generate URLs
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_key}"
            cdn_url = None

            if self.cloudfront_domain:
                cdn_url = f"https://{self.cloudfront_domain}/{object_key}"

            # Generate presigned URL
            presigned_url = self.generate_presigned_url(object_key)

            logger.info(f"Video uploaded successfully to S3: {object_key}")

            # Clean up optimized file if different from original
            if upload_path != file_path and os.path.exists(upload_path):
                os.remove(upload_path)
                logger.debug(f"Cleaned up optimized file: {upload_path}")

            return {
                "success": True,
                "object_key": object_key,
                "s3_url": s3_url,
                "cdn_url": cdn_url,
                "presigned_url": presigned_url,
                "file_size_mb": file_size,
                "bucket": self.bucket_name
            }

        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None
    ) -> str:
        """
        Generate a presigned URL for downloading the video.

        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        if expiration is None:
            expiration = settings.PRESIGNED_URL_EXPIRATION

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for: {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise

    def delete_video(self, object_key: str) -> bool:
        """
        Delete video from S3.

        Args:
            object_key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"Deleted video from S3: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete video: {str(e)}")
            return False

    def check_bucket_exists(self) -> bool:
        """Check if the S3 bucket exists and is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' is accessible")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error(f"Error accessing S3 bucket: {str(e)}")
            return False

    def list_videos(self, prefix: str = "videos/", max_keys: int = 100) -> list:
        """
        List videos in S3 bucket.

        Args:
            prefix: S3 key prefix to filter by
            max_keys: Maximum number of keys to return

        Returns:
            List of video objects
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            videos = []
            for obj in response['Contents']:
                videos.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'url': self.generate_presigned_url(obj['Key'])
                })

            logger.info(f"Found {len(videos)} videos with prefix: {prefix}")
            return videos

        except ClientError as e:
            logger.error(f"Failed to list videos: {str(e)}")
            return []


# Global storage instance
video_storage = VideoStorage()
