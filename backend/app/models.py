"""
GPU Model Manager for handling multiple video generation models.
"""
import gc
import torch
from typing import Dict, Optional, Any, Callable
from enum import Enum
from loguru import logger
from diffusers import DiffusionPipeline
from .config import get_settings

settings = get_settings()


class ModelType(str, Enum):
    """Supported video generation models."""
    WAN_T2V = "wan-2.2-t2v"
    WAN_I2V = "wan-2.2-i2v"
    SKYREELS_T2V = "skyreels-v2-t2v"
    SKYREELS_I2V = "skyreels-v2-i2v"
    SKYREELS_DF = "skyreels-v2-df"
    HUNYUAN_I2V_STABILITY = "hunyuan-i2v-stability"
    HUNYUAN_I2V_DYNAMIC = "hunyuan-i2v-dynamic"


class GPUModelManager:
    """
    Manages GPU models for video generation.
    Handles loading, unloading, and memory optimization.
    """

    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if settings.USE_BF16 else (
            torch.float16 if settings.USE_FP16 else torch.float32
        )
        logger.info(f"Initialized GPUModelManager with device: {self.device}, dtype: {self.dtype}")

    def _clear_gpu_memory(self):
        """Clear GPU memory cache."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
        logger.info("GPU memory cleared")

    def _get_gpu_memory_usage(self) -> Dict[str, float]:
        """Get current GPU memory usage in GB."""
        if not torch.cuda.is_available():
            return {"allocated": 0, "reserved": 0}

        return {
            "allocated": torch.cuda.memory_allocated() / 1024**3,
            "reserved": torch.cuda.memory_reserved() / 1024**3
        }

    def unload_model(self, model_type: str):
        """Unload a model from memory."""
        if model_type in self.models:
            logger.info(f"Unloading model: {model_type}")
            del self.models[model_type]
            self._clear_gpu_memory()

    def unload_all_models(self):
        """Unload all models from memory."""
        logger.info("Unloading all models")
        self.models.clear()
        self._clear_gpu_memory()

    def load_wan_model(self, model_type: ModelType) -> DiffusionPipeline:
        """Load Wan 2.2 model (T2V or I2V)."""
        model_key = model_type.value

        if model_key in self.models:
            logger.info(f"Model {model_key} already loaded")
            return self.models[model_key]

        # Manage memory by unloading other models if necessary
        if len(self.models) >= settings.MAX_MODELS_IN_MEMORY:
            self.unload_all_models()

        logger.info(f"Loading Wan 2.2 model: {model_key}")

        try:
            # Example: Load from Hugging Face
            # Adjust the model ID based on actual availability
            model_id = "ali-vilab/wan-2.2" if model_type == ModelType.WAN_T2V else "ali-vilab/wan-2.2-i2v"

            pipeline = DiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
                cache_dir=settings.MODELS_CACHE_DIR,
                variant="fp16" if settings.USE_FP16 else None
            )

            if settings.ENABLE_CPU_OFFLOAD:
                pipeline.enable_model_cpu_offload()
            else:
                pipeline.to(self.device)

            # Enable memory optimizations
            pipeline.enable_attention_slicing()
            pipeline.enable_vae_slicing()

            self.models[model_key] = pipeline
            logger.info(f"Successfully loaded {model_key}")
            logger.info(f"GPU Memory: {self._get_gpu_memory_usage()}")

            return pipeline

        except Exception as e:
            logger.error(f"Failed to load {model_key}: {str(e)}")
            raise

    def load_skyreels_model(self, model_type: ModelType):
        """
        Load SkyReels V2 model.
        Note: This is a placeholder. Actual implementation depends on SkyReels API.
        """
        model_key = model_type.value

        if model_key in self.models:
            logger.info(f"Model {model_key} already loaded")
            return self.models[model_key]

        if len(self.models) >= settings.MAX_MODELS_IN_MEMORY:
            self.unload_all_models()

        logger.info(f"Loading SkyReels model: {model_key}")

        try:
            # Placeholder for SkyReels model loading
            # You would integrate the actual SkyReels Python API here
            # from skyreels import SkyReelsModel
            # model = SkyReelsModel(model_type=model_type, device=self.device)

            # For now, we'll use a placeholder
            model = {
                "type": model_key,
                "device": self.device,
                "loaded": True
            }

            self.models[model_key] = model
            logger.info(f"Successfully loaded {model_key}")

            return model

        except Exception as e:
            logger.error(f"Failed to load {model_key}: {str(e)}")
            raise

    def load_hunyuan_model(self, model_type: ModelType):
        """
        Load HunyuanVideo I2V model.
        Note: This is a placeholder. Actual implementation depends on Hunyuan API.
        """
        model_key = model_type.value

        if model_key in self.models:
            logger.info(f"Model {model_key} already loaded")
            return self.models[model_key]

        if len(self.models) >= settings.MAX_MODELS_IN_MEMORY:
            self.unload_all_models()

        logger.info(f"Loading Hunyuan model: {model_key}")

        try:
            # Placeholder for Hunyuan model loading
            # You would integrate the actual Hunyuan PyTorch implementation here
            # from hunyuan import HunyuanI2V
            # mode = "stability" if model_type == ModelType.HUNYUAN_I2V_STABILITY else "dynamic"
            # model = HunyuanI2V(mode=mode, device=self.device)

            # For now, we'll use a placeholder
            model = {
                "type": model_key,
                "mode": "stability" if model_type == ModelType.HUNYUAN_I2V_STABILITY else "dynamic",
                "device": self.device,
                "loaded": True
            }

            self.models[model_key] = model
            logger.info(f"Successfully loaded {model_key}")

            return model

        except Exception as e:
            logger.error(f"Failed to load {model_key}: {str(e)}")
            raise

    def load_model(self, model_type: ModelType) -> Any:
        """Load a model based on its type."""
        logger.info(f"Loading model: {model_type.value}")

        if model_type in [ModelType.WAN_T2V, ModelType.WAN_I2V]:
            return self.load_wan_model(model_type)
        elif model_type in [ModelType.SKYREELS_T2V, ModelType.SKYREELS_I2V, ModelType.SKYREELS_DF]:
            return self.load_skyreels_model(model_type)
        elif model_type in [ModelType.HUNYUAN_I2V_STABILITY, ModelType.HUNYUAN_I2V_DYNAMIC]:
            return self.load_hunyuan_model(model_type)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def generate_video(
        self,
        model_type: ModelType,
        prompt: str,
        image_path: Optional[str] = None,
        num_frames: int = 81,
        height: int = 720,
        width: int = 1280,
        fps: int = 8,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        **kwargs
    ) -> str:
        """
        Generate video using the specified model.

        Args:
            model_type: Type of model to use
            prompt: Text prompt for generation
            image_path: Path to input image (for I2V models)
            num_frames: Number of frames to generate
            height: Video height
            width: Video width
            fps: Frames per second
            num_inference_steps: Number of denoising steps
            guidance_scale: Guidance scale for generation
            progress_callback: Optional callback for progress updates
            **kwargs: Additional model-specific parameters

        Returns:
            Path to generated video file
        """
        model = self.load_model(model_type)

        if progress_callback:
            progress_callback(0, 100, "Starting video generation")

        try:
            if model_type in [ModelType.WAN_T2V, ModelType.WAN_I2V]:
                return self._generate_wan_video(
                    model, model_type, prompt, image_path, num_frames,
                    height, width, fps, num_inference_steps, guidance_scale,
                    progress_callback, **kwargs
                )
            elif model_type in [ModelType.SKYREELS_T2V, ModelType.SKYREELS_I2V, ModelType.SKYREELS_DF]:
                return self._generate_skyreels_video(
                    model, model_type, prompt, image_path, num_frames,
                    height, width, fps, progress_callback, **kwargs
                )
            elif model_type in [ModelType.HUNYUAN_I2V_STABILITY, ModelType.HUNYUAN_I2V_DYNAMIC]:
                return self._generate_hunyuan_video(
                    model, model_type, prompt, image_path, num_frames,
                    height, width, fps, progress_callback, **kwargs
                )
            else:
                raise ValueError(f"Unknown model type: {model_type}")

        except Exception as e:
            logger.error(f"Video generation failed: {str(e)}")
            raise

    def _generate_wan_video(
        self, model, model_type, prompt, image_path, num_frames,
        height, width, fps, num_inference_steps, guidance_scale,
        progress_callback, **kwargs
    ) -> str:
        """Generate video using Wan 2.2 model."""
        import tempfile
        from PIL import Image

        logger.info(f"Generating video with Wan 2.2: {model_type.value}")

        # Define progress callback for the pipeline
        def diffusers_callback(step: int, timestep: int, latents):
            if progress_callback:
                progress = int((step / num_inference_steps) * 100)
                progress_callback(progress, 100, f"Generating frames: {step}/{num_inference_steps}")

        try:
            # Prepare inputs
            if model_type == ModelType.WAN_I2V and image_path:
                image = Image.open(image_path).convert("RGB")
                image = image.resize((width, height))
                output = model(
                    prompt=prompt,
                    image=image,
                    num_frames=num_frames,
                    height=height,
                    width=width,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    callback=diffusers_callback,
                    callback_steps=1,
                    **kwargs
                )
            else:
                output = model(
                    prompt=prompt,
                    num_frames=num_frames,
                    height=height,
                    width=width,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    callback=diffusers_callback,
                    callback_steps=1,
                    **kwargs
                )

            # Save video
            output_path = tempfile.mktemp(suffix=".mp4", dir=settings.OUTPUT_DIR)
            frames = output.frames[0]

            # Export to video using imageio
            import imageio
            writer = imageio.get_writer(output_path, fps=fps)
            for frame in frames:
                writer.append_data(frame)
            writer.close()

            if progress_callback:
                progress_callback(100, 100, "Video generation complete")

            logger.info(f"Video saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Wan video generation failed: {str(e)}")
            raise

    def _generate_skyreels_video(
        self, model, model_type, prompt, image_path, num_frames,
        height, width, fps, progress_callback, **kwargs
    ) -> str:
        """Generate video using SkyReels V2 model."""
        import tempfile

        logger.info(f"Generating video with SkyReels: {model_type.value}")

        # Placeholder for actual SkyReels implementation
        # This would call the actual SkyReels API

        output_path = tempfile.mktemp(suffix=".mp4", dir=settings.OUTPUT_DIR)

        if progress_callback:
            progress_callback(100, 100, "Video generation complete")

        logger.info(f"Video saved to: {output_path}")
        return output_path

    def _generate_hunyuan_video(
        self, model, model_type, prompt, image_path, num_frames,
        height, width, fps, progress_callback, **kwargs
    ) -> str:
        """Generate video using Hunyuan I2V model."""
        import tempfile

        logger.info(f"Generating video with Hunyuan: {model_type.value}")

        # Placeholder for actual Hunyuan implementation
        # This would call the actual Hunyuan PyTorch implementation

        output_path = tempfile.mktemp(suffix=".mp4", dir=settings.OUTPUT_DIR)

        if progress_callback:
            progress_callback(100, 100, "Video generation complete")

        logger.info(f"Video saved to: {output_path}")
        return output_path


# Global model manager instance
model_manager = GPUModelManager()
