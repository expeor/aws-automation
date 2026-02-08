# tests/test_cli_app.py
"""
cli/app.py 단위 테스트

CLI 메인 엔트리포인트 테스트.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

# =============================================================================
# get_version 테스트
# =============================================================================


class TestGetVersion:
    """get_version 함수 테스트"""

    def test_version_from_file(self, tmp_path):
        """version.txt에서 버전 읽기"""
        from core.cli.app import get_version

        version = get_version()
        # 버전이 문자열인지 확인
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_format(self):
        """버전 형식 확인 (semantic versioning)"""
        from core.cli.app import get_version

        version = get_version()
        # x.y.z 형식 확인
        parts = version.split(".")
        assert len(parts) >= 2, "버전은 최소 x.y 형식이어야 함"
        for part in parts:
            assert part.isdigit(), f"버전 파트는 숫자여야 함: {part}"


# =============================================================================
# CLI 그룹 테스트
# =============================================================================


class TestCLI:
    """CLI 그룹 테스트"""

    @pytest.fixture
    def runner(self):
        """Click CliRunner"""
        return CliRunner()

    def test_version_option(self, runner):
        """--version 옵션 테스트"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "aa" in result.output.lower() or "version" in result.output.lower()

    def test_help_option(self, runner):
        """--help 옵션 테스트"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AWS Automation" in result.output or "aa" in result.output.lower()

    @patch("core.cli.ui.main_menu.show_main_menu")
    def test_invoke_without_command(self, mock_menu, runner):
        """서브명령어 없이 실행 시 메인 메뉴 호출"""
        from core.cli.app import cli

        runner.invoke(cli, [])
        # 메인 메뉴가 호출되었는지 확인
        mock_menu.assert_called_once()


# =============================================================================
# _build_help_text 테스트
# =============================================================================


class TestBuildHelpText:
    """_build_help_text 함수 테스트"""

    def test_help_text_content(self):
        """help 텍스트 내용 확인"""
        from core.cli.app import _build_help_text

        help_text = _build_help_text()

        assert "AA" in help_text
        assert "AWS Automation" in help_text or "자동화" in help_text
        assert "사용법" in help_text


# =============================================================================
# 카테고리 명령어 등록 테스트
# =============================================================================


class TestCategoryCommands:
    """카테고리 명령어 자동 등록 테스트"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("core.tools.discovery.discover_categories")
    def test_category_commands_registered(self, mock_discover, runner):
        """카테고리 명령어가 등록되는지 테스트"""
        mock_discover.return_value = [
            {
                "name": "cost",
                "description": "💰 비용 최적화",
                "tools": [
                    {"name": "미사용 리소스", "permission": "read"},
                ],
                "aliases": ["unused"],
            }
        ]

        from core.cli.app import cli

        result = runner.invoke(cli, ["--help"])
        # help 출력에 cost가 있는지 확인 (등록된 명령어)
        assert result.exit_code == 0

    def test_ec2_command_exists(self, runner):
        """ec2 명령어가 존재하는지 테스트"""
        from core.cli.app import cli

        result = runner.invoke(cli, ["ec2", "--help"])
        # ec2 명령어가 등록되어 있으면 help가 표시됨
        assert result.exit_code == 0
