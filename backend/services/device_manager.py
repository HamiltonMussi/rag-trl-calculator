"""Device management utilities for ML model deployment."""

import torch
import logging
from typing import Union

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages device selection and configuration for ML models."""
    
    _instance = None
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def device(self) -> torch.device:
        """Get the optimal device for model execution."""
        if self._device is None:
            self._device = self._detect_optimal_device()
        return self._device
    
    def _detect_optimal_device(self) -> torch.device:
        """Detect and return the optimal device for model execution."""
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            device = torch.device("mps")
            logger.info("Using MPS (Apple Silicon) device")
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Using CUDA device: {torch.cuda.get_device_name()}")
        else:
            device = torch.device("cpu")
            logger.info("Using CPU device")
        
        return device
    
    def get_pipeline_device_param(self) -> Union[str, int]:
        """Get device parameter formatted for HuggingFace pipeline."""
        device = self.device
        if device.type == 'mps':
            return str(device)
        elif device.type == 'cuda':
            return device.index if device.index is not None else 0
        else:
            return -1
    
    def move_model_to_device(self, model) -> None:
        """Move a model to the optimal device."""
        try:
            model.to(self.device)
            logger.info(f"Model moved to device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to move model to device {self.device}: {e}")
            raise


# Global instance for easy access
device_manager = DeviceManager()