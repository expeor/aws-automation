# tests/test_flow_runner.py
"""
internal/flow/runner.py 단위 테스트

FlowRunner 클래스 테스트.
"""

from unittest.mock import MagicMock, patch  # noqa: F401

import pytest

from cli.flow.context import ExecutionContext, FlowResult, ProviderKind, ToolInfo
from cli.flow.runner import FlowRunner, create_flow_runner

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def flow_runner():
    """FlowRunner 인스턴스"""
    return FlowRunner()


@pytest.fixture
def mock_context():
    """Mock ExecutionContext"""
    tool = ToolInfo(
        name="테스트 도구",
        description="테스트 설명",
        category="test",
        permission="read",
    )
    return ExecutionContext(
        category="test",
        tool=tool,
        profile_name="dev",
        regions=["ap-northeast-2"],
    )


# =============================================================================
# create_flow_runner 테스트
# =============================================================================


class TestCreateFlowRunner:
    """create_flow_runner 함수 테스트"""

    def test_returns_flow_runner(self):
        """FlowRunner 인스턴스 반환"""
        runner = create_flow_runner()
        assert isinstance(runner, FlowRunner)


# =============================================================================
# FlowRunner._tool_requires_session 테스트
# =============================================================================


class TestToolRequiresSession:
    """_tool_requires_session 메서드 테스트"""

    def test_no_tool_returns_true(self, flow_runner):
        """도구 없으면 True (기본값)"""
        ctx = ExecutionContext()
        assert flow_runner._tool_requires_session(ctx) is True

    def test_no_category_returns_true(self, flow_runner):
        """카테고리 없으면 True (기본값)"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(tool=tool)
        assert flow_runner._tool_requires_session(ctx) is True

    @patch("core.tools.discovery.discover_categories")
    def test_tool_with_require_session_false(self, mock_discover, flow_runner):
        """require_session=False인 도구"""
        mock_discover.return_value = [
            {
                "name": "test",
                "tools": [
                    {
                        "name": "세션 불필요 도구",
                        "require_session": False,
                    }
                ],
            }
        ]

        tool = ToolInfo(
            name="세션 불필요 도구",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(category="test", tool=tool)

        assert flow_runner._tool_requires_session(ctx) is False

    @patch("core.tools.discovery.discover_categories")
    def test_tool_with_require_session_true(self, mock_discover, flow_runner):
        """require_session=True인 도구 (기본값)"""
        mock_discover.return_value = [
            {
                "name": "test",
                "tools": [
                    {
                        "name": "세션 필요 도구",
                        "require_session": True,
                    }
                ],
            }
        ]

        tool = ToolInfo(
            name="세션 필요 도구",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(category="test", tool=tool)

        assert flow_runner._tool_requires_session(ctx) is True

    @patch("core.tools.discovery.discover_categories")
    def test_tool_without_require_session_defaults_true(self, mock_discover, flow_runner):
        """require_session 없으면 True (기본값)"""
        mock_discover.return_value = [
            {
                "name": "test",
                "tools": [
                    {
                        "name": "기본 도구",
                        # require_session 없음
                    }
                ],
            }
        ]

        tool = ToolInfo(
            name="기본 도구",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(category="test", tool=tool)

        assert flow_runner._tool_requires_session(ctx) is True

    @patch("core.tools.discovery.discover_categories")
    def test_tool_not_found_returns_true(self, mock_discover, flow_runner):
        """도구를 찾지 못하면 True"""
        mock_discover.return_value = [
            {
                "name": "other",
                "tools": [],
            }
        ]

        tool = ToolInfo(
            name="존재하지 않는 도구",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(category="test", tool=tool)

        assert flow_runner._tool_requires_session(ctx) is True


# =============================================================================
# FlowRunner._execute_tool 테스트
# =============================================================================


class TestExecuteTool:
    """_execute_tool 메서드 테스트"""

    def test_no_tool_sets_error(self, flow_runner):
        """도구 없으면 에러 설정"""
        ctx = ExecutionContext(category="test")
        flow_runner._execute_tool(ctx)

        assert ctx.error is not None
        assert "선택되지 않음" in str(ctx.error)

    def test_no_category_sets_error(self, flow_runner):
        """카테고리 없으면 에러 설정"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(tool=tool)
        flow_runner._execute_tool(ctx)

        assert ctx.error is not None

    @patch("core.tools.discovery.load_tool")
    def test_tool_not_found(self, mock_load, flow_runner, mock_context):
        """도구를 찾지 못하면 경고"""
        mock_load.return_value = None

        # 에러 발생하지 않음 (경고만 출력)
        flow_runner._execute_tool(mock_context)

        mock_load.assert_called_once_with("test", "테스트 도구")

    @patch("core.tools.discovery.load_tool")
    def test_tool_execution_success(self, mock_load, flow_runner, mock_context):
        """도구 실행 성공"""
        mock_run = MagicMock(return_value="결과")
        mock_load.return_value = {
            "run": mock_run,
            "collect_options": None,
            "meta": {},
        }

        flow_runner._execute_tool(mock_context)

        mock_run.assert_called_once_with(mock_context)
        assert mock_context.result == "결과"
        assert mock_context.error is None

    @patch("core.tools.discovery.load_tool")
    def test_tool_execution_with_collect_options(self, mock_load, flow_runner, mock_context):
        """collect_options 호출 확인"""
        mock_run = MagicMock()
        mock_collect = MagicMock()
        mock_load.return_value = {
            "run": mock_run,
            "collect_options": mock_collect,
            "meta": {},
        }

        flow_runner._execute_tool(mock_context)

        mock_collect.assert_called_once_with(mock_context)
        mock_run.assert_called_once_with(mock_context)

    @patch("core.tools.discovery.load_tool")
    def test_tool_execution_failure(self, mock_load, flow_runner, mock_context):
        """도구 실행 실패"""
        mock_run = MagicMock(side_effect=ValueError("실행 오류"))
        mock_load.return_value = {
            "run": mock_run,
            "collect_options": None,
            "meta": {},
        }

        with pytest.raises(ValueError):
            flow_runner._execute_tool(mock_context)

        assert mock_context.error is not None


# =============================================================================
# FlowRunner._print_execution_summary 테스트
# =============================================================================


class TestPrintExecutionSummary:
    """_print_execution_summary 메서드 테스트"""

    def test_single_region(self, flow_runner, mock_context, capsys):
        """단일 리전 출력"""
        flow_runner._print_execution_summary(mock_context)
        # 출력 확인은 Rich console이라 capsys로 캡처 어려움
        # 에러 없이 실행되는지 확인

    def test_multiple_regions(self, flow_runner, capsys):
        """다중 리전 출력"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(
            category="test",
            tool=tool,
            profile_name="dev",
            regions=["ap-northeast-2", "us-east-1", "eu-west-1"],
        )

        flow_runner._print_execution_summary(ctx)
        # 에러 없이 실행되는지 확인

    def test_with_role_selection(self, flow_runner):
        """Role Selection 포함"""
        from cli.flow.context import RoleSelection

        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        ctx = ExecutionContext(
            category="test",
            tool=tool,
            profile_name="dev",
            regions=["ap-northeast-2"],
            role_selection=RoleSelection(
                primary_role="AdminRole",
                fallback_role="ReadOnlyRole",
            ),
        )

        flow_runner._print_execution_summary(ctx)
        # 에러 없이 실행되는지 확인

    def test_with_multi_account(self, flow_runner):
        """멀티 계정 포함"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )

        mock_acc = MagicMock()
        mock_acc.id = "111111111111"

        ctx = ExecutionContext(
            category="test",
            tool=tool,
            profile_name="dev",
            provider_kind=ProviderKind.SSO_SESSION,
            regions=["ap-northeast-2"],
            accounts=[mock_acc],
        )

        flow_runner._print_execution_summary(ctx)
        # 에러 없이 실행되는지 확인


# =============================================================================
# FlowRunner._run_once 테스트
# =============================================================================


class TestRunOnce:
    """_run_once 메서드 테스트"""

    @patch.object(FlowRunner, "_execute_tool")
    @patch.object(FlowRunner, "_tool_requires_session")
    @patch("cli.flow.runner.CategoryStep")
    def test_run_once_no_session_required(self, mock_cat_step, mock_requires, mock_execute, flow_runner):
        """세션 불필요 도구 실행"""
        # Setup
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        mock_ctx = ExecutionContext(category="test", tool=tool)

        mock_step_instance = MagicMock()
        mock_step_instance.execute.return_value = mock_ctx
        mock_cat_step.return_value = mock_step_instance

        mock_requires.return_value = False

        # Execute
        result = flow_runner._run_once()

        # Verify
        mock_cat_step.return_value.execute.assert_called_once()
        mock_requires.assert_called_once()
        mock_execute.assert_called_once()
        assert isinstance(result, FlowResult)

    @patch.object(FlowRunner, "_execute_tool")
    @patch.object(FlowRunner, "_tool_requires_session")
    @patch("cli.flow.runner.RegionStep")
    @patch("cli.flow.runner.ProfileStep")
    @patch("cli.flow.runner.CategoryStep")
    def test_run_once_with_session_required(
        self,
        mock_cat_step,
        mock_profile_step,
        mock_region_step,
        mock_requires,
        mock_execute,
        flow_runner,
    ):
        """세션 필요 도구 실행"""
        # Setup
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        mock_ctx = ExecutionContext(
            category="test",
            tool=tool,
            provider_kind=ProviderKind.STATIC_CREDENTIALS,
        )

        for mock_step in [mock_cat_step, mock_profile_step, mock_region_step]:
            instance = MagicMock()
            instance.execute.return_value = mock_ctx
            mock_step.return_value = instance

        mock_requires.return_value = True

        # Execute
        result = flow_runner._run_once()

        # Verify
        mock_cat_step.return_value.execute.assert_called_once()
        mock_profile_step.return_value.execute.assert_called_once()
        mock_region_step.return_value.execute.assert_called_once()
        assert isinstance(result, FlowResult)

    @patch.object(FlowRunner, "_execute_tool")
    @patch.object(FlowRunner, "_tool_requires_session")
    @patch("cli.flow.runner.RoleStep")
    @patch("cli.flow.runner.AccountStep")
    @patch("cli.flow.runner.RegionStep")
    @patch("cli.flow.runner.ProfileStep")
    @patch("cli.flow.runner.CategoryStep")
    def test_run_once_with_multi_account(
        self,
        mock_cat_step,
        mock_profile_step,
        mock_region_step,
        mock_account_step,
        mock_role_step,
        mock_requires,
        mock_execute,
        flow_runner,
    ):
        """멀티 계정 도구 실행 (Account + Role Step 호출)"""
        # Setup
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )
        mock_ctx = ExecutionContext(
            category="test",
            tool=tool,
            provider_kind=ProviderKind.SSO_SESSION,  # Multi-account
        )

        for mock_step in [
            mock_cat_step,
            mock_profile_step,
            mock_region_step,
            mock_account_step,
            mock_role_step,
        ]:
            instance = MagicMock()
            instance.execute.return_value = mock_ctx
            mock_step.return_value = instance

        mock_requires.return_value = True

        # Execute
        flow_runner._run_once()

        # Verify - SSO_SESSION이므로 AccountStep, RoleStep 호출됨
        mock_account_step.return_value.execute.assert_called_once()
        mock_role_step.return_value.execute.assert_called_once()


# =============================================================================
# FlowRunner.run 테스트
# =============================================================================


class TestRun:
    """run 메서드 테스트"""

    @patch.object(FlowRunner, "_run_once")
    def test_run_keyboard_interrupt(self, mock_run_once, flow_runner):
        """KeyboardInterrupt로 종료"""
        mock_run_once.side_effect = KeyboardInterrupt()

        # 에러 없이 종료
        flow_runner.run()

    @patch.object(FlowRunner, "_run_once")
    @patch("cli.flow.runner.console")
    def test_run_exception_continue(self, mock_console, mock_run_once, flow_runner):
        """예외 발생 후 계속"""
        # 첫 번째 호출: 예외, 두 번째: KeyboardInterrupt
        mock_run_once.side_effect = [
            ValueError("테스트 오류"),
            KeyboardInterrupt(),
        ]
        mock_console.input.return_value = "y"

        flow_runner.run()

        assert mock_run_once.call_count == 2

    @patch.object(FlowRunner, "_run_once")
    @patch("cli.flow.runner.console")
    def test_run_exception_exit(self, mock_console, mock_run_once, flow_runner):
        """예외 발생 후 종료"""
        mock_run_once.side_effect = ValueError("테스트 오류")
        mock_console.input.return_value = "n"

        flow_runner.run()

        assert mock_run_once.call_count == 1
