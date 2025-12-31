"""
Vectorize Service - Hybrid Implementation with Automatic Fallback

This is the main vectorization service with built-in resilience.
Implements a hybrid strategy: custom self-deployed service (primary) 
with automatic fallback to DeepInfra (secondary).

Usage:
    from agentic_layer.vectorize_service import get_vectorize_service
    
    service = get_vectorize_service()
    embedding = await service.get_embedding("Hello world")  # Auto-fallback
"""

import logging
import os
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
import numpy as np

from core.di.decorators import service

from agentic_layer.vectorize_interface import VectorizeServiceInterface, VectorizeError, UsageInfo
from agentic_layer.vectorize_custom import CustomVectorizeService, CustomVectorizeConfig
from agentic_layer.vectorize_deepinfra import (
    DeepInfraVectorizeService,
    DeepInfraVectorizeConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class HybridVectorizeConfig:
    """Configuration for hybrid vectorize service with fallback"""

    # Custom service config
    custom_config: CustomVectorizeConfig = field(default_factory=CustomVectorizeConfig)

    # DeepInfra config
    deepinfra_config: DeepInfraVectorizeConfig = field(
        default_factory=DeepInfraVectorizeConfig
    )

    # Fallback behavior
    enable_fallback: bool = True
    max_custom_failures: int = 3

    # Runtime state (failure tracking)
    _custom_failure_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        """Load hybrid service configuration from environment"""
        self.enable_fallback = (
            os.getenv("ENABLE_EMBEDDING_FALLBACK", "true").lower() == "true"
        )
        self.max_custom_failures = int(
            os.getenv("MAX_CUSTOM_FAILURES", str(self.max_custom_failures))
        )


class HybridVectorizeService(VectorizeServiceInterface):
    """
    Hybrid Vectorization Service with Automatic Fallback
    
    This service implements a dual-strategy approach:
    1. Implements VectorizeServiceInterface with full API
    2. Primary: Custom self-deployed service (low cost, fast)
    3. Secondary: DeepInfra commercial API (high availability)
    4. Automatic failover on errors with failure tracking
    5. All method calls transparently use fallback logic
    
    Strategy Benefits:
    - Cost optimization: ~95% savings with custom service
    - High availability: Automatic failover ensures reliability
    - Zero downtime: Continues working during custom service maintenance
    
    Usage:
        service = HybridVectorizeService()
        embedding = await service.get_embedding("Hello")  # Auto-fallback built-in
    """

    def __init__(self, config: Optional[HybridVectorizeConfig] = None):
        if config is None:
            config = HybridVectorizeConfig()

        self.config = config
        
        # Initialize both services
        self.custom_service = CustomVectorizeService(config.custom_config)
        self.deepinfra_service = DeepInfraVectorizeService(config.deepinfra_config)
        
        # Current active service
        self._current_service: VectorizeServiceInterface = self.custom_service

        logger.info(
            f"Initialized HybridVectorizeService | "
            f"fallback_enabled={config.enable_fallback} | "
            f"max_failures={config.max_custom_failures}"
        )

    def get_service(self) -> VectorizeServiceInterface:
        """
        Get the current active service (for advanced usage)
        
        Returns:
            VectorizeServiceInterface: The active service (custom or deepinfra)
            
        Note: Prefer using proxy methods directly for automatic fallback
        """
        return self._current_service
    
    # Implement VectorizeServiceInterface methods with automatic fallback
    
    async def get_embedding(
        self, text: str, instruction: Optional[str] = None, is_query: bool = False
    ) -> np.ndarray:
        """Get embedding for a single text with automatic fallback"""
        return await self.execute_with_fallback(
            "get_embedding",
            lambda: self.custom_service.get_embedding(text, instruction, is_query),
            lambda: self.deepinfra_service.get_embedding(text, instruction, is_query),
        )
    
    async def get_embedding_with_usage(
        self, text: str, instruction: Optional[str] = None, is_query: bool = False
    ) -> Tuple[np.ndarray, Optional[UsageInfo]]:
        """Get embedding with usage information with automatic fallback"""
        return await self.execute_with_fallback(
            "get_embedding_with_usage",
            lambda: self.custom_service.get_embedding_with_usage(text, instruction, is_query),
            lambda: self.deepinfra_service.get_embedding_with_usage(text, instruction, is_query),
        )
    
    async def get_embeddings(
        self,
        texts: List[str],
        instruction: Optional[str] = None,
        is_query: bool = False,
    ) -> List[np.ndarray]:
        """Get embeddings for multiple texts with automatic fallback"""
        return await self.execute_with_fallback(
            "get_embeddings",
            lambda: self.custom_service.get_embeddings(texts, instruction, is_query),
            lambda: self.deepinfra_service.get_embeddings(texts, instruction, is_query),
        )
    
    async def get_embeddings_batch(
        self,
        text_batches: List[List[str]],
        instruction: Optional[str] = None,
        is_query: bool = False,
    ) -> List[List[np.ndarray]]:
        """Get embeddings for multiple batches with automatic fallback"""
        return await self.execute_with_fallback(
            "get_embeddings_batch",
            lambda: self.custom_service.get_embeddings_batch(text_batches, instruction, is_query),
            lambda: self.deepinfra_service.get_embeddings_batch(text_batches, instruction, is_query),
        )
    
    def get_model_name(self) -> str:
        """Get the current model name (from custom service)"""
        return self.custom_service.get_model_name()

    async def execute_with_fallback(self, operation_name: str, primary_func, fallback_func):
        """
        Execute operation with automatic fallback logic
        
        Args:
            operation_name: Name of the operation for logging
            primary_func: Function to call on primary service
            fallback_func: Function to call on fallback service
            
        Returns:
            Result from primary or fallback service
            
        Raises:
            VectorizeError: If both services fail
        """
        # Try primary (custom) service first
        try:
            result = await primary_func()
            # Reset failure count on success
            self.config._custom_failure_count = 0
            return result

        except Exception as primary_error:
            # Increment failure count
            self.config._custom_failure_count += 1

            logger.warning(
                f"Custom service {operation_name} failed "
                f"(count: {self.config._custom_failure_count}): {primary_error}"
            )

            # Check if fallback is enabled
            if not self.config.enable_fallback:
                logger.error("Fallback disabled, re-raising error")
                raise VectorizeError(
                    f"Custom service failed and fallback is disabled: {primary_error}"
                )

            # Check if exceeded max failures
            if self.config._custom_failure_count >= self.config.max_custom_failures:
                logger.warning(
                    f"⚠️ Custom service exceeded max failures ({self.config.max_custom_failures}), "
                    f"using DeepInfra fallback"
                )

            # Try fallback service
            try:
                logger.info(f"🔄 Falling back to DeepInfra for {operation_name}")
                result = await fallback_func()
                return result

            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {fallback_error}")
                raise VectorizeError(
                    f"Both custom and fallback services failed. "
                    f"Custom: {primary_error}, Fallback: {fallback_error}"
                )

    def get_failure_count(self) -> int:
        """Get current custom service failure count"""
        return self.config._custom_failure_count

    def reset_failure_count(self):
        """Reset failure count (useful for health check recovery)"""
        self.config._custom_failure_count = 0
        logger.info("Reset custom service failure count to 0")

    async def close(self):
        """Close all services"""
        await self.custom_service.close()
        await self.deepinfra_service.close()


# Global service instance (lazy initialization)
_service_instance: Optional[HybridVectorizeService] = None


def get_hybrid_service() -> HybridVectorizeService:
    """
    Get the global hybrid service instance (singleton)
    
    Returns:
        HybridVectorizeService: The global hybrid service instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = HybridVectorizeService()
    return _service_instance


# Main entry point - registered with DI container
@service(name="vectorize_service", primary=True)
def get_vectorize_service() -> VectorizeServiceInterface:
    """
    Get the vectorization service (main entry point)
    
    Returns the hybrid service which implements VectorizeServiceInterface.
    All method calls automatically go through fallback logic.
    
    Returns:
        VectorizeServiceInterface: The hybrid service with automatic fallback
        
    Example:
        ```python
        from agentic_layer.vectorize_service import get_vectorize_service
        
        service = get_vectorize_service()  # Returns hybrid service with fallback
        embedding = await service.get_embedding("Hello world")  # Auto-fallback
        embeddings = await service.get_embeddings(["Text 1", "Text 2"])  # Auto-fallback
        await service.close()
        ```
    """
    return get_hybrid_service()  # Return hybrid service (implements VectorizeServiceInterface)


# Export public API
__all__ = [
    "get_vectorize_service",
]
