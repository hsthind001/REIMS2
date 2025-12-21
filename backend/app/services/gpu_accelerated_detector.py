"""
GPU-Accelerated Anomaly Detector

Provides GPU acceleration for PyOD models and other ML operations.
Falls back gracefully to CPU if GPU is not available.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)

# Try to import GPU dependencies
try:
    import torch
    import cupy as cp
    GPU_AVAILABLE = torch.cuda.is_available()
    GPU_DEVICE = "cuda" if GPU_AVAILABLE else "cpu"
    if GPU_AVAILABLE:
        logger.info(f"GPU acceleration available: {torch.cuda.get_device_name(0)}")
    else:
        logger.info("GPU not available, using CPU")
except ImportError as e:
    GPU_AVAILABLE = False
    GPU_DEVICE = "cpu"
    logger.warning(f"GPU dependencies not available: {e}")


class GPUAcceleratedDetector:
    """
    GPU-accelerated anomaly detection.

    Features:
    - Automatic GPU/CPU selection
    - Batch processing on GPU
    - Memory management
    - Graceful fallback to CPU
    """

    def __init__(self, db: Session):
        self.db = db
        self.flags = FeatureFlags()
        self.device = self._get_device()
        self.use_gpu = self._should_use_gpu()

    def _get_device(self) -> str:
        """Determine device (CPU/GPU) for computations."""
        if not GPU_AVAILABLE:
            return "cpu"

        if settings.ANOMALY_USE_GPU and self.flags.is_gpu_acceleration_enabled():
            return GPU_DEVICE
        return "cpu"

    def _should_use_gpu(self) -> bool:
        """Check if GPU should be used."""
        return (
            GPU_AVAILABLE and
            self.device == "cuda" and
            settings.ANOMALY_USE_GPU and
            self.flags.is_gpu_acceleration_enabled()
        )

    def detect_anomalies_batch(
        self,
        data: np.ndarray,
        model: Any,
        batch_size: int = 1000
    ) -> np.ndarray:
        """
        Detect anomalies in batch using GPU acceleration.

        Args:
            data: Input data array (n_samples, n_features)
            model: Trained PyOD model
            batch_size: Batch size for GPU processing

        Returns:
            Array of anomaly scores
        """
        try:
            if self.use_gpu and hasattr(model, 'decision_function'):
                return self._gpu_batch_detection(data, model, batch_size)
            else:
                # CPU fallback
                return model.decision_function(data)

        except Exception as e:
            logger.error(f"Error in GPU batch detection: {e}")
            # Fallback to CPU
            return model.decision_function(data)

    def _gpu_batch_detection(
        self,
        data: np.ndarray,
        model: Any,
        batch_size: int
    ) -> np.ndarray:
        """Perform batch detection on GPU."""
        n_samples = data.shape[0]
        scores = np.zeros(n_samples)

        # Process in batches to avoid GPU memory overflow
        for start_idx in range(0, n_samples, batch_size):
            end_idx = min(start_idx + batch_size, n_samples)
            batch = data[start_idx:end_idx]

            # Move batch to GPU
            if self.use_gpu:
                try:
                    batch_gpu = torch.tensor(batch, device=self.device, dtype=torch.float32)
                    # Process batch
                    batch_scores = model.decision_function(batch_gpu.cpu().numpy())
                    scores[start_idx:end_idx] = batch_scores
                except Exception as e:
                    logger.warning(f"GPU processing failed, falling back to CPU: {e}")
                    batch_scores = model.decision_function(batch)
                    scores[start_idx:end_idx] = batch_scores
            else:
                batch_scores = model.decision_function(batch)
                scores[start_idx:end_idx] = batch_scores

        return scores

    def compute_distances_gpu(
        self,
        X: np.ndarray,
        Y: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute pairwise distances using GPU.

        Args:
            X: First array (n_samples_1, n_features)
            Y: Second array (n_samples_2, n_features). If None, compute X vs X.

        Returns:
            Distance matrix
        """
        if not self.use_gpu:
            # CPU fallback using scipy
            from scipy.spatial.distance import cdist
            if Y is None:
                Y = X
            return cdist(X, Y)

        try:
            # GPU computation using CuPy
            X_gpu = cp.asarray(X)

            if Y is None:
                Y_gpu = X_gpu
            else:
                Y_gpu = cp.asarray(Y)

            # Compute pairwise Euclidean distances
            distances = cp.linalg.norm(X_gpu[:, None] - Y_gpu[None, :], axis=2)

            return cp.asnumpy(distances)

        except Exception as e:
            logger.error(f"GPU distance computation failed: {e}")
            # Fallback to CPU
            from scipy.spatial.distance import cdist
            if Y is None:
                Y = X
            return cdist(X, Y)

    def zscore_gpu(self, data: np.ndarray) -> np.ndarray:
        """
        Compute Z-scores using GPU.

        Args:
            data: Input data array

        Returns:
            Z-scores
        """
        if not self.use_gpu:
            # CPU fallback
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            return (data - mean) / (std + 1e-10)

        try:
            # GPU computation
            data_gpu = cp.asarray(data)
            mean = cp.mean(data_gpu, axis=0)
            std = cp.std(data_gpu, axis=0)
            zscores = (data_gpu - mean) / (std + 1e-10)
            return cp.asnumpy(zscores)

        except Exception as e:
            logger.error(f"GPU zscore computation failed: {e}")
            # Fallback to CPU
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            return (data - mean) / (std + 1e-10)

    def correlation_matrix_gpu(self, data: np.ndarray) -> np.ndarray:
        """
        Compute correlation matrix using GPU.

        Args:
            data: Input data array (n_samples, n_features)

        Returns:
            Correlation matrix (n_features, n_features)
        """
        if not self.use_gpu:
            # CPU fallback
            return np.corrcoef(data, rowvar=False)

        try:
            # GPU computation
            data_gpu = cp.asarray(data)
            corr = cp.corrcoef(data_gpu, rowvar=False)
            return cp.asnumpy(corr)

        except Exception as e:
            logger.error(f"GPU correlation computation failed: {e}")
            # Fallback to CPU
            return np.corrcoef(data, rowvar=False)

    def get_gpu_memory_info(self) -> Dict[str, Any]:
        """
        Get GPU memory usage information.

        Returns:
            Dictionary with memory statistics
        """
        if not GPU_AVAILABLE or not self.use_gpu:
            return {
                'gpu_available': False,
                'message': 'GPU not available or not enabled'
            }

        try:
            import torch

            return {
                'gpu_available': True,
                'device_name': torch.cuda.get_device_name(0),
                'total_memory_mb': torch.cuda.get_device_properties(0).total_memory / 1024 / 1024,
                'allocated_memory_mb': torch.cuda.memory_allocated(0) / 1024 / 1024,
                'cached_memory_mb': torch.cuda.memory_reserved(0) / 1024 / 1024,
                'free_memory_mb': (
                    torch.cuda.get_device_properties(0).total_memory -
                    torch.cuda.memory_allocated(0)
                ) / 1024 / 1024
            }

        except Exception as e:
            logger.error(f"Error getting GPU memory info: {e}")
            return {
                'gpu_available': True,
                'error': str(e)
            }

    def clear_gpu_cache(self):
        """Clear GPU memory cache."""
        if not GPU_AVAILABLE or not self.use_gpu:
            return

        try:
            import torch
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
        except Exception as e:
            logger.error(f"Error clearing GPU cache: {e}")

    def benchmark_gpu_vs_cpu(
        self,
        data: np.ndarray,
        model: Any,
        iterations: int = 10
    ) -> Dict[str, float]:
        """
        Benchmark GPU vs CPU performance.

        Args:
            data: Test data
            model: Model to benchmark
            iterations: Number of iterations

        Returns:
            Dictionary with timing results
        """
        import time

        # CPU timing
        cpu_times = []
        for _ in range(iterations):
            start = time.time()
            _ = model.decision_function(data)
            cpu_times.append(time.time() - start)

        cpu_avg = np.mean(cpu_times)

        # GPU timing (if available)
        if self.use_gpu:
            gpu_times = []
            for _ in range(iterations):
                start = time.time()
                _ = self.detect_anomalies_batch(data, model)
                gpu_times.append(time.time() - start)

            gpu_avg = np.mean(gpu_times)
            speedup = cpu_avg / gpu_avg

            return {
                'cpu_time_ms': cpu_avg * 1000,
                'gpu_time_ms': gpu_avg * 1000,
                'speedup': speedup,
                'gpu_faster': speedup > 1.0
            }
        else:
            return {
                'cpu_time_ms': cpu_avg * 1000,
                'gpu_time_ms': None,
                'speedup': 1.0,
                'gpu_faster': False,
                'message': 'GPU not available'
            }
