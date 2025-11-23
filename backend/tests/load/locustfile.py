"""
Load testing with Locust for the Video Generation API.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Or with web UI:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import json
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample prompts for testing
SAMPLE_PROMPTS = [
    "A beautiful sunset over the ocean with waves crashing on the shore",
    "A cat playing with a ball of yarn in a cozy living room",
    "A futuristic city with flying cars and neon lights",
    "A serene mountain landscape with snow-capped peaks",
    "A colorful coral reef with tropical fish swimming around",
    "A thunderstorm over a wheat field with lightning",
    "A cozy coffee shop on a rainy day",
    "An astronaut floating in space with Earth in the background",
    "A vintage train traveling through autumn forest",
    "A magical forest with glowing mushrooms and fireflies",
]

# Model types for testing
MODEL_TYPES = [
    "wan-2.2-t2v",
    "skyreels-v2-t2v",
]


class VideoGenUser(HttpUser):
    """Simulated user for video generation API."""

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    def on_start(self):
        """Called when a simulated user starts."""
        logger.info("User started")
        # Could add authentication here if needed

    @task(10)
    def health_check(self):
        """Check API health - high frequency task."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["healthy", "degraded"]:
                    response.success()
                else:
                    response.failure(f"Unexpected health status: {data.get('status')}")
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(5)
    def get_root(self):
        """Get root endpoint - medium frequency."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Root endpoint failed: {response.status_code}")

    @task(5)
    def list_models(self):
        """List available models - medium frequency."""
        with self.client.get("/models", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "models" in data and len(data["models"]) > 0:
                    response.success()
                else:
                    response.failure("No models returned")
            else:
                response.failure(f"List models failed: {response.status_code}")

    @task(2)
    def submit_video_generation(self):
        """Submit video generation task - low frequency (expensive operation)."""
        payload = {
            "model_type": random.choice(MODEL_TYPES),
            "prompt": random.choice(SAMPLE_PROMPTS),
            "num_frames": random.choice([41, 61, 81]),
            "height": 480,  # Use lower resolution for load testing
            "width": 640,
            "fps": 8,
            "num_inference_steps": 20,  # Lower steps for faster testing
            "guidance_scale": 7.5,
            "upload_to_s3": False  # Don't upload during load testing
        }

        with self.client.post(
            "/api/generate",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "task_id" in data:
                    response.success()
                    # Store task_id for potential status checks
                    self.last_task_id = data["task_id"]
                else:
                    response.failure("No task_id in response")
            elif response.status_code == 429:
                # Rate limited - expected behavior
                response.success()
                logger.info("Rate limited (expected)")
            else:
                response.failure(f"Generation submit failed: {response.status_code}")

    @task(3)
    def check_task_status(self):
        """Check task status - medium frequency."""
        # Use a dummy task ID or the last submitted one
        task_id = getattr(self, 'last_task_id', 'test-task-id')

        with self.client.get(
            f"/api/status/{task_id}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                # Task not found is acceptable
                response.success()


class QuickUser(HttpUser):
    """User that only performs quick, read-only operations."""

    wait_time = between(0.5, 2)

    @task(5)
    def health_check(self):
        """Quick health check."""
        self.client.get("/health")

    @task(3)
    def list_models(self):
        """List models."""
        self.client.get("/models")

    @task(2)
    def root(self):
        """Get root."""
        self.client.get("/")


class StressTestUser(HttpUser):
    """User for stress testing - aggressive requests."""

    wait_time = between(0.1, 0.5)

    @task
    def rapid_health_checks(self):
        """Rapid fire health checks."""
        self.client.get("/health")

    @task
    def rapid_model_list(self):
        """Rapid fire model listing."""
        self.client.get("/models")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request details for debugging."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    logger.info("Load test starting...")
    if isinstance(environment.runner, MasterRunner):
        logger.info("Running in distributed mode")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    logger.info("Load test completed")

    # Print summary statistics
    stats = environment.runner.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"Requests per second: {stats.total.current_rps:.2f}")
