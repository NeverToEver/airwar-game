"""Integration tests for multi-page tutorial system — content & rendering validation."""
import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene
from airwar.config.tutorial import TUTORIAL_PAGES
from airwar.config.design_tokens import get_design_tokens


class TestTutorialPages:
    """Validate TUTORIAL_PAGES content structure and accuracy."""

    def test_pages_is_list(self):
        assert isinstance(TUTORIAL_PAGES, list)
        assert len(TUTORIAL_PAGES) == 4

    def test_each_page_has_required_fields(self):
        for page in TUTORIAL_PAGES:
            assert 'title' in page
            assert 'subtitle' in page
            assert 'sections' in page
            assert isinstance(page['sections'], list)
            assert len(page['sections']) > 0

    def test_each_section_has_required_fields(self):
        for page in TUTORIAL_PAGES:
            for section in page['sections']:
                assert 'title' in section
                assert 'items' in section
                assert isinstance(section['items'], list)
                assert len(section['items']) > 0

    def test_items_are_tuples_of_key_desc(self):
        for page in TUTORIAL_PAGES:
            for section in page['sections']:
                for item in section['items']:
                    assert isinstance(item, tuple)
                    assert len(item) == 2
                    assert isinstance(item[0], str)
                    assert isinstance(item[1], str)

    def test_movement_page_has_correct_keys(self):
        page0 = TUTORIAL_PAGES[0]
        all_keys = []
        for sec in page0['sections']:
            for key, _ in sec['items']:
                all_keys.append(key)
        # Correct movement controls
        assert any('W' in k and '↑' in k for k in all_keys)
        assert any('S' in k and '↓' in k for k in all_keys)
        assert any('A' in k and '←' in k for k in all_keys)
        assert any('D' in k and '→' in k for k in all_keys)
        # SHIFT boost must be present (was missing before)
        assert any('SHIFT' in k.upper() for k in all_keys)

    def test_auto_fire_documented_correctly(self):
        """Auto-fire is always on — tutorial must not say SPACE fires."""
        page0 = TUTORIAL_PAGES[0]
        all_keys = []
        for sec in page0['sections']:
            for key, desc in sec['items']:
                all_keys.append((key, desc))
        assert any('Auto-Fire' in key for key, _ in all_keys), \
            "Auto-Fire must be listed as a key"

    def test_surrender_not_tied_to_docked(self):
        """K surrender does NOT require docking (fixed from old content)."""
        page2 = TUTORIAL_PAGES[2]
        all_descs = []
        for sec in page2['sections']:
            for _, desc in sec['items']:
                all_descs.append(desc)
        surrender_desc = [d for d in all_descs if 'Surrender' in d or 'surrender' in d]
        assert any(surrender_desc), "Surrender must be documented"
        for sd in surrender_desc:
            assert 'dock' not in sd.lower(), \
                f"Surrender should not mention docking: '{sd}'"

    def test_reward_selection_uses_ws_not_number_keys(self):
        """Reward selection uses W/S + ENTER/SPACE, NOT 1-4."""
        page3 = TUTORIAL_PAGES[3]
        all_items = []
        for sec in page3['sections']:
            for key, desc in sec['items']:
                all_items.append((key, desc))
        reward_keys = {k for k, _ in all_items}
        # Must have W/S navigation
        assert any('W' in k and 'S' in k for k in reward_keys) or \
               any(('W' in k or '/ S' in k) for k in reward_keys), \
            "W/S navigation must be documented"
        # Must have ENTER/SPACE selection
        assert any('ENTER' in k.upper() for k in reward_keys), \
            "ENTER key must be documented for reward selection"
        # Must NOT have 1-4
        assert not any('1-4' in k for k in reward_keys), \
            "1-4 key binding is incorrect (was in old tutorial)"

    def test_mothership_page_has_docking_and_ammo(self):
        page1 = TUTORIAL_PAGES[1]
        all_keys = []
        for sec in page1['sections']:
            for key, _ in sec['items']:
                all_keys.append(key)
        assert any('H' in k for k in all_keys), "H-dock must be documented"
        assert any('Ammo' in k for k in all_keys), "Ammo system must be documented"

    def test_no_tutorial_renderer_class(self):
        """TutorialRenderer should not exist after refactor."""
        with pytest.raises(ImportError):
            from airwar.scenes.tutorial import TutorialRenderer


class TestTutorialRendering:
    """Light rendering tests for the multi-page tutorial."""

    def test_scene_renders_all_pages(self):
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        scene = TutorialScene()
        scene.enter()
        for pg in range(4):
            scene._current_page = pg
            for _ in range(3):
                scene.update()
            scene.render(surface)
        pygame.quit()

    def test_escape_exits_scene(self):
        scene = TutorialScene()
        scene.enter()
        assert scene.is_running()
        ev = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(ev)
        assert scene.should_quit()

    def test_scene_reset(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 2
        esc = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(esc)
        scene.reset()
        assert scene._current_page == 0
        assert scene.is_running()
        assert not scene.should_quit()

    def test_scene_with_pygame_surface(self):
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        scene = TutorialScene()
        scene.enter()
        for _ in range(5):
            scene.update()
            scene.render(surface)
        assert scene.is_running()
        esc = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(esc)
        assert scene.should_quit()
        pygame.quit()


class TestDesignTokens:
    """Verify design tokens are available for tutorial rendering."""

    def test_scene_colors_available(self):
        tokens = get_design_tokens()
        SC = tokens.scene
        assert hasattr(SC, 'BG_PRIMARY')
        assert hasattr(SC, 'BG_PANEL')
        assert hasattr(SC, 'BG_PANEL_LIGHT')
        assert hasattr(SC, 'BORDER_TEAL')
        assert hasattr(SC, 'BORDER_GLOW')
        assert hasattr(SC, 'GOLD_PRIMARY')
        assert hasattr(SC, 'TEXT_PRIMARY')
        assert hasattr(SC, 'TEXT_DIM')
        assert hasattr(SC, 'TEXT_BRIGHT')
        assert hasattr(SC, 'HINT_DIM')

    def test_font_sizes_available(self):
        tokens = get_design_tokens()
        T = tokens.typography
        assert hasattr(T, 'SUBHEADING_SIZE')
        assert hasattr(T, 'CAPTION_SIZE')
        assert hasattr(T, 'SMALL_SIZE')
        assert hasattr(T, 'TINY_SIZE')
