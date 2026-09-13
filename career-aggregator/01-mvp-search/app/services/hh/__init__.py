"""
Сервисы для работы с HH.ru API.
"""

from app.services.hh.client import (
    HHClient,
    HHClientError,
    HHAPIRateLimitError,
    HHAPIAuthError,
    HHAPINotFoundError,
    get_hh_client,
    HHClientContext,
)

__all__ = [
    "HHClient",
    "HHClientError",
    "HHAPIRateLimitError",
    "HHAPIAuthError",
    "HHAPINotFoundError",
    "get_hh_client",
    "HHClientContext",
]