"""
Celery tasks for video generation.
"""
import os
import json
from typing import Optional, Dict, Any
from celery import Task, current_task
from celery.signals import worker_init
from loguru import logger
import redis

from .worker import celery_app
from .models import model_manager, ModelType
from .storage import video_storage
from .config import get_settings

settings = get_settings()

# Redis client for progress updates
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


class VideoGenerationTask(Task):
    """Base task class for video generation with progress tracking."""

    def __init__(self):
        super().__init__()
        self.redis_client = redis_client

    def update_progress(
        self,
        task_id: str,
        progress: int,
        total: int,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update task progress in Redis.

        Args:
            task_id: Celery task ID
            progress: Current progress value
            total: Total progress value
            status: Status message
            metadata: Additional metadata
        """
        try:
            progress_data = {
                "task_id": task_id,
                "progress": progress,
                "total": total,
                "percentage": int((progress / total) * 100) if total > 0 else 0,
                "status": status,
                "metadata": metadata or {}
            }

            # Store in Redis with expiration
            key = f"task_progress:{task_id}"
            self.redis_client.setex(
                key,
                3600,  # Expire after 1 hour
                json.dumps(progress_data)
            )

            # Also publish to channel for real-time updates
            channel = f"task_updates:{task_id}"
            self.redis_client.publish(channel, json.dumps(progress_data))

            logger.debug(f"Progress update - Task {task_id}: {progress}/{total} - {status}")

        except Exception as e:
            logger.error(f"Failed to update progress: {str(e)}")

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} completed successfully")
        self.update_progress(task_id, 100, 100, "Completed", {"result": retval})

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {str(exc)}")
        self.update_progress(task_id, 0, 100, f"Failed: {str(exc)}", {"error": str(exc)})

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {task_id} is being retried: {str(exc)}")
        self.update_progress(task_id, 0, 100, f"Retrying: {str(exc)}")


@worker_init.connect
def init_worker(**kwargs):
    """Initialize worker - load models, check connections, etc."""
    logger.info("Initializing Celery worker...")

    # Check S3 connection
    try:
        if video_storage.check_bucket_exists():
            logger.info("S3 bucket is accessible")
        else:
            logger.warning("S3 bucket is not accessible - uploads may fail")
    except Exception as e:
        logger.error(f"Failed to check S3 bucket: {str(e)}")

    # Initialize model manager
    try:
        logger.info("GPU Model Manager initialized")
        logger.info(f"CUDA available: {model_manager.device}")
    except Exception as e:
        logger.error(f"Failed to initialize model manager: {str(e)}")

    logger.info("Worker initialization complete")


@celery_app.task(
    bind=True,
    base=VideoGenerationTask,
    name="tasks.generate_video",
    max_retries=3,
    soft_time_limit=3000,  # 50 minutes
    time_limit=3600  # 1 hour hard limit
)
def generate_video_task(
    self,
    model_type: str,
    prompt: str,
    image_path: Optional[str] = None,
    num_frames: int = 81,
    height: int = 720,
    width: int = 1280,
    fps: int = 8,
    num_inference_steps: int = 50,
    guidance_scale: float = 7.5,
    upload_to_s3: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate video using specified model.

    Args:
        model_type: Type of model to use (e.g., "wan-2.2-t2v")
        prompt: Text prompt for generation
        image_path: Path to input image (for I2V models)
        num_frames: Number of frames to generate
        height: Video height
        width: Video width
        fps: Frames per second
        num_inference_steps: Number of denoising steps
        guidance_scale: Guidance scale for generation
        upload_to_s3: Whether to upload result to S3
        **kwargs: Additional model-specific parameters

    Returns:
        Dictionary with generation results
    """
    task_id = self.request.id
    logger.info(f"Starting video generation task: {task_id}")
    logger.info(f"Model: {model_type}, Prompt: {prompt[:100]}...")

    try:
        # Validate model type
        try:
            model_enum = ModelType(model_type)
        except ValueError:
            raise ValueError(f"Invalid model type: {model_type}")

        # Update progress - Initializing
        self.update_progress(task_id, 0, 100, "Initializing video generation")

        # Define progress callback
        def progress_callback(progress: int, total: int, status: str):
            self.update_progress(task_id, progress, total, status)

        # Update progress - Loading model
        self.update_progress(task_id, 5, 100, f"Loading model: {model_type}")

        # Generate video
        logger.info("Starting video generation...")
        video_path = model_manager.generate_video(
            model_type=model_enum,
            prompt=prompt,
            image_path=image_path,
            num_frames=num_frames,
            height=height,
            width=width,
            fps=fps,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            progress_callback=progress_callback,
            **kwargs
        )

        logger.info(f"Video generated successfully: {video_path}")

        result = {
            "task_id": task_id,
            "success": True,
            "video_path": video_path,
            "model_type": model_type,
            "prompt": prompt,
            "params": {
                "num_frames": num_frames,
                "height": height,
                "width": width,
                "fps": fps,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale
            }
        }

        # Upload to S3 if requested
        if upload_to_s3:
            self.update_progress(task_id, 95, 100, "Uploading video to S3...")

            try:
                upload_result = video_storage.upload_video(
                    video_path,
                    optimize=True,
                    metadata={
                        "model_type": model_type,
                        "prompt": prompt[:200],
                        "task_id": task_id
                    }
                )

                if upload_result["success"]:
                    result["s3_url"] = upload_result["s3_url"]
                    result["cdn_url"] = upload_result["cdn_url"]
                    result["presigned_url"] = upload_result["presigned_url"]
                    result["object_key"] = upload_result["object_key"]
                    logger.info(f"Video uploaded to S3: {upload_result['object_key']}")

                    # Clean up local file after successful upload
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        logger.debug(f"Cleaned up local file: {video_path}")
                else:
                    logger.error(f"S3 upload failed: {upload_result.get('error')}")
                    result["upload_error"] = upload_result.get("error")

            except Exception as e:
                logger.error(f"Failed to upload to S3: {str(e)}")
                result["upload_error"] = str(e)

        self.update_progress(task_id, 100, 100, "Video generation complete", result)
        return result

    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}", exc_info=True)
        self.update_progress(task_id, 0, 100, f"Failed: {str(e)}")
        raise


@celery_app.task(name="tasks.get_task_progress")
def get_task_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get task progress from Redis.

    Args:
        task_id: Celery task ID

    Returns:
        Progress data dictionary or None
    """
    try:
        key = f"task_progress:{task_id}"
        data = redis_client.get(key)

        if data:
            return json.loads(data)
        return None

    except Exception as e:
        logger.error(f"Failed to get task progress: {str(e)}")
        return None


@celery_app.task(name="tasks.cancel_task")
def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    Cancel a running task.

    Args:
        task_id: Celery task ID

    Returns:
        Cancellation result
    """
    try:
        # Revoke task
        celery_app.control.revoke(task_id, terminate=True)

        # Update progress
        redis_client.setex(
            f"task_progress:{task_id}",
            3600,
            json.dumps({
                "task_id": task_id,
                "progress": 0,
                "total": 100,
                "percentage": 0,
                "status": "Cancelled",
                "metadata": {}
            })
        )

        logger.info(f"Task {task_id} cancelled")
        return {"success": True, "message": "Task cancelled"}

    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="tasks.cleanup_old_videos")
def cleanup_old_videos(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old videos from local storage.

    Args:
        days_old: Delete files older than this many days

    Returns:
        Cleanup result
    """
    import time
    from pathlib import Path

    try:
        output_dir = Path(settings.OUTPUT_DIR)
        current_time = time.time()
        deleted_count = 0
        deleted_size = 0

        for file_path in output_dir.glob("*.mp4"):
            file_age_days = (current_time - file_path.stat().st_mtime) / (86400)

            if file_age_days > days_old:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                deleted_size += file_size
                logger.debug(f"Deleted old video: {file_path}")

        deleted_size_mb = deleted_size / (1024 * 1024)
        logger.info(
            f"Cleanup complete - Deleted {deleted_count} files, "
            f"freed {deleted_size_mb:.2f}MB"
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "deleted_size_mb": deleted_size_mb
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {"success": False, "error": str(e)}
