"""Cross-platform CJK font loading.

Priority chain:
1. Bundled msyh.ttc (Microsoft YaHei) in airwar/assets/fonts/
2. Windows system msyh.ttc via /mnt/c/Windows/Fonts/ (WSL)
3. System-installed CJK font via pygame.font.match_font()
4. pygame default font (freesansbold — basic CJK support)
"""

import logging
import os
from functools import lru_cache

import pygame

logger = logging.getLogger(__name__)

# Possible paths for a bundled CJK font, relative to this file's package
_BUNDLED_CANDIDATES = [
    "msyh.ttc",
    "wqy-microhei.ttc",
    "NotoSansCJK-Regular.ttc",
    "SourceHanSansSC-Regular.otf",
]

# System CJK font names to try via match_font
_SYSTEM_CJK_NAMES = [
    "microsoftyahei",
    "msyh",
    "Microsoft YaHei",
    "notosanscjksc",
    "notosanscjk",
    "Noto Sans CJK SC",
    "wqy",
    "wenquanyi",
    "WenQuanYi Micro Hei",
    "simhei",
    "SimHei",
    "simsun",
    "SimSun",
    "stxihei",
    "STXihei",
    "sourcehansanssc",
    "Source Han Sans SC",
]


def _find_bundled_font() -> str | None:
    """Search for a bundled CJK font file in the assets directory."""
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
    for name in _BUNDLED_CANDIDATES:
        path = os.path.join(assets_dir, name)
        if os.path.isfile(path):
            return path
    return None


def _find_wsl_font() -> str | None:
    """Try Windows fonts accessible via WSL at /mnt/c/Windows/Fonts/."""
    wsl_fonts = [
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "/mnt/c/Windows/Fonts/STXIHEI.TTF",
        "/mnt/c/Windows/Fonts/simsun.ttc",
    ]
    for path in wsl_fonts:
        if os.path.isfile(path):
            return path
    return None


def _find_system_cjk_font() -> str | None:
    """Search for a CJK font installed on the system via fontconfig/pygame."""
    for name in _SYSTEM_CJK_NAMES:
        path = pygame.font.match_font(name)
        if path:
            return path
    return None


_CJK_FONT_PATH: str | None = None


def _get_cjk_font_path() -> str | None:
    """Lazy-resolve the best available CJK font path."""
    global _CJK_FONT_PATH
    if _CJK_FONT_PATH is None:
        _CJK_FONT_PATH = _find_bundled_font() or _find_wsl_font() or _find_system_cjk_font() or None
    return _CJK_FONT_PATH


@lru_cache(maxsize=32)
def get_cjk_font(size: int) -> pygame.font.Font:
    """Return a font capable of rendering CJK characters at the given size.

    Uses the best available CJK font found on the system. Falls back to
    pygame's default font if no CJK font is available.
    """
    path = _get_cjk_font_path()
    if path:
        try:
            return pygame.font.Font(path, size)
        except (OSError, pygame.error):
            logger.warning("CJK font %s unavailable, falling back", path)
    return pygame.font.Font(None, size)


# Locale prefixes that should use the CJK font. Anything else uses pygame's
# built-in default (a Latin font that also handles most European scripts).
_CJK_LOCALE_PREFIXES = ("zh", "ja", "ko")


def is_cjk_locale(locale: str) -> bool:
    """Return True if ``locale`` should be rendered with the CJK font.

    A locale is "CJK" when its primary language tag starts with ``zh``,
    ``ja``, or ``ko`` (e.g. ``zh_CN``, ``zh_TW``, ``ja_JP``, ``ko_KR``).
    Locale strings are matched case-insensitively against the prefix.
    """
    if not locale:
        return False
    primary = locale.split("_", 1)[0].split("-", 1)[0].lower()
    return primary in _CJK_LOCALE_PREFIXES


@lru_cache(maxsize=64)
def get_font_for_locale(locale: str, size: int) -> pygame.font.Font:
    """Return a font appropriate for the active ``locale``.

    - CJK locales (zh_*, ja_*, ko_*) get :func:`get_cjk_font`.
    - Latin / other locales get pygame's default font (freesansbold),
      which renders basic Latin / European scripts cleanly and is much
      smaller than shipping a second font asset just for placeholders.

    Cached on ``(locale, size)`` — the cache is intentionally small
    because the call sites (login panel placeholder, scene hint text)
    only ever use a handful of size+locale combinations.
    """
    if is_cjk_locale(locale):
        return get_cjk_font(size)
    return pygame.font.Font(None, size)
