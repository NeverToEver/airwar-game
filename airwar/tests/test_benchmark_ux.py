"""Regression test for the BenchmarkScene UX affordance.

Background: a user reported that the benchmark scene's idle state
showed a single static box labelled "自动化测试" with no obvious
affordance — they could not tell whether to click it, press Enter,
or whether anything was actually running.

The fix:
* the i18n key ``benchmark.enter_button`` is now an action
  ("▶ 开始运行 [Enter]" / "▶ Run [Enter]") rather than a
  description
* a new i18n key ``benchmark.enter_hint`` is rendered directly
  under the button ("按 Enter 或点击按钮" / "Press Enter or
  click the button")
* both keys are present in **both** locales (zh_CN + en_US)

This test pins all three contracts so a future translator
regression cannot re-introduce the static-box UX.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _load_locale(code: str) -> dict[str, str]:
    import json
    import pathlib

    path = pathlib.Path(__file__).parent.parent / "locales" / f"{code}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_benchmark_enter_button_is_action_verb_not_title() -> None:
    """The enter button must use an action verb in both locales.

    The old text ("进入自动化测试" / "Run Benchmark") was visually
    indistinguishable from the page title "自动化测试" / "Benchmark",
    which made the button look like a static label. The new text
    starts with "▶ " and includes "[Enter]" so the affordance is
    obvious without hovering.
    """
    for code, expected_fragment in [
        ("zh_CN", "[Enter]"),
        ("en_US", "[Enter]"),
    ]:
        data = _load_locale(code)
        text = data["benchmark.enter_button"]
        assert "[Enter]" in text, (
            f"benchmark.enter_button in {code} must include '[Enter]' "
            f"to advertise the keyboard affordance, got {text!r}"
        )
        assert text.startswith("▶"), (
            f"benchmark.enter_button in {code} must start with the "
            f"play-arrow glyph to read as an action, got {text!r}"
        )


def test_benchmark_enter_button_differs_from_title() -> None:
    """The button text must not equal the page title in either locale.

    Regression guard for the original UX bug: in zh_CN both were
    "自动化测试" (the title) and "进入自动化测试" (the button) but
    rendered in the same colour family, so a static screenshot
    could not distinguish them. The new action prefix ("▶ ") plus
    "[Enter]" hint makes the difference obvious.
    """
    for code in ("zh_CN", "en_US"):
        data = _load_locale(code)
        assert data["benchmark.enter_button"] != data["benchmark.title"], (
            f"benchmark.enter_button and benchmark.title must differ "
            f"in {code}; otherwise the button looks like a static label."
        )


def test_benchmark_enter_hint_present_in_both_locales() -> None:
    """The keyboard/mouse hint key must exist and be non-empty in
    every locale. A missing key would silently fall back to the
    raw key string, which is the same kind of UX failure as the
    original bug."""
    for code in ("zh_CN", "en_US"):
        data = _load_locale(code)
        assert "benchmark.enter_hint" in data, (
            f"benchmark.enter_hint missing in {code}"
        )
        text = data["benchmark.enter_hint"].strip()
        assert text, f"benchmark.enter_hint in {code} must be non-empty"
        # The hint should be an instruction, not a description of
        # the page. Reject anything that is a duplicate of the
        # button or the title.
        assert text != data["benchmark.enter_button"]
        assert text != data["benchmark.title"]
