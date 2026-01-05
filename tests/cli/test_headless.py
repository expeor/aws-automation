"""
tests/cli/test_headless.py - cli/headless.py 테스트

Headless CLI Runner 단위 테스트.
"""

from unittest.mock import MagicMock, patch

import pytest

from cli.headless import HeadlessConfig, HeadlessRunner, run_headless


class TestHeadlessConfig:
    """HeadlessConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
        )

        assert config.category == "ec2"
        assert config.tool_module == "ebs_audit"
        assert config.profile == "test-profile"
        assert config.regions == []
        assert config.format == "console"
        assert config.output is None
        assert config.quiet is False

    def test_custom_values(self):
        """커스텀 값 설정"""
        config = HeadlessConfig(
            category="vpc",
            tool_module="nat_audit",
            profile="my-profile",
            regions=["ap-northeast-2", "us-east-1"],
            format="json",
            output="/tmp/output.json",
            quiet=True,
        )

        assert config.category == "vpc"
        assert config.tool_module == "nat_audit"
        assert config.profile == "my-profile"
        assert config.regions == ["ap-northeast-2", "us-east-1"]
        assert config.format == "json"
        assert config.output == "/tmp/output.json"
        assert config.quiet is True


class TestHeadlessRunner:
    """HeadlessRunner 테스트"""

    @pytest.fixture
    def basic_config(self):
        """기본 테스트 설정"""
        return HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2"],
        )

    def test_init(self, basic_config):
        """초기화 테스트"""
        runner = HeadlessRunner(basic_config)
        assert runner.config == basic_config
        assert runner._ctx is None

    @patch("cli.headless.console")
    def test_load_tool_not_found(self, mock_console, basic_config):
        """도구를 찾을 수 없을 때"""
        runner = HeadlessRunner(basic_config)

        with patch("cli.headless.HeadlessRunner._load_tool") as mock_load:
            mock_load.return_value = None
            result = runner.run()

        assert result == 1

    def test_build_context(self, basic_config):
        """ExecutionContext 구성 테스트"""
        runner = HeadlessRunner(basic_config)

        tool_meta = {
            "name": "EBS Audit",
            "description": "EBS 볼륨 감사",
            "permission": "read",
            "supports_single_region_only": False,
            "supports_single_account_only": False,
            "is_global": False,
        }

        ctx = runner._build_context(tool_meta)

        assert ctx.category == "ec2"
        assert ctx.tool.name == "EBS Audit"
        assert ctx.tool.description == "EBS 볼륨 감사"
        assert ctx.tool.permission == "read"
        assert ctx.tool.supports_single_region_only is False

    @patch("cli.headless.console")
    def test_setup_regions_single(self, mock_console, basic_config):
        """단일 리전 설정"""
        runner = HeadlessRunner(basic_config)

        # Context 설정
        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_regions()

        assert result is True
        assert runner._ctx.regions == ["ap-northeast-2"]

    @patch("cli.headless.console")
    def test_setup_regions_multiple(self, mock_console):
        """다중 리전 설정"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2", "us-east-1", "eu-west-1"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_regions()

        assert result is True
        assert runner._ctx.regions == ["ap-northeast-2", "us-east-1", "eu-west-1"]

    @patch("cli.headless.console")
    def test_setup_regions_all(self, mock_console):
        """전체 리전 설정"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["all"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_regions()

        assert result is True
        assert len(runner._ctx.regions) > 10  # 많은 리전이 설정되어야 함

    @patch("cli.headless.console")
    def test_setup_regions_pattern(self, mock_console):
        """리전 패턴 설정"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-*"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_regions()

        assert result is True
        assert all(r.startswith("ap-") for r in runner._ctx.regions)

    @patch("cli.headless.console")
    def test_setup_regions_duplicates_removed(self, mock_console):
        """중복 리전 제거"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2", "ap-northeast-2", "us-east-1"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_regions()

        assert result is True
        assert runner._ctx.regions == ["ap-northeast-2", "us-east-1"]

    @patch("cli.headless.console")
    def test_keyboard_interrupt(self, mock_console, basic_config):
        """키보드 인터럽트 처리"""
        runner = HeadlessRunner(basic_config)

        with patch.object(runner, "_load_tool", side_effect=KeyboardInterrupt):
            result = runner.run()

        assert result == 130

    @patch("cli.headless.console")
    def test_unexpected_exception(self, mock_console, basic_config):
        """예상치 못한 예외 처리"""
        runner = HeadlessRunner(basic_config)

        with patch.object(runner, "_load_tool", side_effect=ValueError("test error")):
            result = runner.run()

        assert result == 1


class TestRunHeadless:
    """run_headless 함수 테스트"""

    @patch("cli.headless.console")
    def test_invalid_tool_path_no_slash(self, mock_console):
        """잘못된 도구 경로 (슬래시 없음)"""
        result = run_headless(
            tool_path="invalid",
            profile="test",
            regions=["ap-northeast-2"],
        )
        assert result == 1

    @patch("cli.headless.console")
    def test_invalid_tool_path_too_many_parts(self, mock_console):
        """잘못된 도구 경로 (너무 많은 부분)"""
        result = run_headless(
            tool_path="a/b/c",
            profile="test",
            regions=["ap-northeast-2"],
        )
        assert result == 1

    @patch("cli.headless.HeadlessRunner.run")
    def test_valid_tool_path(self, mock_run):
        """유효한 도구 경로"""
        mock_run.return_value = 0

        result = run_headless(
            tool_path="ec2/ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2"],
        )

        assert result == 0
        mock_run.assert_called_once()

    @patch("cli.headless.HeadlessRunner.run")
    def test_default_region(self, mock_run):
        """기본 리전 설정"""
        mock_run.return_value = 0

        run_headless(
            tool_path="ec2/ebs_audit",
            profile="test-profile",
            regions=[],
        )

        # HeadlessRunner가 생성되었는지 확인
        mock_run.assert_called_once()

    @patch("cli.headless.HeadlessRunner.run")
    def test_with_all_options(self, mock_run):
        """모든 옵션 설정"""
        mock_run.return_value = 0

        result = run_headless(
            tool_path="ec2/ebs_audit",
            profile="my-profile",
            regions=["ap-northeast-2", "us-east-1"],
            format="json",
            output="/tmp/output.json",
            quiet=True,
        )

        assert result == 0


class TestHeadlessRunnerAuth:
    """HeadlessRunner 인증 관련 테스트"""

    @pytest.fixture
    def basic_config(self):
        """기본 테스트 설정"""
        return HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2"],
        )

    @patch("cli.headless.console")
    @patch("core.auth.config.load_config")
    def test_setup_auth_profile_not_found(self, mock_load_config, mock_console, basic_config):
        """프로파일을 찾을 수 없을 때"""
        mock_config = MagicMock()
        mock_config.sessions = {}
        mock_config.profiles = {}
        mock_load_config.return_value = mock_config

        runner = HeadlessRunner(basic_config)

        from cli.flow.context import ExecutionContext

        runner._ctx = ExecutionContext()

        result = runner._setup_auth()

        assert result is False

    @patch("cli.headless.console")
    @patch("core.auth.config.load_config")
    @patch("core.auth.config.detect_provider_type")
    def test_setup_static_credentials(self, mock_detect, mock_load_config, mock_console, basic_config):
        """Static Credentials 설정"""
        from core.auth.types import ProviderType

        mock_config = MagicMock()
        mock_config.sessions = {}
        mock_config.profiles = {"test-profile": {"aws_access_key_id": "test"}}
        mock_load_config.return_value = mock_config
        mock_detect.return_value = ProviderType.STATIC_CREDENTIALS

        runner = HeadlessRunner(basic_config)

        from cli.flow.context import ExecutionContext, ProviderKind

        runner._ctx = ExecutionContext()

        result = runner._setup_auth()

        assert result is True
        assert runner._ctx.provider_kind == ProviderKind.STATIC_CREDENTIALS

    @patch("cli.headless.console")
    @patch("core.auth.config.load_config")
    @patch("core.auth.config.detect_provider_type")
    def test_setup_sso_profile(self, mock_detect, mock_load_config, mock_console, basic_config):
        """SSO Profile 설정"""
        from core.auth.types import ProviderType

        mock_config = MagicMock()
        mock_config.sessions = {}
        mock_config.profiles = {"test-profile": {"sso_start_url": "https://test.awsapps.com/start"}}
        mock_load_config.return_value = mock_config
        mock_detect.return_value = ProviderType.SSO_PROFILE

        runner = HeadlessRunner(basic_config)

        from cli.flow.context import ExecutionContext, ProviderKind

        runner._ctx = ExecutionContext()

        result = runner._setup_auth()

        assert result is True
        assert runner._ctx.provider_kind == ProviderKind.SSO_PROFILE


class TestHeadlessRunnerPrintSummary:
    """HeadlessRunner 요약 출력 테스트"""

    @patch("cli.headless.console")
    def test_print_summary_single_region(self, mock_console):
        """단일 리전 요약 출력"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext, ToolInfo

        runner._ctx = ExecutionContext()
        runner._ctx.tool = ToolInfo(
            name="EBS Audit",
            description="test",
            category="ec2",
            permission="read",
        )
        runner._ctx.profile_name = "test-profile"
        runner._ctx.regions = ["ap-northeast-2"]

        runner._print_summary()

        # console.print가 호출되었는지 확인
        assert mock_console.print.called

    @patch("cli.headless.console")
    def test_print_summary_multiple_regions(self, mock_console):
        """다중 리전 요약 출력"""
        config = HeadlessConfig(
            category="ec2",
            tool_module="ebs_audit",
            profile="test-profile",
            regions=["ap-northeast-2", "us-east-1"],
        )
        runner = HeadlessRunner(config)

        from cli.flow.context import ExecutionContext, ToolInfo

        runner._ctx = ExecutionContext()
        runner._ctx.tool = ToolInfo(
            name="EBS Audit",
            description="test",
            category="ec2",
            permission="read",
        )
        runner._ctx.profile_name = "test-profile"
        runner._ctx.regions = ["ap-northeast-2", "us-east-1"]

        runner._print_summary()

        # 리전 개수가 출력되었는지 확인
        assert mock_console.print.called
