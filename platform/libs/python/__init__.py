"""Shared error taxonomy for n8n Code nodes and Python backends."""

from .errors import (
    BASE_DELAY_S,
    CAP_DELAY_S,
    MAX_ATTEMPTS,
    classify_error,
    compute_next_delay,
)

__all__ = [
    "BASE_DELAY_S",
    "CAP_DELAY_S",
    "MAX_ATTEMPTS",
    "classify_error",
    "compute_next_delay",
]
