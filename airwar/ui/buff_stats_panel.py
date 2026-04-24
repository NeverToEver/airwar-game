from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import math
import pygame
import logging

from airwar.config.design_tokens import MilitaryColors, MilitaryUI
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.hex_icon import HexIcon, ICON_POWER, ICON_DEFENSE, ICON_SPEED

logger = logging.getLogger(__name__)


@dataclass
class BuffStatEntry:
    name: str
    short_name: str
    value: str
    level: int
    color: Tuple[int, int, int]
    category: str


class BuffStatsAggregator:
    def __init__(self):
        self._stat_formatters = self._init_stat_formatters()
        self._category_order = ['offense', 'defense', 'health', 'utility']

    def _init_stat_formatters(self) -> Dict[str, callable]:
        return {
            'Power Shot': lambda rs, p: f"+{int((p.bullet_damage / rs.base_bullet_damage - 1) * 100)}%",
            'Rapid Fire': lambda rs, p: self._calculate_rapid_fire_value(rs),
            'Piercing': lambda rs, _: f"Lv.{rs.piercing_level}",
            'Spread Shot': lambda rs, _: f"Lv.{rs.spread_level}",
            'Explosive': lambda rs, _: f"Lv.{rs.explosive_level}",
            'Shotgun': lambda rs, _: "ON" if 'Shotgun' in rs.unlocked_buffs else "-",
            'Laser': lambda rs, _: "ON" if 'Laser' in rs.unlocked_buffs else "-",
            'Armor': lambda rs, _: f"-{rs.armor_level * 15}%",
            'Evasion': lambda rs, _: f"+{rs.evasion_level * 20}%",
            'Barrier': lambda rs, _: "+50",
            'Extra Life': lambda rs, _: f"+50 HP",
            'Regeneration': lambda rs, _: "+2/s",
            'Lifesteal': lambda rs, _: "+10%",
            'Speed Boost': lambda rs, _: "+15%",
            'Magnet': lambda rs, _: "+30%",
            'Slow Field': lambda rs, _: f"{int((1 - rs.slow_factor) * 100)}%",
            'Shield': lambda rs, _: "Ready" if 'Shield' in rs.unlocked_buffs else "-",
        }

    def _calculate_rapid_fire_value(self, reward_system) -> str:
        level = getattr(reward_system, 'rapid_fire_level', 0)
        if level <= 0:
            return "-"
        base_cooldown = reward_system.base_fire_cooldown
        cooldown = base_cooldown
        for _ in range(level):
            cooldown = max(1, int(cooldown * 0.8))
        bonus = int((1 - cooldown / base_cooldown) * 100)
        return f"+{bonus}%"

    def _get_buff_color(self, name: str, reward_system) -> Tuple[int, int, int]:
        try:
            from airwar.game.buffs.buff_registry import create_buff
            return create_buff(name).get_color()
        except (ValueError, AttributeError):
            return MilitaryColors.STATS_TEXT

    def _get_buff_category(self, name: str) -> str:
        category_map = {
            'Power Shot': 'offense', 'Rapid Fire': 'offense', 'Piercing': 'offense',
            'Spread Shot': 'offense', 'Explosive': 'offense', 'Shotgun': 'offense',
            'Laser': 'offense',
            'Armor': 'defense', 'Evasion': 'defense', 'Shield': 'defense',
            'Barrier': 'defense',
            'Extra Life': 'health', 'Regeneration': 'health', 'Lifesteal': 'health',
            'Speed Boost': 'utility', 'Magnet': 'utility', 'Slow Field': 'utility',
        }
        return category_map.get(name, 'utility')

    def _get_short_name(self, name: str) -> str:
        short_names = {
            'Power Shot': 'PWR', 'Rapid Fire': 'RPD', 'Piercing': 'PIR',
            'Spread Shot': 'SPD', 'Explosive': 'EXP', 'Shotgun': 'SHT',
            'Laser': 'LSR', 'Armor': 'ARM', 'Evasion': 'EVD',
            'Barrier': 'BAR', 'Extra Life': 'XLP', 'Regeneration': 'REG',
            'Lifesteal': 'LST', 'Speed Boost': 'SPB', 'Magnet': 'MAG',
            'Slow Field': 'SLO', 'Shield': 'SHD',
        }
        return short_names.get(name, name[:3].upper())

    def _get_buff_level(self, name: str, reward_system) -> int:
        level_map = {
            'Piercing': reward_system.piercing_level,
            'Spread Shot': reward_system.spread_level,
            'Explosive': reward_system.explosive_level,
            'Armor': reward_system.armor_level,
            'Evasion': reward_system.evasion_level,
        }
        return level_map.get(name, 1)

    def get_buff_stats(self, reward_system, player) -> List[BuffStatEntry]:
        if not reward_system or not reward_system.unlocked_buffs:
            return []

        entries = []
        for buff_name in reward_system.unlocked_buffs:
            try:
                formatter = self._stat_formatters.get(buff_name)
                if formatter:
                    value = formatter(reward_system, player)
                else:
                    value = "ON"

                entries.append(BuffStatEntry(
                    name=buff_name,
                    short_name=self._get_short_name(buff_name),
                    value=value,
                    level=self._get_buff_level(buff_name, reward_system),
                    color=self._get_buff_color(buff_name, reward_system),
                    category=self._get_buff_category(buff_name)
                ))
            except (AttributeError, TypeError, KeyError) as e:
                logger.debug(f"Failed to format buff '{buff_name}': {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error processing buff '{buff_name}': {e}")
                continue

        return entries

    def get_summary_stats(self, reward_system, player) -> Dict[str, str]:
        if not reward_system:
            return {}

        summary = {}
        try:
            base_damage = reward_system.base_bullet_damage
            current_damage = player.bullet_damage
            total_damage_bonus = int((current_damage / base_damage - 1) * 100) if current_damage > base_damage else 0
            if total_damage_bonus > 0:
                summary['DMG'] = f"+{total_damage_bonus}%"

            rapid_fire_value = self._calculate_rapid_fire_value(reward_system)
            if rapid_fire_value != "-":
                summary['RATE'] = rapid_fire_value

            total_armor = reward_system.armor_level * 15
            if total_armor > 0:
                summary['ARM'] = f"-{total_armor}%"

            total_dodge = reward_system.evasion_level * 20
            if total_dodge > 0:
                summary['EVD'] = f"+{total_dodge}%"

            total_pierce = reward_system.piercing_level
            if total_pierce > 0:
                summary['PIR'] = f"+{total_pierce}"

            if reward_system.explosive_level > 0:
                summary['EXP'] = f"Lv.{reward_system.explosive_level}"

            if reward_system.spread_level > 0:
                summary['SPD'] = f"Lv.{reward_system.spread_level}"

        except (AttributeError, TypeError) as e:
            logger.debug(f"Failed to calculate summary stats: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error calculating summary stats: {e}")

        return summary


class BuffStatsPanel:
    _MAX_CACHE_SIZE = 50
    _panel_surface_cache: dict = {}

    @classmethod
    def _add_to_cache(cls, key, surface):
        if len(cls._panel_surface_cache) >= cls._MAX_CACHE_SIZE:
            cls._panel_surface_cache.clear()
        cls._panel_surface_cache[key] = surface

    def __init__(self):
        from airwar.config.design_tokens import get_design_tokens
        pygame.font.init()

        self._tokens = get_design_tokens()
        colors = self._tokens.colors

        self._panel_width = 160
        self._panel_padding = 10
        self._item_height = 28
        self._item_spacing = 4
        self._summary_height = 50
        self._corner_radius = 8
        self._border_width = 1

        self._title_font = pygame.font.Font(None, 18)
        self._name_font = pygame.font.Font(None, 16)
        self._value_font = pygame.font.Font(None, 14)
        self._summary_font = pygame.font.Font(None, 15)

        self._bg_color = (*colors.BACKGROUND_PANEL, 25)
        self._border_color = (*colors.PANEL_BORDER, 80)
        self._title_color = colors.TEXT_SECONDARY
        self._summary_bg_color = (*colors.BACKGROUND_PANEL, 30)

        self._aggregator = BuffStatsAggregator()
        self._cached_surface: Optional[pygame.Surface] = None
        self._cache_valid = False

    def _calculate_panel_height(self, buff_count: int) -> int:
        if buff_count == 0:
            return 0
        header_height = 25
        items_height = buff_count * self._item_height + (buff_count - 1) * self._item_spacing
        return header_height + items_height + self._item_spacing + self._summary_height + self._panel_padding * 2

    def _create_panel_surface(self, width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(
            surface, self._bg_color,
            (0, 0, width, height),
            border_radius=self._corner_radius
        )
        pygame.draw.rect(
            surface, self._border_color,
            (0, 0, width, height),
            self._border_width,
            border_radius=self._corner_radius
        )
        return surface

    def render(
        self,
        surface: pygame.Surface,
        reward_system,
        player,
        screen_width: int,
        screen_height: int,
        use_military: bool = True
    ) -> None:
        if not reward_system or not reward_system.unlocked_buffs:
            return

        try:
            buff_entries = self._aggregator.get_buff_stats(reward_system, player)
            if not buff_entries:
                return

            summary = self._aggregator.get_summary_stats(reward_system, player)

            panel_height = self._calculate_panel_height(len(buff_entries))
            panel_x = screen_width - self._panel_width - 15
            panel_y = (screen_height - panel_height) // 2

            if panel_y < 50:
                panel_y = 50

            if use_military:
                self._render_military_style(
                    surface, buff_entries, summary,
                    self._panel_width, panel_height,
                    panel_x, panel_y
                )
            else:
                cache_key = (self._panel_width, panel_height, tuple(sorted(reward_system.unlocked_buffs)))
                if cache_key not in BuffStatsPanel._panel_surface_cache:
                    panel_surface = self._create_panel_surface(self._panel_width, panel_height)
                    self._render_header(panel_surface)
                    self._render_buff_items(panel_surface, buff_entries)
                    self._render_summary(panel_surface, summary)
                    self._add_to_cache(cache_key, panel_surface)
                else:
                    panel_surface = BuffStatsPanel._panel_surface_cache[cache_key]

                surface.blit(panel_surface, (panel_x, panel_y))

        except (AttributeError, TypeError) as e:
            logger.debug(f"Failed to render buff stats panel: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error rendering buff stats panel: {e}")

    def _render_header(self, surface: pygame.Surface) -> None:
        title = self._title_font.render("ACTIVE BUFFS", True, self._title_color)
        title_rect = title.get_rect(centerx=surface.get_width() // 2, top=self._panel_padding)
        surface.blit(title, title_rect)

        pygame.draw.line(
            surface, self._border_color,
            (self._panel_padding, 22),
            (surface.get_width() - self._panel_padding, 22),
            1
        )

    def _render_buff_items(self, surface: pygame.Surface, entries: List[BuffStatEntry]) -> None:
        y_offset = 25 + self._item_spacing

        for entry in entries:
            self._render_buff_item(surface, entry, y_offset)
            y_offset += self._item_height + self._item_spacing

    def _render_buff_item(self, surface: pygame.Surface, entry: BuffStatEntry, y_offset: int) -> None:
        x = self._panel_padding + 5
        item_width = surface.get_width() - (self._panel_padding + 5) * 2
        item_height = self._item_height

        bg_rect = pygame.Rect(x, y_offset, item_width, item_height)
        pygame.draw.rect(surface, (*entry.color[:3], 15), bg_rect, border_radius=4)

        name_text = self._name_font.render(entry.short_name, True, entry.color)
        surface.blit(name_text, (x + 5, y_offset + 4))

        value_text = self._value_font.render(entry.value, True, MilitaryColors.STATS_TEXT_BRIGHT)
        value_rect = value_text.get_rect(right=x + item_width - 5, centery=y_offset + item_height // 2)
        surface.blit(value_text, value_rect)

        if entry.level > 1:
            level_text = self._value_font.render(f"x{entry.level}", True, MilitaryColors.STATS_TEXT_DIM)
            surface.blit(level_text, (x + 5, y_offset + item_height - 14))

    def _render_summary(self, surface: pygame.Surface, summary: Dict[str, str]) -> None:
        if not summary:
            return

        y_offset = surface.get_height() - self._summary_height - self._panel_padding

        pygame.draw.line(
            surface, self._border_color,
            (self._panel_padding, y_offset),
            (surface.get_width() - self._panel_padding, y_offset),
            1
        )

        y_offset += 8
        x = self._panel_padding + 5

        for key, value in list(summary.items())[:4]:
            text = self._summary_font.render(f"{key}:{value}", True, MilitaryColors.STATS_TEXT)
            surface.blit(text, (x, y_offset))
            x += text.get_width() + 12

            if x > surface.get_width() - 80:
                break

    def _render_military_style(
        self,
        surface: pygame.Surface,
        buff_entries: List[BuffStatEntry],
        summary: Dict[str, str],
        panel_width: int,
        panel_height: int,
        panel_x: int,
        panel_y: int
    ) -> None:
        """Render buff stats panel in military style"""
        # Draw chamfered panel background
        draw_chamfered_panel(
            surface, panel_x, panel_y, panel_width, panel_height,
            MilitaryColors.BG_PANEL,
            MilitaryColors.BORDER_GLOW,
            MilitaryColors.AMBER_GLOW,
            chamfer_depth=8
        )

        # Render content on a separate surface
        content_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        content_surf.fill((0, 0, 0, 0))

        # Title
        title_font = pygame.font.Font(None, MilitaryUI.MILITARY_LABEL_SIZE)
        title = title_font.render("ACTIVE", True, MilitaryColors.TEXT_DIM)
        title_rect = title.get_rect(centerx=panel_width // 2, top=10)
        content_surf.blit(title, title_rect)

        # Divider line
        pygame.draw.line(
            content_surf, MilitaryColors.BORDER_DIM,
            (10, 30), (panel_width - 10, 30), 1
        )

        # Buff items
        y_offset = 40
        for entry in buff_entries:
            self._render_military_buff_item(content_surf, entry, y_offset, panel_width)
            y_offset += 32

        # Summary (if any)
        if summary:
            pygame.draw.line(
                content_surf, MilitaryColors.BORDER_DIM,
                (10, y_offset + 5), (panel_width - 10, y_offset + 5), 1
            )
            y_offset += 15
            summary_font = pygame.font.Font(None, MilitaryUI.MILITARY_SMALL_SIZE)
            x_offset = 10
            for key, value in list(summary.items())[:4]:
                text = summary_font.render(f"{key}:{value}", True, MilitaryColors.AMBER_PRIMARY)
                content_surf.blit(text, (x_offset, y_offset))
                x_offset += text.get_width() + 15

        surface.blit(content_surf, (panel_x, panel_y))

    def _render_military_buff_item(
        self,
        surface: pygame.Surface,
        entry: BuffStatEntry,
        y_offset: int,
        panel_width: int
    ) -> None:
        """Render a single buff item in military style"""
        # Determine icon type based on category
        icon_type = ICON_POWER
        if entry.category == 'defense':
            icon_type = ICON_DEFENSE
        elif entry.category == 'utility':
            icon_type = ICON_SPEED

        # Draw hexagon icon
        icon = HexIcon(icon_type, 12, is_active=True)
        icon.render(surface, (20, y_offset + 10), entry.color)

        # Buff name
        name_font = pygame.font.Font(None, MilitaryUI.MILITARY_SMALL_SIZE)
        name_text = name_font.render(entry.short_name, True, MilitaryColors.TEXT_PRIMARY)
        surface.blit(name_text, (38, y_offset + 2))

        # Buff value
        value_text = name_font.render(entry.value, True, MilitaryColors.AMBER_PRIMARY)
        value_rect = value_text.get_rect(right=panel_width - 10, top=y_offset + 2)
        surface.blit(value_text, value_rect)

        # Level indicator
        if entry.level > 1:
            level_text = name_font.render(f"x{entry.level}", True, MilitaryColors.TEXT_DIM)
            surface.blit(level_text, (38, y_offset + 16))


@dataclass
class AttackModeEntry:
    name: str
    short_name: str
    is_on: bool
    color: Tuple[int, int, int]


class AttackModePanel:
    """Horizontal attack mode indicator strip at top-left."""

    PANEL_WIDTH = 240
    PANEL_HEIGHT = 80
    LIGHT_SIZE = 16

    def __init__(self):
        pygame.font.init()
        from airwar.config.design_tokens import MilitaryColors, MilitaryUI
        self._colors = MilitaryColors
        self._font = pygame.font.Font(None, MilitaryUI.MILITARY_LABEL_SIZE)
        self._name_font = pygame.font.Font(None, MilitaryUI.MILITARY_LABEL_SIZE)

    def render(
        self,
        surface: pygame.Surface,
        reward_system,
        screen_width: int,
        screen_height: int
    ) -> None:
        if not reward_system:
            return

        spread_on = reward_system.spread_level > 0 or 'Shotgun' in reward_system.unlocked_buffs
        laser_on = reward_system.laser_level > 0 or 'Laser' in reward_system.unlocked_buffs
        explosive_on = reward_system.explosive_level > 0

        panel_x = 15
        panel_y = 95

        draw_chamfered_panel(
            surface, panel_x, panel_y, self.PANEL_WIDTH, self.PANEL_HEIGHT,
            MilitaryColors.BG_PANEL,
            MilitaryColors.BORDER_GLOW,
            MilitaryColors.AMBER_GLOW,
            chamfer_depth=5
        )

        content_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
        content_surf.fill((0, 0, 0, 0))

        # Title
        title = self._font.render("ATTACK", True, MilitaryColors.TEXT_BRIGHT)
        title_rect = title.get_rect(left=12, top=6)
        content_surf.blit(title, title_rect)

        entries = [
            AttackModeEntry("SPR", "SPREAD", spread_on, (255, 160, 30)),
            AttackModeEntry("LAS", "LASER", laser_on, (255, 80, 180)),
            AttackModeEntry("EXP", "EXPLOSIVE", explosive_on, (255, 100, 50)),
        ]

        spacing = self.PANEL_WIDTH // 3
        hex_center_y = 46
        label_top_y = hex_center_y + self.LIGHT_SIZE + 4

        for i, entry in enumerate(entries):
            cx = spacing * i + spacing // 2
            color_on = entry.color
            color_off = (80, 80, 90)
            color = color_on if entry.is_on else color_off

            # Glow when on
            if entry.is_on:
                glow_surf = pygame.Surface((self.LIGHT_SIZE * 4 + 8, self.LIGHT_SIZE * 4 + 8), pygame.SRCALPHA)
                for r in range(self.LIGHT_SIZE + 4, 1, -2):
                    alpha = max(0, 70 - (r - 1) * 5)
                    pygame.draw.circle(glow_surf, (*color_on, alpha),
                                       (self.LIGHT_SIZE * 2 + 4, self.LIGHT_SIZE * 2 + 4), r)
                content_surf.blit(glow_surf, (cx - self.LIGHT_SIZE * 2 - 4, hex_center_y - self.LIGHT_SIZE * 2 - 4))

            # Hexagon indicator
            hex_surf = self._draw_hexagon(self.LIGHT_SIZE, color)
            hex_rect = hex_surf.get_rect(center=(cx, hex_center_y))
            content_surf.blit(hex_surf, hex_rect)

            # Label below hexagon
            label_color = color_on if entry.is_on else (110, 110, 120)
            label = self._name_font.render(entry.short_name, True, label_color)
            label_rect = label.get_rect(centerx=cx, top=label_top_y)
            content_surf.blit(label, label_rect)

        surface.blit(content_surf, (panel_x, panel_y))

    def _draw_hexagon(self, size: int, color: Tuple[int, int, int]) -> pygame.Surface:
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        cx, cy = size, size
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append((px, py))
        pygame.draw.polygon(surf, color, points)
        inner = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            px = cx + (size - 3) * math.cos(angle)
            py = cy + (size - 3) * math.sin(angle)
            inner.append((px, py))
        pygame.draw.polygon(surf, (30, 30, 40), inner)
        return surf
