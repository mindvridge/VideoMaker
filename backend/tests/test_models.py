"""
Test GPU Model Manager.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.models import GPUModelManager, ModelType


@pytest.mark.unit
class TestGPUModelManager:
    """Test GPU Model Manager."""

    @pytest.fixture
    def model_manager(self):
        """Create model manager instance."""
        return GPUModelManager()

    def test_initialization(self, model_manager):
        """Test model manager initialization."""
        assert model_manager.models == {}
        assert model_manager.device in ["cuda", "cpu"]
        assert model_manager.dtype is not None

    def test_clear_gpu_memory(self, model_manager):
        """Test GPU memory clearing."""
        # Should not raise any errors
        model_manager._clear_gpu_memory()

    def test_get_gpu_memory_usage(self, model_manager):
        """Test getting GPU memory usage."""
        usage = model_manager._get_gpu_memory_usage()

        assert isinstance(usage, dict)
        assert "allocated" in usage
        assert "reserved" in usage
        assert usage["allocated"] >= 0
        assert usage["reserved"] >= 0

    @patch("app.models.torch.cuda.is_available", return_value=False)
    def test_cpu_fallback(self, mock_cuda):
        """Test fallback to CPU when CUDA is not available."""
        manager = GPUModelManager()
        assert manager.device == "cpu"

    def test_unload_model(self, model_manager, mock_gpu_model):
        """Test unloading a model."""
        # Add a model
        model_manager.models["test-model"] = mock_gpu_model

        # Unload it
        model_manager.unload_model("test-model")

        assert "test-model" not in model_manager.models

    def test_unload_all_models(self, model_manager, mock_gpu_model):
        """Test unloading all models."""
        # Add multiple models
        model_manager.models["model1"] = mock_gpu_model
        model_manager.models["model2"] = mock_gpu_model

        # Unload all
        model_manager.unload_all_models()

        assert len(model_manager.models) == 0

    @patch("app.models.DiffusionPipeline.from_pretrained")
    def test_load_wan_model_caching(self, mock_from_pretrained, model_manager):
        """Test Wan model caching."""
        mock_pipeline = MagicMock()
        mock_from_pretrained.return_value = mock_pipeline

        # Load model first time
        model1 = model_manager.load_wan_model(ModelType.WAN_T2V)

        # Load same model again
        model2 = model_manager.load_wan_model(ModelType.WAN_T2V)

        # Should return cached model
        assert model1 is model2
        # Should only call from_pretrained once
        assert mock_from_pretrained.call_count == 1

    @patch("app.models.DiffusionPipeline.from_pretrained")
    def test_max_models_in_memory(self, mock_from_pretrained, model_manager):
        """Test maximum models in memory limit."""
        mock_pipeline = MagicMock()
        mock_from_pretrained.return_value = mock_pipeline

        # Load first model
        model_manager.load_wan_model(ModelType.WAN_T2V)
        assert len(model_manager.models) == 1

        # Load second model (should trigger unload if max is 1)
        with patch("app.models.settings.MAX_MODELS_IN_MEMORY", 1):
            model_manager.load_wan_model(ModelType.WAN_I2V)
            # After loading second model with max=1, only one should remain
            assert len(model_manager.models) <= 1


@pytest.mark.unit
class TestModelType:
    """Test ModelType enum."""

    def test_model_types_exist(self):
        """Test all expected model types exist."""
        assert ModelType.WAN_T2V == "wan-2.2-t2v"
        assert ModelType.WAN_I2V == "wan-2.2-i2v"
        assert ModelType.SKYREELS_T2V == "skyreels-v2-t2v"
        assert ModelType.SKYREELS_I2V == "skyreels-v2-i2v"
        assert ModelType.SKYREELS_DF == "skyreels-v2-df"
        assert ModelType.HUNYUAN_I2V_STABILITY == "hunyuan-i2v-stability"
        assert ModelType.HUNYUAN_I2V_DYNAMIC == "hunyuan-i2v-dynamic"

    def test_model_type_validation(self):
        """Test model type validation."""
        # Valid model type
        model_type = ModelType("wan-2.2-t2v")
        assert model_type == ModelType.WAN_T2V

        # Invalid model type
        with pytest.raises(ValueError):
            ModelType("invalid-model")
