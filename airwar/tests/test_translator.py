"""Unit tests for the lightweight i18n Translator."""

import os
import tempfile

import pytest

from airwar.i18n import (
    DEFAULT_LOCALE,
    Translator,
    get_translator,
    reset_translator_for_tests,
    t,
)

# All i18n tests are pure-unit and fast — include in the smoke subset.
pytestmark = pytest.mark.smoke


@pytest.fixture
def isolated_translator():
    """Provide a Translator bound to a temp directory and reset the singleton."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write a minimal en_US catalog so the test does not depend on the
        # shipped locale files living next to the package.
        with open(os.path.join(tmpdir, "en_US.json"), "w", encoding="utf-8") as fh:
            fh.write('{"hello": "Hello, {name}!", "bye": "Goodbye"}')
        with open(os.path.join(tmpdir, "zh_CN.json"), "w", encoding="utf-8") as fh:
            fh.write('{"hello": "你好, {name}!", "bye": "再见"}')
        tr = Translator(locales_dir=tmpdir)
        yield tr
        reset_translator_for_tests(None)


def test_set_and_get_locale(isolated_translator):
    """set_locale should update the active locale; get_locale should return it."""
    assert isolated_translator.get_locale() == DEFAULT_LOCALE
    isolated_translator.set_locale("en_US")
    assert isolated_translator.get_locale() == "en_US"


def test_t_returns_translation_for_current_locale(isolated_translator):
    """t() should return the value from the active locale's catalog."""
    isolated_translator.set_locale("en_US")
    assert isolated_translator.t("bye") == "Goodbye"
    isolated_translator.set_locale("zh_CN")
    assert isolated_translator.t("bye") == "再见"


def test_t_falls_back_to_key_when_missing(isolated_translator, caplog):
    """Missing translations should return the key itself and log a warning."""
    with caplog.at_level("WARNING"):
        result = isolated_translator.t("not.a.real.key")
    assert result == "not.a.real.key"
    assert any("Missing translation" in rec.message for rec in caplog.records)


def test_t_supports_kwargs_string_formatting(isolated_translator):
    """t() should forward kwargs to str.format on the translation template."""
    isolated_translator.set_locale("en_US")
    assert isolated_translator.t("hello", name="Pilot") == "Hello, Pilot!"
    isolated_translator.set_locale("zh_CN")
    assert isolated_translator.t("hello", name="飞行员") == "你好, 飞行员!"


def test_singleton_t_helper_uses_module_translator():
    """The module-level t() and get_translator() should share a single instance."""
    reset_translator_for_tests(None)
    a = get_translator()
    b = get_translator()
    assert a is b
    # The singleton's default locale is the package default (zh_CN), which
    # keeps the shipped hardcoded-Chinese UI intact on first import.
    assert a.get_locale() == DEFAULT_LOCALE
    # The convenience t() helper should delegate to the same singleton.
    assert t("__definitely_missing__") == "__definitely_missing__"


def test_missing_key_warns_exactly_once(isolated_translator, caplog):
    """Repeated calls with the same missing key should warn only once."""
    with caplog.at_level("WARNING"):
        for _ in range(5):
            isolated_translator.t("missing.once.key")
    warnings = [r for r in caplog.records if "Missing translation" in r.message and "missing.once.key" in r.message]
    assert len(warnings) == 1


_CJK_RE = __import__("re").compile(r"[一-鿿]")


def test_en_us_tutorial_keys_have_no_cjk():
    """en_US tutorial stage translations must not contain CJK characters."""
    from airwar.config.tutorial.tutorial_stages import TUTORIAL_STAGES

    tr = Translator(default_locale="en_US")
    for stage in TUTORIAL_STAGES:
        if stage.title_key:
            assert not _CJK_RE.search(tr.t(stage.title_key)), f"CJK in en_US {stage.title_key}"
        if stage.objective_key:
            assert not _CJK_RE.search(tr.t(stage.objective_key)), f"CJK in en_US {stage.objective_key}"
        for key in stage.instructions_keys:
            assert not _CJK_RE.search(tr.t(key)), f"CJK in en_US {key}"
