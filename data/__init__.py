"""
Object Studio Data Module

This module provides configuration constants and data used throughout the application.
"""

from .config import (
    DEBUG,
    CURRENT_VERSION,
    DOCUMENTATION_URL,
    RELEASE_API_ENDPOINT,
)

from .constants import (
    TILE_SIZE,
    CHUNK_SIZES,
    ORIENTATION_VALUES,
)

from .framegen import special_cases

__all__ = [
    # Config
    "DEBUG",
    "CURRENT_VERSION",
    "DOCUMENTATION_URL",
    "RELEASE_API_ENDPOINT",
    # Constants
    "TILE_SIZE",
    "CHUNK_SIZES",
    "ORIENTATION_VALUES",
    # Framegen
    "special_cases",
]
