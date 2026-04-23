"""
Tutorial System Configuration Module

This module exports all tutorial-related configurations.
Visual styling is now handled by DesignTokens for consistency.
"""

from .tutorial_config import (
    StepType,
    PanelConfig,
    ButtonConfig,
    ContentCardConfig,
    TUTORIAL_CONTENT,
)

__all__ = [
    'StepType',
    'PanelConfig',
    'ButtonConfig',
    'ContentCardConfig',
    'TUTORIAL_CONTENT',
]
