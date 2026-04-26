"""Responsive helper — adaptive sizing for varying screen dimensions."""
class ResponsiveHelper:
    """Responsive helper — adaptive sizing calculations for varying screen dimensions."""
    BASE_WIDTH = 1280
    BASE_HEIGHT = 720
    MIN_SCALE = 0.625
    MAX_SCALE = 1.5

    @staticmethod
    def get_scale_factor(width: int, height: int) -> float:
        scale = width / ResponsiveHelper.BASE_WIDTH
        return max(ResponsiveHelper.MIN_SCALE, min(scale, ResponsiveHelper.MAX_SCALE))

    @staticmethod
    def scale(spacing: int, scale: float) -> int:
        return int(spacing * scale)

    @staticmethod
    def font_size(base_size: int, scale: float) -> int:
        return int(base_size * scale)
