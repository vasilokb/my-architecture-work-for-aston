"""
Сервисы для работы с эмбеддингами текста.
"""

from app.services.embeddings.service import (
    EmbeddingService,
    EmbeddingServiceError,
    EmbeddingModelNotLoadedError,
    get_embedding_service,
)

__all__ = [
    "EmbeddingService",
    "EmbeddingServiceError",
    "EmbeddingModelNotLoadedError",
    "get_embedding_service",
]