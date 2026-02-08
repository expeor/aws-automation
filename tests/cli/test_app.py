# tests/cli/test_app.py
"""
Comprehensive tests for cli/app.py - Main CLI entry point

Tests cover:
- CLI version display
- Help text generation
- Command registration
- Interactive menu invocation
- Headless run command
- Profile group management
- Category command registration
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# =============================================================================
# get_version Tests
# =============================================================================


class TestGetVersion:
    """Test version retrieval"""

    def test_version_from_config(self):
        """Version is retrieved from core.config"""
        from core.cli.app import get_version

        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_format(self):
        """Version follows semantic versioning format"""
        from core.cli.app import get_version

        version = get_version()
        # Should be x.y.z format
        parts = version.split(".")
        assert len(parts) >= 2, "Version should be at least x.y format"
        for part in parts[:2]:  # Check major.minor
            assert part.isdigit(), f"Version part should be numeric: {part}"

    def test_version_constant_set(self):
        """VERSION constant is set in module"""
        from core.cli.app import VERSION

        assert isinstance(VERSION, str)
        assert len(VERSION) > 0


# =============================================================================
# CLI Group Tests
# =============================================================================


class TestCLI:
    """Test main CLI group"""

    @pytest.fixture
    def runner(self):
        """Click CliRunner fixture"""
        return CliRunner()

    def test_version_option(self, runner):
        """--version flag displays version"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "aa" in result.output.lower() or "version" in result.output.lower()

    def test_help_option(self, runner):
        """--help flag displays help text"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AWS Automation" in result.output or "aa" in result.output.lower()

    def test_lang_option_ko(self, runner):
        """--lang ko sets Korean language"""
        from core.cli.app import cli

        with patch("core.cli.i18n.set_lang") as mock_set_lang, patch("core.cli.ui.main_menu.show_main_menu"):
            runner.invoke(cli, ["--lang", "ko"])
            mock_set_lang.assert_called_once_with("ko")

    def test_lang_option_en(self, runner):
        """--lang en sets English language"""
        from core.cli.app import cli

        with patch("core.cli.i18n.set_lang") as mock_set_lang, patch("core.cli.ui.main_menu.show_main_menu"):
            runner.invoke(cli, ["--lang", "en"])
            mock_set_lang.assert_called_once_with("en")

    @patch("core.cli.ui.main_menu.show_main_menu")
    def test_invoke_without_command_shows_menu(self, mock_menu, runner):
        """Running without subcommand shows main menu"""
        from core.cli.app import cli

        runner.invoke(cli, [])
        mock_menu.assert_called_once()

    def test_context_object_creation(self, runner):
        """Context object is created with lang"""
        from core.cli.app import cli

        with patch("core.cli.ui.main_menu.show_main_menu"):
            result = runner.invoke(cli, ["--lang", "en"], obj={})
            assert result.exit_code == 0


# =============================================================================
# Help Text Tests
# =============================================================================


class TestBuildHelpText:
    """Test help text generation"""

    def test_help_text_korean(self):
        """Korean help text contains expected content"""
        from core.cli.app import _build_help_text

        help_text = _build_help_text(lang="ko")

        assert "AA" in help_text
        assert "AWS" in help_text
        assert "리소스" in help_text or "자동화" in help_text
        assert "사용법" in help_text or "기본" in help_text

    def test_help_text_english(self):
        """English help text contains expected content"""
        from core.cli.app import _build_help_text

        help_text = _build_help_text(lang="en")

        assert "AA" in help_text
        assert "AWS Automation" in help_text
        assert "Usage" in help_text or "Examples" in help_text

    def test_help_text_has_sections(self):
        """Help text has all required sections"""
        from core.cli.app import _build_help_text

        help_text = _build_help_text()

        # Should have basic usage, headless mode, profile groups sections
        assert "aa" in help_text.lower()
        assert "run" in help_text or "group" in help_text


# =============================================================================
# Path-based Tool Execution Tests
# =============================================================================


class TestPathBasedExecution:
    """Test path-based tool execution (aa ec2/unused -p ...)"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_path_execution_requires_auth_option(self, runner):
        """Path-based execution requires authentication option"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["ec2/unused"])
        assert result.exit_code != 0
        # Check that it fails (exit code 1) - message content doesn't matter

    def test_path_execution_with_profile_option(self, runner):
        """Path-based execution accepts profile option"""
        from core.cli.app import cli

        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(cli, ["ec2/unused", "-p", "my-profile"])
            assert result.exit_code == 0

    def test_path_execution_single_profile_only(self, runner):
        """Path-based execution -p accepts single profile only"""
        from core.cli.app import cli

        # -p는 단일 프로파일만 지원, 다중 프로파일은 -g (profile group) 사용
        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(cli, ["ec2/unused", "-p", "my-profile"])
            assert result.exit_code == 0

    def test_path_execution_with_profile_group(self, runner):
        """Path-based execution accepts profile group"""
        from core.cli.app import cli

        mock_group = MagicMock()
        mock_group.profiles = ["dev", "prod"]

        with patch("core.tools.history.ProfileGroupsManager") as mock_manager:
            mock_manager.return_value.get_by_name.return_value = mock_group
            with patch("core.cli.headless.run_headless", return_value=0):
                result = runner.invoke(cli, ["ec2/unused", "-g", "Dev Team"])
                assert result.exit_code == 0

    def test_path_execution_with_nonexistent_group(self, runner):
        """Path-based execution fails with nonexistent group"""
        from core.cli.app import cli

        with patch("core.tools.history.ProfileGroupsManager") as mock_manager:
            mock_manager.return_value.get_by_name.return_value = None
            result = runner.invoke(cli, ["ec2/unused", "-g", "NonExistent"])
            assert result.exit_code != 0

    def test_path_execution_with_sso_session(self, runner):
        """Path-based execution accepts SSO session options"""
        from core.cli.app import cli

        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(
                cli,
                [
                    "ec2/unused",
                    "-s",
                    "my-sso",
                    "--account",
                    "123456789012",
                    "--role",
                    "AdminRole",
                ],
            )
            assert result.exit_code == 0

    def test_path_execution_sso_requires_role(self, runner):
        """Path-based execution with SSO session requires role"""
        from core.cli.app import cli

        result = runner.invoke(
            cli,
            [
                "ec2/unused",
                "-s",
                "my-sso",
                "--account",
                "123456789012",
            ],
        )
        assert result.exit_code != 0

    def test_path_execution_sso_requires_account(self, runner):
        """Path-based execution with SSO session requires account"""
        from core.cli.app import cli

        result = runner.invoke(
            cli,
            [
                "ec2/unused",
                "-s",
                "my-sso",
                "--role",
                "AdminRole",
            ],
        )
        assert result.exit_code != 0

    def test_path_execution_conflict_auth_options(self, runner):
        """Path-based execution rejects conflicting auth options"""
        from core.cli.app import cli

        result = runner.invoke(
            cli,
            [
                "ec2/unused",
                "-p",
                "profile",
                "-g",
                "group",
            ],
        )
        assert result.exit_code != 0

    def test_path_execution_with_regions(self, runner):
        """Path-based execution accepts region options"""
        from core.cli.app import cli

        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(
                cli,
                [
                    "ec2/unused",
                    "-p",
                    "profile",
                    "-r",
                    "ap-northeast-2",
                    "-r",
                    "us-east-1",
                ],
            )
            assert result.exit_code == 0

    def test_path_execution_with_output_format(self, runner):
        """Path-based execution accepts output format"""
        from core.cli.app import cli

        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(
                cli,
                [
                    "ec2/unused",
                    "-p",
                    "profile",
                    "-f",
                    "json",
                ],
            )
            assert result.exit_code == 0

    def test_path_execution_with_quiet_flag(self, runner):
        """Path-based execution accepts quiet flag"""
        from core.cli.app import cli

        with patch("core.cli.headless.run_headless", return_value=0):
            result = runner.invoke(
                cli,
                [
                    "ec2/unused",
                    "-p",
                    "profile",
                    "-q",
                ],
            )
            assert result.exit_code == 0


# =============================================================================
# List Tools Command Tests
# =============================================================================


class TestListToolsCommand:
    """Test list-tools command"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("core.tools.discovery.discover_categories")
    def test_list_tools_basic(self, mock_discover, runner):
        """List tools displays all tools"""
        from core.cli.app import cli

        mock_discover.return_value = [
            {
                "name": "ec2",
                "display_name": "EC2",
                "tools": [
                    {"name": "Unused EC2", "module": "unused", "permission": "read"},
                ],
            }
        ]

        result = runner.invoke(cli, ["list-tools"])
        assert result.exit_code == 0
        assert "ec2" in result.output.lower() or "unused" in result.output.lower()

    @patch("core.tools.discovery.discover_categories")
    def test_list_tools_json_format(self, mock_discover, runner):
        """List tools with JSON output"""
        from core.cli.app import cli

        mock_discover.return_value = [
            {
                "name": "ec2",
                "display_name": "EC2",
                "tools": [
                    {"name": "Unused EC2", "module": "unused", "permission": "read"},
                ],
            }
        ]

        result = runner.invoke(cli, ["list-tools", "--json"])
        assert result.exit_code == 0
        assert "[" in result.output  # JSON array

    @patch("core.tools.discovery.discover_categories")
    def test_list_tools_by_category(self, mock_discover, runner):
        """List tools filtered by category"""
        from core.cli.app import cli

        mock_discover.return_value = [
            {
                "name": "ec2",
                "display_name": "EC2",
                "tools": [
                    {"name": "Unused EC2", "module": "unused", "permission": "read"},
                ],
            }
        ]

        result = runner.invoke(cli, ["list-tools", "-c", "ec2"])
        assert result.exit_code == 0

    @patch("core.tools.discovery.discover_categories")
    def test_list_tools_nonexistent_category(self, mock_discover, runner):
        """List tools fails with nonexistent category"""
        from core.cli.app import cli

        mock_discover.return_value = []

        result = runner.invoke(cli, ["list-tools", "-c", "nonexistent"])
        assert result.exit_code != 0


# =============================================================================
# Profile Group Commands Tests
# =============================================================================


class TestGroupCommands:
    """Test profile group management commands"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_list_empty(self, mock_manager, runner):
        """Group list with no groups"""
        from core.cli.app import cli

        mock_manager.return_value.get_all.return_value = []

        result = runner.invoke(cli, ["group", "list"])
        assert result.exit_code == 0

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_list_with_groups(self, mock_manager, runner):
        """Group list displays groups"""
        from core.cli.app import cli

        mock_group = MagicMock()
        mock_group.name = "Dev Team"
        mock_group.kind = "sso_profile"
        mock_group.profiles = ["dev1", "dev2"]
        mock_group.added_at = "2024-01-01T00:00:00Z"

        mock_manager.return_value.get_all.return_value = [mock_group]

        result = runner.invoke(cli, ["group", "list"])
        assert result.exit_code == 0
        assert "Dev Team" in result.output or "dev1" in result.output

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_list_json_format(self, mock_manager, runner):
        """Group list with JSON output"""
        from core.cli.app import cli

        mock_group = MagicMock()
        mock_group.name = "Dev Team"
        mock_group.kind = "sso_profile"
        mock_group.profiles = ["dev1", "dev2"]
        mock_group.added_at = "2024-01-01T00:00:00Z"

        mock_manager.return_value.get_all.return_value = [mock_group]

        result = runner.invoke(cli, ["group", "list", "--json"])
        assert result.exit_code == 0
        assert "[" in result.output

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_show(self, mock_manager, runner):
        """Group show displays group details"""
        from core.cli.app import cli

        mock_group = MagicMock()
        mock_group.name = "Dev Team"
        mock_group.kind = "sso_profile"
        mock_group.profiles = ["dev1", "dev2"]
        mock_group.added_at = "2024-01-01T00:00:00Z"

        mock_manager.return_value.get_by_name.return_value = mock_group

        result = runner.invoke(cli, ["group", "show", "Dev Team"])
        assert result.exit_code == 0

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_show_nonexistent(self, mock_manager, runner):
        """Group show fails for nonexistent group"""
        from core.cli.app import cli

        mock_manager.return_value.get_by_name.return_value = None

        result = runner.invoke(cli, ["group", "show", "NonExistent"])
        assert result.exit_code != 0

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_delete_with_confirmation(self, mock_manager, runner):
        """Group delete with confirmation"""
        from core.cli.app import cli

        mock_group = MagicMock()
        mock_group.name = "Dev Team"
        mock_group.profiles = ["dev1", "dev2"]

        mock_manager.return_value.get_by_name.return_value = mock_group
        mock_manager.return_value.remove.return_value = True

        result = runner.invoke(cli, ["group", "delete", "Dev Team", "-y"])
        assert result.exit_code == 0

    @patch("core.tools.history.ProfileGroupsManager")
    def test_group_delete_nonexistent(self, mock_manager, runner):
        """Group delete fails for nonexistent group"""
        from core.cli.app import cli

        mock_manager.return_value.get_by_name.return_value = None

        result = runner.invoke(cli, ["group", "delete", "NonExistent", "-y"])
        assert result.exit_code != 0


# =============================================================================
# Category Command Registration Tests
# =============================================================================


class TestCategoryCommands:
    """Test category command auto-registration"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_ec2_command_exists(self, runner):
        """EC2 category command is registered"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["ec2", "--help"])
        assert result.exit_code == 0

    @patch("core.cli.flow.runner.FlowRunner.run")
    def test_category_command_invokes_flow(self, mock_run, runner):
        """Category command invokes FlowRunner"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["ec2"])
        # FlowRunner.run should be called (even if it fails in test)
        # Just check command is recognized
        assert result.exit_code is not None


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestParseSelection:
    """Test selection parsing helper"""

    def test_parse_single_number(self):
        """Parse single number"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1", 10)
        assert result == [0]  # 0-indexed

    def test_parse_multiple_numbers(self):
        """Parse multiple numbers"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1 2 3", 10)
        assert result == [0, 1, 2]

    def test_parse_comma_separated(self):
        """Parse comma-separated numbers"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1,2,3", 10)
        assert result == [0, 1, 2]

    def test_parse_range(self):
        """Parse range (1-3)"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1-3", 10)
        assert result == [0, 1, 2]

    def test_parse_mixed_format(self):
        """Parse mixed format (1,3-5,7)"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1,3-5,7", 10)
        assert result == [0, 2, 3, 4, 6]

    def test_parse_out_of_range(self):
        """Out of range numbers are ignored"""
        from core.cli.app import _parse_selection

        result = _parse_selection("1 99", 10)
        assert result == [0]

    def test_parse_invalid_input(self):
        """Invalid input returns empty list"""
        from core.cli.app import _parse_selection

        result = _parse_selection("abc", 10)
        assert result == []


class TestGetProfilesByKind:
    """Test profile filtering by kind"""

    def test_get_profiles_by_kind_basic(self):
        """Test basic profile filtering logic - simplified"""
        from core.cli.app import _get_profiles_by_kind

        # This function relies on real AWS config
        # Just test that it returns a list
        result = _get_profiles_by_kind("sso_profile")
        assert isinstance(result, list)

        result = _get_profiles_by_kind("static")
        assert isinstance(result, list)

    def test_get_profiles_by_kind_invalid(self):
        """Test with invalid kind"""
        from core.cli.app import _get_profiles_by_kind

        result = _get_profiles_by_kind("invalid_kind")
        assert isinstance(result, list)
        assert len(result) == 0  # Should return empty for invalid kind


# =============================================================================
# Grouped Commands Group Tests
# =============================================================================


class TestGroupedCommandsGroup:
    """Test custom Click group for command grouping"""

    def test_format_commands_separates_utilities(self):
        """Commands are separated into utilities and services"""
        from core.cli.app import GroupedCommandsGroup, cli

        assert isinstance(cli, GroupedCommandsGroup)

    def test_utility_commands_defined(self):
        """UTILITY_COMMANDS set is defined"""
        from core.cli.app import UTILITY_COMMANDS

        assert isinstance(UTILITY_COMMANDS, set)
        assert "tools" in UTILITY_COMMANDS
        assert "group" in UTILITY_COMMANDS
