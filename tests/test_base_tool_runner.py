# tests/test_base_tool_runner.py
"""
internal/tools/base.py 단위 테스트

BaseToolRunner 클래스 테스트.
"""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from cli.flow.context import ExecutionContext, ProviderKind, RoleSelection
from core.tools.base import BaseToolRunner, _get_console

# =============================================================================
# Fixtures
# =============================================================================


@dataclass
class ConcreteToolRunner(BaseToolRunner):
    """테스트용 구현 클래스"""

    def get_tools(self):
        return {
            "테스트 도구": self._run_test_tool,
            "다른 도구": self._run_other_tool,
        }

    def _run_test_tool(self):
        return "test_result"

    def _run_other_tool(self):
        return "other_result"


@pytest.fixture
def mock_provider():
    """Mock Provider"""
    provider = MagicMock()
    provider.start_url = "https://example.awsapps.com/start"
    mock_session = MagicMock()
    provider.get_session.return_value = mock_session
    return provider


@pytest.fixture
def mock_context(mock_provider):
    """Mock ExecutionContext"""
    ctx = MagicMock(spec=ExecutionContext)
    ctx.profile_name = "test-profile"
    ctx.regions = ["ap-northeast-2", "us-east-1"]
    ctx.provider = mock_provider
    ctx.role_selection = None
    ctx.is_multi_account.return_value = False
    ctx.get_target_accounts.return_value = []
    return ctx


@pytest.fixture
def runner(mock_context):
    """BaseToolRunner 인스턴스"""
    return ConcreteToolRunner(ctx=mock_context)


# =============================================================================
# _get_console 테스트
# =============================================================================


class TestGetConsole:
    """_get_console 함수 테스트"""

    def test_returns_console(self):
        """Console 인스턴스 반환"""
        from rich.console import Console

        console = _get_console()
        assert isinstance(console, Console)


# =============================================================================
# BaseToolRunner 초기화 테스트
# =============================================================================


class TestBaseToolRunnerInit:
    """BaseToolRunner 초기화 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        runner = ConcreteToolRunner()

        assert runner.ctx is None
        assert runner.profiles == []
        assert runner.regions == []
        assert runner.start_url is None
        assert runner.session_name is None

    def test_with_context(self, mock_context):
        """컨텍스트로 초기화"""
        runner = ConcreteToolRunner(ctx=mock_context)

        assert runner.ctx == mock_context
        assert runner.regions == ["ap-northeast-2", "us-east-1"]
        assert runner.profiles == ["test-profile"]

    def test_with_context_extracts_sso_info(self, mock_context, mock_provider):
        """SSO 정보 추출"""
        mock_context.provider = mock_provider

        runner = ConcreteToolRunner(ctx=mock_context)

        assert runner.start_url == "https://example.awsapps.com/start"
        assert runner.session_name == "test-profile"

    def test_manual_regions_override(self, mock_context):
        """수동 regions 설정이 ctx보다 우선"""
        runner = ConcreteToolRunner(
            ctx=mock_context,
            regions=["eu-west-1"],
        )

        # 수동 설정이 유지됨 (ctx에서 덮어쓰지 않음)
        assert runner.regions == ["eu-west-1"]

    def test_manual_profiles_override(self, mock_context):
        """수동 profiles 설정이 ctx보다 우선"""
        runner = ConcreteToolRunner(
            ctx=mock_context,
            profiles=["manual-profile"],
        )

        assert runner.profiles == ["manual-profile"]


# =============================================================================
# get_tools 추상 메서드 테스트
# =============================================================================


class TestGetTools:
    """get_tools 메서드 테스트"""

    def test_returns_dict(self, runner):
        """dict 반환 확인"""
        tools = runner.get_tools()
        assert isinstance(tools, dict)

    def test_tools_are_callable(self, runner):
        """도구가 callable인지 확인"""
        tools = runner.get_tools()
        for name, func in tools.items():
            assert callable(func)

    def test_contains_expected_tools(self, runner):
        """예상 도구 포함 확인"""
        tools = runner.get_tools()
        assert "테스트 도구" in tools
        assert "다른 도구" in tools


# =============================================================================
# run_tool 메서드 테스트
# =============================================================================


class TestRunTool:
    """run_tool 메서드 테스트"""

    def test_run_existing_tool(self, runner):
        """존재하는 도구 실행"""
        result = runner.run_tool("테스트 도구")
        assert result == "test_result"

    def test_run_other_tool(self, runner):
        """다른 도구 실행"""
        result = runner.run_tool("다른 도구")
        assert result == "other_result"

    def test_run_nonexistent_tool(self, runner):
        """존재하지 않는 도구 실행"""
        result = runner.run_tool("없는 도구")
        assert result is None


# =============================================================================
# get_session 메서드 테스트
# =============================================================================


class TestGetSession:
    """get_session 메서드 테스트"""

    def test_get_session_with_provider(self, runner, mock_provider):
        """Provider를 통한 세션 획득"""
        session = runner.get_session("ap-northeast-2")

        mock_provider.get_session.assert_called_with(region="ap-northeast-2")
        assert session is not None

    def test_get_session_with_account_id(self, mock_context, mock_provider):
        """계정 ID와 함께 세션 획득"""
        mock_context.role_selection = RoleSelection(primary_role="AdminRole")

        runner = ConcreteToolRunner(ctx=mock_context)
        session = runner.get_session("ap-northeast-2", account_id="111111111111")

        mock_provider.get_session.assert_called_with(
            account_id="111111111111",
            role_name="AdminRole",
            region="ap-northeast-2",
        )

    @patch("boto3.Session")
    def test_get_session_fallback(self, mock_session, mock_context, mock_provider):
        """Provider 실패 시 fallback"""
        mock_provider.get_session.side_effect = Exception("인증 실패")

        runner = ConcreteToolRunner(ctx=mock_context)
        runner.get_session("ap-northeast-2")

        # fallback으로 boto3.Session 직접 호출
        mock_session.assert_called_with(
            profile_name="test-profile",
            region_name="ap-northeast-2",
        )

    @patch("boto3.Session")
    def test_get_session_no_context(self, mock_session):
        """컨텍스트 없이 세션 획득"""
        runner = ConcreteToolRunner(profiles=["my-profile"])
        runner.get_session("us-east-1")

        mock_session.assert_called_with(
            profile_name="my-profile",
            region_name="us-east-1",
        )

    @patch("boto3.Session")
    def test_get_session_no_profile(self, mock_session):
        """프로파일 없이 세션 획득"""
        runner = ConcreteToolRunner()
        runner.get_session("us-east-1")

        mock_session.assert_called_with(
            profile_name=None,
            region_name="us-east-1",
        )


# =============================================================================
# iterate_regions 메서드 테스트
# =============================================================================


class TestIterateRegions:
    """iterate_regions 메서드 테스트"""

    def test_yields_region_session_tuples(self, runner, mock_provider):
        """(region, session) 튜플 반환"""
        results = list(runner.iterate_regions())

        assert len(results) == 2
        assert results[0][0] == "ap-northeast-2"
        assert results[1][0] == "us-east-1"

    def test_empty_regions(self, mock_context):
        """빈 regions"""
        mock_context.regions = []
        runner = ConcreteToolRunner(ctx=mock_context)
        runner.regions = []

        results = list(runner.iterate_regions())
        assert results == []


# =============================================================================
# iterate_accounts_and_regions 메서드 테스트
# =============================================================================


class TestIterateAccountsAndRegions:
    """iterate_accounts_and_regions 메서드 테스트"""

    def test_single_account_mode(self, runner, mock_context):
        """단일 계정 모드"""
        mock_context.is_multi_account.return_value = False

        results = list(runner.iterate_accounts_and_regions())

        # account_id가 None인 튜플 반환
        assert len(results) == 2
        assert results[0][0] is None  # account_id
        assert results[0][1] == "ap-northeast-2"  # region
        assert results[1][0] is None
        assert results[1][1] == "us-east-1"

    def test_multi_account_mode(self, mock_context, mock_provider):
        """멀티 계정 모드"""
        mock_context.is_multi_account.return_value = True

        mock_acc1 = MagicMock()
        mock_acc1.id = "111111111111"  # AccountInfo.id 사용
        mock_acc2 = MagicMock()
        mock_acc2.id = "222222222222"  # AccountInfo.id 사용
        mock_context.get_target_accounts.return_value = [mock_acc1, mock_acc2]

        runner = ConcreteToolRunner(ctx=mock_context)
        results = list(runner.iterate_accounts_and_regions())

        # 2 accounts × 2 regions = 4
        assert len(results) == 4
        assert results[0] == (
            "111111111111",
            "ap-northeast-2",
            mock_provider.get_session(),
        )


# =============================================================================
# Abstract 클래스 테스트
# =============================================================================


class TestAbstractClass:
    """BaseToolRunner 추상 클래스 테스트"""

    def test_cannot_instantiate_directly(self):
        """직접 인스턴스화 불가"""
        with pytest.raises(TypeError):
            BaseToolRunner()

    def test_subclass_must_implement_get_tools(self):
        """서브클래스는 get_tools 구현 필수"""

        @dataclass
        class IncompleteRunner(BaseToolRunner):
            pass

        with pytest.raises(TypeError):
            IncompleteRunner()
