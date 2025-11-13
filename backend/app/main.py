"""
FastAPI main application.
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from celery.result import AsyncResult
from loguru import logger
import redis
import asyncio

from .config import get_settings
from .worker import celery_app
from .tasks import generate_video_task, get_task_progress, cancel_task
from .models import ModelType

settings = get_settings()

# Configure logger
logger.add(
    "logs/api_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Video Generation API with multiple model support"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client for SSE
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


# Pydantic models
class VideoGenerationRequest(BaseModel):
    """Request model for video generation."""
    model_type: str = Field(..., description="Model type to use")
    prompt: str = Field(..., description="Text prompt for generation")
    num_frames: int = Field(81, ge=1, le=300, description="Number of frames")
    height: int = Field(720, ge=256, le=1080, description="Video height")
    width: int = Field(1280, ge=256, le=1920, description="Video width")
    fps: int = Field(8, ge=1, le=30, description="Frames per second")
    num_inference_steps: int = Field(50, ge=10, le=100, description="Inference steps")
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0, description="Guidance scale")
    upload_to_s3: bool = Field(True, description="Upload result to S3")

    class Config:
        json_schema_extra = {
            "example": {
                "model_type": "wan-2.2-t2v",
                "prompt": "A beautiful sunset over the ocean with waves crashing",
                "num_frames": 81,
                "height": 720,
                "width": 1280,
                "fps": 8,
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
                "upload_to_s3": True
            }
        }


class TaskResponse(BaseModel):
    """Response model for task submission."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "supported_models": [model.value for model in ModelType]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_status = "disconnected"

    # Check Celery
    try:
        celery_inspect = celery_app.control.inspect()
        active_workers = celery_inspect.active()
        celery_status = "connected" if active_workers else "no workers"
    except Exception as e:
        logger.error(f"Celery health check failed: {str(e)}")
        celery_status = "disconnected"

    return {
        "status": "healthy" if redis_status == "connected" else "degraded",
        "redis": redis_status,
        "celery": celery_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/models")
async def list_models():
    """List supported models."""
    models = []
    for model in ModelType:
        models.append({
            "id": model.value,
            "name": model.value.upper(),
            "type": "T2V" if "t2v" in model.value else "I2V" if "i2v" in model.value else "DF"
        })

    return {"models": models}


@app.post("/api/generate", response_model=TaskResponse)
async def generate_video(request: VideoGenerationRequest):
    """
    Submit video generation task.

    This endpoint submits a video generation task to the Celery queue
    and returns a task ID for tracking progress.
    """
    try:
        # Validate model type
        try:
            ModelType(request.model_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type: {request.model_type}"
            )

        # Submit task to Celery
        task = generate_video_task.apply_async(
            kwargs={
                "model_type": request.model_type,
                "prompt": request.prompt,
                "num_frames": request.num_frames,
                "height": request.height,
                "width": request.width,
                "fps": request.fps,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
                "upload_to_s3": request.upload_to_s3
            }
        )

        logger.info(f"Video generation task submitted: {task.id}")

        return TaskResponse(
            task_id=task.id,
            status="submitted",
            message="Video generation task submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/i2v", response_model=TaskResponse)
async def generate_video_i2v(
    model_type: str = Form(...),
    prompt: str = Form(...),
    image: UploadFile = File(...),
    num_frames: int = Form(81),
    height: int = Form(720),
    width: int = Form(1280),
    fps: int = Form(8),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(7.5),
    upload_to_s3: bool = Form(True)
):
    """
    Submit image-to-video generation task.

    This endpoint accepts an image file and generates a video based on it.
    """
    try:
        # Validate model type
        try:
            ModelType(model_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type: {model_type}"
            )

        # Check if model supports I2V
        if "i2v" not in model_type.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_type} does not support image-to-video"
            )

        # Save uploaded image
        import tempfile
        import os
        from pathlib import Path

        suffix = Path(image.filename).suffix
        if suffix.lower() not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: {settings.ALLOWED_IMAGE_EXTENSIONS}"
            )

        temp_image = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=settings.OUTPUT_DIR
        )

        # Read and save image
        content = await image.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Max size: {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
            )

        temp_image.write(content)
        temp_image.close()

        logger.info(f"Image uploaded: {temp_image.name}")

        # Submit task to Celery
        task = generate_video_task.apply_async(
            kwargs={
                "model_type": model_type,
                "prompt": prompt,
                "image_path": temp_image.name,
                "num_frames": num_frames,
                "height": height,
                "width": width,
                "fps": fps,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "upload_to_s3": upload_to_s3
            }
        )

        logger.info(f"I2V generation task submitted: {task.id}")

        return TaskResponse(
            task_id=task.id,
            status="submitted",
            message="Image-to-video generation task submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit I2V task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get task status and progress."""
    try:
        # Get Celery task result
        task_result = AsyncResult(task_id, app=celery_app)

        # Get progress from Redis
        progress = get_task_progress(task_id)

        response = TaskStatusResponse(
            task_id=task_id,
            status=task_result.status.lower(),
            progress=progress
        )

        if task_result.successful():
            response.result = task_result.result
        elif task_result.failed():
            response.error = str(task_result.info)

        return response

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/{task_id}")
async def stream_progress(task_id: str):
    """Stream task progress using Server-Sent Events (SSE)."""
    async def event_generator():
        """Generate SSE events."""
        pubsub = redis_client.pubsub()
        channel = f"task_updates:{task_id}"
        pubsub.subscribe(channel)

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'status': 'connected'})}\n\n"

            # Listen for updates
            for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    yield f"data: {data}\n\n"

                    # Check if task is complete
                    progress_data = json.loads(data)
                    if progress_data.get('percentage', 0) >= 100:
                        break

                # Allow other tasks to run
                await asyncio.sleep(0.1)

        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.websocket("/ws/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()
    logger.info(f"WebSocket connection established for task: {task_id}")

    pubsub = redis_client.pubsub()
    channel = f"task_updates:{task_id}"
    pubsub.subscribe(channel)

    try:
        # Send initial connection message
        await websocket.send_json({"status": "connected", "task_id": task_id})

        # Listen for updates
        while True:
            message = pubsub.get_message()

            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                await websocket.send_json(data)

                # Close connection if task is complete
                if data.get('percentage', 0) >= 100:
                    logger.info(f"Task {task_id} complete, closing WebSocket")
                    break

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task: {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        await websocket.close()


@app.delete("/api/task/{task_id}")
async def cancel_task_endpoint(task_id: str):
    """Cancel a running task."""
    try:
        result = cancel_task(task_id)
        return result
    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
