"""Tests for the lightweight i18n module."""

import pytest

from airwar.i18n import Translator, set_locale


class TestSetLocalePathTraversal:
    def test_set_locale_rejects_path_traversal(self):
        translator = Translator()
        with pytest.raises(ValueError):
            translator.set_locale("../../etc/passwd")

    def test_set_locale_rejects_directory_separator(self):
        translator = Translator()
        with pytest.raises(ValueError):
            translator.set_locale("foo/bar")

    def test_set_locale_accepts_alphanumeric_underscore(self):
        translator = Translator()
        # zh_CN is the default and is already loaded, but this still proves
        # the validator accepts the canonical form.
        translator.set_locale("zh_CN")
        assert translator.get_locale() == "zh_CN"

    def test_module_set_locale_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            set_locale("../../etc/passwd")

    def test_set_locale_rejects_non_string(self):
        translator = Translator()
        with pytest.raises(ValueError):
            translator.set_locale(None)  # type: ignore[arg-type]
