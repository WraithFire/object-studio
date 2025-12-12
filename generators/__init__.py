"""
Object Studio Generators Module

This module provides functions for converting between frames and objects
"""

from .object_generator import (
    og_process_single_folder,
    og_process_multiple_folder,
    generate_object_main,
    validate_og_input_folder,
)

from .frames_generator import (
    fg_process_single_folder,
    fg_process_multiple_folder,
    generate_frames_main,
    validate_fg_input_folder,
)

__all__ = [
    # Object Generator functions
    "og_process_single_folder",
    "og_process_multiple_folder",
    "generate_object_main",
    "validate_og_input_folder",
    # Frames Generator functions
    "fg_process_single_folder",
    "fg_process_multiple_folder",
    "generate_frames_main",
    "validate_fg_input_folder",
]
