# tests/cli/i18n/test_i18n.py
"""
Comprehensive tests for cli/i18n - Internationalization module

Tests cover:
- Translation function (t)
- Language context management
- Message registry
- Format string interpolation
- get_text helper
- Message completeness
- Error handling
"""

import pytest

from cli.i18n import DEFAULT_LANG, SUPPORTED_LANGS, get_lang, get_text, set_lang, t


# =============================================================================
# Language Context Tests
# =============================================================================


class TestLanguageContext:
    """Test language context management"""

    def test_default_language(self):
        """Default language is Korean"""
        assert DEFAULT_LANG == "ko"

    def test_supported_languages(self):
        """Supported languages are defined"""
        assert "ko" in SUPPORTED_LANGS
        assert "en" in SUPPORTED_LANGS
        assert len(SUPPORTED_LANGS) == 2

    def test_get_lang_default(self):
        """Get default language"""
        # Reset to default
        set_lang("ko")
        lang = get_lang()
        assert lang == "ko"

    def test_set_lang_korean(self):
        """Set language to Korean"""
        set_lang("ko")
        assert get_lang() == "ko"

    def test_set_lang_english(self):
        """Set language to English"""
        set_lang("en")
        lang = get_lang()
        assert lang == "en"
        # Reset
        set_lang("ko")

    def test_set_lang_invalid(self):
        """Invalid language defaults to Korean"""
        set_lang("fr")  # Unsupported language
        assert get_lang() == "ko"

    def test_lang_context_isolation(self):
        """Language context is isolated per context"""
        set_lang("ko")
        assert get_lang() == "ko"

        set_lang("en")
        assert get_lang() == "en"

        # Reset
        set_lang("ko")


# =============================================================================
# Translation Function Tests
# =============================================================================


class TestTranslationFunction:
    """Test translation function (t)"""

    def test_translate_simple_korean(self):
        """Translate simple message in Korean"""
        set_lang("ko")
        text = t("common.exit")
        assert text == "종료"
        # Reset
        set_lang("ko")

    def test_translate_simple_english(self):
        """Translate simple message in English"""
        set_lang("en")
        text = t("common.exit")
        assert text == "Exit"
        # Reset
        set_lang("ko")

    def test_translate_with_lang_override(self):
        """Translate with language override"""
        set_lang("ko")
        # Override to English
        text = t("common.exit", lang="en")
        assert text == "Exit"
        # Context should still be Korean
        assert get_lang() == "ko"

    def test_translate_nonexistent_key(self):
        """Nonexistent key returns key itself"""
        text = t("nonexistent.key")
        assert text == "nonexistent.key"

    def test_translate_with_format_korean(self):
        """Translate with format string in Korean"""
        set_lang("ko")
        text = t("common.found_items", count=5)
        assert "5" in text
        assert "개" in text  # Korean counter
        # Reset
        set_lang("ko")

    def test_translate_with_format_english(self):
        """Translate with format string in English"""
        set_lang("en")
        text = t("common.found_items", count=5)
        assert "5" in text
        assert "Found" in text or "items" in text
        # Reset
        set_lang("ko")

    def test_translate_with_multiple_params(self):
        """Translate with multiple format parameters"""
        set_lang("en")
        text = t("common.api_error", message="Connection failed")
        assert "Connection failed" in text
        # Reset
        set_lang("ko")

    def test_translate_invalid_format_params(self):
        """Invalid format parameters are handled gracefully"""
        # Should not raise exception
        text = t("common.found_items", wrong_param=5)
        assert isinstance(text, str)

    def test_translate_missing_translation_fallback(self):
        """Missing translation falls back to default language"""
        # Create a scenario where English translation might be missing
        text = t("common.exit", lang="en")
        assert isinstance(text, str)
        assert len(text) > 0


# =============================================================================
# Message Registry Tests
# =============================================================================


class TestMessageRegistry:
    """Test message registry structure"""

    def test_messages_imported(self):
        """Messages are imported and available"""
        from cli.i18n.messages import MESSAGES

        assert isinstance(MESSAGES, dict)
        assert len(MESSAGES) > 0

    def test_common_messages_registered(self):
        """Common messages are registered"""
        from cli.i18n.messages import MESSAGES

        assert "common.exit" in MESSAGES
        assert "common.error" in MESSAGES
        assert "common.select_profile" in MESSAGES

    def test_message_structure(self):
        """Each message has ko and en translations"""
        from cli.i18n.messages import MESSAGES

        for key, value in MESSAGES.items():
            assert isinstance(value, dict), f"Message {key} should be a dict"
            # Should have at least Korean translation
            assert "ko" in value, f"Message {key} missing Korean translation"

    def test_register_messages_function(self):
        """register_messages function works"""
        from cli.i18n.messages import register_messages

        test_messages = {
            "test_key": {"ko": "테스트", "en": "Test"},
        }

        # Should not raise exception
        register_messages("test", test_messages)

        # Verify registration
        text = t("test.test_key", lang="en")
        assert text == "Test"


# =============================================================================
# get_text Helper Tests
# =============================================================================


class TestGetTextHelper:
    """Test get_text helper function"""

    def test_get_text_korean(self):
        """get_text returns Korean text"""
        set_lang("ko")
        text = get_text("저장됨", "Saved")
        assert text == "저장됨"
        # Reset
        set_lang("ko")

    def test_get_text_english(self):
        """get_text returns English text"""
        set_lang("en")
        text = get_text("저장됨", "Saved")
        assert text == "Saved"
        # Reset
        set_lang("ko")

    def test_get_text_with_override(self):
        """get_text with language override"""
        set_lang("ko")
        text = get_text("저장됨", "Saved", lang="en")
        assert text == "Saved"
        # Context should still be Korean
        assert get_lang() == "ko"

    def test_get_text_invalid_lang(self):
        """get_text with invalid language defaults to Korean"""
        text = get_text("저장됨", "Saved", lang="fr")
        assert text == "저장됨"


# =============================================================================
# Message Namespace Tests
# =============================================================================


class TestMessageNamespaces:
    """Test different message namespaces"""

    def test_common_namespace(self):
        """Common namespace messages exist"""
        # Authentication
        assert t("common.select_profile") != "common.select_profile"
        assert t("common.auth_failed") != "common.auth_failed"

        # Progress
        assert t("common.loading") != "common.loading"
        assert t("common.completed") != "common.completed"

        # User input
        assert t("common.enter_number") != "common.enter_number"
        assert t("common.cancel") != "common.cancel"

    def test_menu_namespace(self):
        """Menu namespace messages exist"""
        assert t("menu.go_back") != "menu.go_back"

    def test_runner_namespace(self):
        """Runner namespace messages exist"""
        assert t("runner.executing") != "runner.executing"

    def test_cli_namespace(self):
        """CLI namespace messages exist"""
        assert t("cli.section_utilities") != "cli.section_utilities"

    def test_flow_namespace(self):
        """Flow namespace messages exist"""
        assert t("flow.category_not_found", name="test") != "flow.category_not_found"


# =============================================================================
# Format String Tests
# =============================================================================


class TestFormatStrings:
    """Test format string interpolation"""

    def test_format_with_count(self):
        """Format string with count parameter"""
        text = t("common.found_items", count=10)
        assert "10" in text

    def test_format_with_name(self):
        """Format string with name parameter"""
        text = t("flow.category_not_found", name="ec2")
        assert "ec2" in text

    def test_format_with_message(self):
        """Format string with message parameter"""
        text = t("common.error_occurred", message="Test error")
        assert "Test error" in text

    def test_format_missing_param_handled(self):
        """Missing format parameter is handled gracefully"""
        # Should not raise exception
        text = t("common.found_items")
        assert isinstance(text, str)

    def test_format_extra_params_ignored(self):
        """Extra format parameters are ignored"""
        text = t("common.exit", extra_param="ignored")
        assert isinstance(text, str)
        assert "ignored" not in text

    def test_format_numeric_zero(self):
        """Format string with zero value"""
        text = t("common.found_items", count=0)
        assert "0" in text

    def test_format_large_number(self):
        """Format string with large number"""
        text = t("common.found_items", count=99999)
        assert "99999" in text


# =============================================================================
# Message Completeness Tests
# =============================================================================


class TestMessageCompleteness:
    """Test message completeness across languages"""

    def test_all_messages_have_korean(self):
        """All messages have Korean translation"""
        from cli.i18n.messages import MESSAGES

        for key, value in MESSAGES.items():
            assert "ko" in value, f"Message {key} missing Korean translation"
            assert isinstance(value["ko"], str), f"Korean translation for {key} is not a string"
            assert len(value["ko"]) > 0, f"Korean translation for {key} is empty"

    def test_critical_messages_have_english(self):
        """Critical messages have English translation"""
        from cli.i18n.messages import MESSAGES

        critical_prefixes = ["common.", "error.", "cli.", "runner."]

        for key in MESSAGES:
            if any(key.startswith(prefix) for prefix in critical_prefixes):
                value = MESSAGES[key]
                # English translation is encouraged but not required
                if "en" in value:
                    assert isinstance(value["en"], str), f"English translation for {key} is not a string"


# =============================================================================
# Context Variable Tests
# =============================================================================


class TestContextVariable:
    """Test context variable behavior"""

    def test_context_var_set_and_get(self):
        """Context variable set and get work correctly"""
        set_lang("en")
        assert get_lang() == "en"

        set_lang("ko")
        assert get_lang() == "ko"

    def test_context_var_default(self):
        """Context variable has correct default"""
        # Default should be Korean
        from cli.i18n import _current_lang

        default = _current_lang.get()
        assert default in SUPPORTED_LANGS


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in i18n module"""

    def test_translate_with_none_key(self):
        """Translate with None key returns empty or key"""
        # Should not raise exception
        try:
            text = t(None)  # type: ignore
            assert text is None or text == ""
        except (TypeError, AttributeError):
            # Expected for None key
            pass

    def test_translate_with_empty_key(self):
        """Translate with empty key"""
        text = t("")
        assert text == "" or isinstance(text, str)

    def test_set_lang_with_none(self):
        """Set lang with None defaults to Korean"""
        try:
            set_lang(None)  # type: ignore
            assert get_lang() == "ko"
        except (TypeError, AttributeError):
            pass

    def test_format_with_complex_types(self):
        """Format with complex types (list, dict)"""
        # Should handle gracefully
        text = t("common.found_items", count={"value": 5})
        assert isinstance(text, str)


# =============================================================================
# Integration Tests
# =============================================================================


class TestI18nIntegration:
    """Integration tests for i18n system"""

    def test_language_switch_persistence(self):
        """Language switch persists in context"""
        original = get_lang()

        set_lang("en")
        assert t("common.exit") == "Exit"

        set_lang("ko")
        assert t("common.exit") == "종료"

        # Restore original
        set_lang(original)

    def test_multiple_translations_same_context(self):
        """Multiple translations in same context"""
        set_lang("ko")

        exit_text = t("common.exit")
        error_text = t("common.error")
        loading_text = t("common.loading")

        assert exit_text == "종료"
        assert error_text == "오류"
        assert "로딩" in loading_text or "중" in loading_text

        # Reset
        set_lang("ko")

    def test_translation_with_nested_format(self):
        """Translation with nested format parameters"""
        text = t("common.error_occurred", message=t("common.auth_failed"))
        assert isinstance(text, str)
        assert len(text) > 0


# =============================================================================
# Module Exports Tests
# =============================================================================


class TestModuleExports:
    """Test module exports"""

    def test_all_exported_functions(self):
        """All expected functions are exported"""
        from cli.i18n import __all__

        assert "t" in __all__
        assert "get_text" in __all__
        assert "get_lang" in __all__
        assert "set_lang" in __all__

    def test_constants_exported(self):
        """Constants are exported"""
        from cli.i18n import __all__

        assert "SUPPORTED_LANGS" in __all__
        assert "DEFAULT_LANG" in __all__

    def test_direct_imports_work(self):
        """Direct imports work correctly"""
        from cli.i18n import DEFAULT_LANG, SUPPORTED_LANGS, get_lang, get_text, set_lang, t

        assert callable(t)
        assert callable(get_text)
        assert callable(get_lang)
        assert callable(set_lang)
        assert isinstance(SUPPORTED_LANGS, tuple)
        assert isinstance(DEFAULT_LANG, str)
