from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pygame


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
            return (200, 200, 200)

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
            except Exception:
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

        except Exception:
            pass

        return summary


class BuffStatsPanel:
    _panel_surface_cache: dict = {}

    def __init__(self):
        pygame.font.init()
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

        self._bg_color = (15, 15, 30, 25)
        self._border_color = (60, 60, 90, 80)
        self._title_color = (180, 180, 210)
        self._summary_bg_color = (20, 20, 40, 30)

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
        screen_height: int
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

            cache_key = (self._panel_width, panel_height, tuple(sorted(reward_system.unlocked_buffs)))
            if cache_key not in BuffStatsPanel._panel_surface_cache:
                panel_surface = self._create_panel_surface(self._panel_width, panel_height)
                self._render_header(panel_surface)
                self._render_buff_items(panel_surface, buff_entries)
                self._render_summary(panel_surface, summary)
                BuffStatsPanel._panel_surface_cache[cache_key] = panel_surface
            else:
                panel_surface = BuffStatsPanel._panel_surface_cache[cache_key]

            surface.blit(panel_surface, (panel_x, panel_y))

        except Exception:
            return

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

        value_text = self._value_font.render(entry.value, True, (220, 220, 240))
        value_rect = value_text.get_rect(right=x + item_width - 5, centery=y_offset + item_height // 2)
        surface.blit(value_text, value_rect)

        if entry.level > 1:
            level_text = self._value_font.render(f"x{entry.level}", True, (150, 150, 180))
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
            text = self._summary_font.render(f"{key}:{value}", True, (200, 200, 220))
            surface.blit(text, (x, y_offset))
            x += text.get_width() + 12

            if x > surface.get_width() - 80:
                break
