# tests/cli/flow/test_flow_manager.py
"""
Comprehensive tests for cli/flow/runner.py - Flow Runner

Tests cover:
- Flow execution lifecycle
- Tool discovery and loading
- Category/tool selection
- Error handling
- History management
- Permission validation
- Execution context management
"""

from unittest.mock import MagicMock, patch

import pytest

from cli.flow.context import ExecutionContext, ToolInfo
from cli.flow.runner import FlowRunner

# =============================================================================
# FlowRunner Creation Tests
# =============================================================================


class TestFlowRunnerCreation:
    """Test FlowRunner factory function"""

    def test_create_flow_runner(self):
        """create_flow_runner returns FlowRunner instance"""
        from cli.flow import create_flow_runner

        runner = create_flow_runner()
        assert isinstance(runner, FlowRunner)

    def test_flow_runner_instance(self):
        """FlowRunner can be instantiated directly"""
        runner = FlowRunner()
        assert isinstance(runner, FlowRunner)


# =============================================================================
# Tool Discovery Tests
# =============================================================================


class TestToolDiscovery:
    """Test tool discovery and metadata retrieval"""

    @patch("core.tools.discovery.discover_categories")
    def test_find_tool_meta_success(self, mock_discover):
        """Find tool metadata successfully"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [
                    {"name": "Unused EC2", "module": "unused", "permission": "read"},
                ],
            }
        ]

        runner = FlowRunner()
        meta = runner._find_tool_meta("ec2", "unused")

        assert meta is not None
        assert meta["name"] == "Unused EC2"
        assert meta["module"] == "unused"

    @patch("core.tools.discovery.discover_categories")
    def test_find_tool_meta_not_found(self, mock_discover):
        """Find tool returns None for nonexistent tool"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [],
            }
        ]

        runner = FlowRunner()
        meta = runner._find_tool_meta("ec2", "nonexistent")

        assert meta is None

    @patch("core.tools.discovery.discover_categories")
    def test_find_tool_meta_wrong_category(self, mock_discover):
        """Find tool returns None for wrong category"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [{"name": "Unused EC2", "module": "unused"}],
            }
        ]

        runner = FlowRunner()
        meta = runner._find_tool_meta("s3", "unused")

        assert meta is None


# =============================================================================
# Tool Execution Tests
# =============================================================================


class TestToolExecution:
    """Test tool execution logic"""

    @patch("core.tools.discovery.load_tool")
    def test_execute_tool_success(self, mock_load):
        """Execute tool successfully"""
        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="Find unused EC2 instances",
            category="ec2",
            permission="read",
        )

        runner._execute_tool(ctx)

        mock_run.assert_called_once_with(ctx)
        assert ctx.error is None

    @patch("core.tools.discovery.load_tool")
    def test_execute_tool_import_error(self, mock_load):
        """Execute tool handles import errors"""
        mock_load.side_effect = ImportError("Module not found")

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="Find unused EC2 instances",
            category="ec2",
            permission="read",
        )

        runner._execute_tool(ctx)

        assert ctx.error is not None
        assert isinstance(ctx.error, ImportError)

    @patch("core.tools.discovery.load_tool")
    def test_execute_tool_runtime_error(self, mock_load):
        """Execute tool handles runtime errors"""

        def failing_run(ctx):
            raise RuntimeError("Tool execution failed")

        mock_load.return_value = {"run": failing_run}

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="Find unused EC2 instances",
            category="ec2",
            permission="read",
        )

        with pytest.raises(RuntimeError):
            runner._execute_tool(ctx)

    @patch("core.tools.discovery.load_tool")
    def test_execute_tool_with_options_collector(self, mock_load):
        """Execute tool calls options collector"""
        mock_run = MagicMock()
        mock_collect = MagicMock()
        mock_load.return_value = {"run": mock_run, "collect_options": mock_collect}

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="Find unused EC2 instances",
            category="ec2",
            permission="read",
        )

        runner._execute_tool(ctx)

        mock_collect.assert_called_once_with(ctx)
        mock_run.assert_called_once_with(ctx)

    def test_execute_tool_missing_context_info(self):
        """Execute tool fails with missing context info"""
        runner = FlowRunner()
        ctx = ExecutionContext()

        runner._execute_tool(ctx)

        assert ctx.error is not None


# =============================================================================
# Tool Requirements Tests
# =============================================================================


class TestToolRequirements:
    """Test tool session requirement checking"""

    @patch("core.tools.discovery.discover_categories")
    def test_tool_requires_session_default(self, mock_discover):
        """Tool requires session by default"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [{"name": "Unused EC2", "module": "unused"}],
            }
        ]

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )

        requires_session = runner._tool_requires_session(ctx)
        assert requires_session is True

    @patch("core.tools.discovery.discover_categories")
    def test_tool_requires_session_explicit_true(self, mock_discover):
        """Tool with require_session=True"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [
                    {
                        "name": "Unused EC2",
                        "module": "unused",
                        "require_session": True,
                    }
                ],
            }
        ]

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )

        requires_session = runner._tool_requires_session(ctx)
        assert requires_session is True

    @patch("core.tools.discovery.discover_categories")
    def test_tool_requires_session_false(self, mock_discover):
        """Tool with require_session=False"""
        mock_discover.return_value = [
            {
                "name": "local",
                "tools": [
                    {
                        "name": "Local Tool",
                        "module": "tool",
                        "require_session": False,
                    }
                ],
            }
        ]

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "local"
        ctx.tool = ToolInfo(
            name="Local Tool",
            description="",
            category="local",
            permission="read",
        )

        requires_session = runner._tool_requires_session(ctx)
        assert requires_session is False

    def test_tool_requires_session_missing_context(self):
        """Tool requires session returns True for missing context"""
        runner = FlowRunner()
        ctx = ExecutionContext()

        requires_session = runner._tool_requires_session(ctx)
        assert requires_session is True


# =============================================================================
# History Management Tests
# =============================================================================


class TestHistoryManagement:
    """Test execution history saving"""

    @patch("core.tools.history.RecentHistory")
    @patch("core.tools.discovery.discover_categories")
    def test_save_history_success(self, mock_discover, mock_history_class):
        """Save execution history successfully"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [{"name": "Unused EC2", "module": "unused"}],
            }
        ]

        mock_history = MagicMock()
        mock_history_class.return_value = mock_history

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )

        runner._save_history(ctx)

        mock_history.add.assert_called_once_with(
            category="ec2",
            tool_name="Unused EC2",
            tool_module="unused",
        )

    def test_save_history_missing_context(self):
        """Save history handles missing context gracefully"""
        runner = FlowRunner()
        ctx = ExecutionContext()

        # Should not raise exception
        runner._save_history(ctx)

    @patch("core.tools.history.RecentHistory")
    @patch("core.tools.discovery.discover_categories")
    def test_save_history_handles_errors(self, mock_discover, mock_history_class):
        """Save history handles errors gracefully"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [{"name": "Unused EC2", "module": "unused"}],
            }
        ]

        mock_history = MagicMock()
        mock_history.add.side_effect = Exception("History save failed")
        mock_history_class.return_value = mock_history

        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )

        # Should not raise exception
        runner._save_history(ctx)


# =============================================================================
# Execution Summary Tests
# =============================================================================


class TestExecutionSummary:
    """Test execution summary printing"""

    def test_print_execution_summary_basic(self):
        """Print basic execution summary"""
        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2"]

        # Should not raise exception
        runner._print_execution_summary(ctx)

    def test_print_execution_summary_multi_region(self):
        """Print summary with multiple regions"""
        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2", "us-east-1", "eu-west-1"]

        # Should not raise exception
        runner._print_execution_summary(ctx)

    def test_print_execution_summary_with_permissions(self):
        """Print summary with required permissions"""
        runner = FlowRunner()
        ctx = ExecutionContext()
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2"]

        required_permissions = {
            "read": ["ec2:DescribeInstances"],
            "write": ["ec2:TerminateInstances"],
        }

        # Should not raise exception
        runner._print_execution_summary(ctx, required_permissions)

    def test_count_permissions(self):
        """Count permissions correctly"""
        runner = FlowRunner()

        permissions = {
            "read": ["ec2:DescribeInstances", "ec2:DescribeVolumes"],
            "write": ["ec2:TerminateInstances"],
        }

        count = runner._count_permissions(permissions)
        assert count == 3


# =============================================================================
# Permission Error Handling Tests
# =============================================================================


class TestPermissionErrorHandling:
    """Test permission error handling"""

    def test_handle_permission_error_access_denied(self):
        """Handle AccessDenied error"""
        runner = FlowRunner()

        error = MagicMock()
        error.response = {"Error": {"Code": "AccessDenied"}}

        required_permissions = {
            "read": ["ec2:DescribeInstances"],
        }

        # Should not raise exception
        runner._handle_permission_error(error, required_permissions)

    def test_handle_permission_error_unauthorized(self):
        """Handle UnauthorizedOperation error"""
        runner = FlowRunner()

        error = MagicMock()
        error.response = {"Error": {"Code": "UnauthorizedOperation"}}

        required_permissions = {
            "read": ["ec2:DescribeInstances"],
        }

        # Should not raise exception
        runner._handle_permission_error(error, required_permissions)

    def test_handle_permission_error_other_error(self):
        """Non-permission errors are ignored"""
        runner = FlowRunner()

        error = MagicMock()
        error.response = {"Error": {"Code": "InvalidParameterValue"}}

        required_permissions = {
            "read": ["ec2:DescribeInstances"],
        }

        # Should not raise exception
        runner._handle_permission_error(error, required_permissions)

    def test_handle_permission_error_no_response(self):
        """Handle error without response attribute"""
        runner = FlowRunner()

        error = Exception("Generic error")

        required_permissions = {
            "read": ["ec2:DescribeInstances"],
        }

        # Should not raise exception
        runner._handle_permission_error(error, required_permissions)


# =============================================================================
# Direct Tool Execution Tests
# =============================================================================


class TestDirectToolExecution:
    """Test run_tool_directly method"""

    @patch("core.tools.discovery.discover_categories")
    @patch("core.tools.discovery.load_tool")
    @patch("cli.flow.steps.ProfileStep")
    @patch("cli.flow.steps.RegionStep")
    def test_run_tool_directly_success(
        self,
        mock_region_step,
        mock_profile_step,
        mock_load,
        mock_discover,
    ):
        """Run tool directly with full flow"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [
                    {
                        "name": "Unused EC2",
                        "module": "unused",
                        "permission": "read",
                        "require_session": True,
                    }
                ],
            }
        ]

        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        # Mock steps
        mock_profile_step.return_value.execute = lambda ctx: ctx
        mock_region_step.return_value.execute = lambda ctx: ctx

        runner = FlowRunner()

        # Should not raise exception
        runner.run_tool_directly("ec2", "unused")

    @patch("core.tools.discovery.discover_categories")
    def test_run_tool_directly_not_found(self, mock_discover):
        """Run tool directly handles tool not found"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [],
            }
        ]

        runner = FlowRunner()

        # Should not raise exception
        runner.run_tool_directly("ec2", "nonexistent")

    @patch("core.tools.discovery.discover_categories")
    @patch("core.tools.discovery.load_tool")
    def test_run_tool_directly_no_session_required(self, mock_load, mock_discover):
        """Run tool directly without session requirement"""
        mock_discover.return_value = [
            {
                "name": "local",
                "tools": [
                    {
                        "name": "Local Tool",
                        "module": "tool",
                        "permission": "read",
                        "require_session": False,
                    }
                ],
            }
        ]

        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        runner = FlowRunner()

        # Should not raise exception
        runner.run_tool_directly("local", "tool")


# =============================================================================
# Flow Lifecycle Tests
# =============================================================================


class TestFlowLifecycle:
    """Test complete flow execution lifecycle"""

    @patch("cli.flow.runner.CategoryStep")
    @patch("cli.flow.runner.ProfileStep")
    @patch("cli.flow.runner.RegionStep")
    @patch("core.tools.discovery.load_tool")
    @patch("core.tools.discovery.discover_categories")
    @patch("core.tools.history.RecentHistory")
    def test_run_once_complete_flow(
        self,
        mock_history,
        mock_discover,
        mock_load,
        mock_region_step,
        mock_profile_step,
        mock_category_step,
    ):
        """Run once executes complete flow"""
        # Setup mocks
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [
                    {
                        "name": "Unused EC2",
                        "module": "unused",
                        "permission": "read",
                        "require_session": True,
                    }
                ],
            }
        ]

        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2"]

        # Mock the step instances
        mock_category_instance = MagicMock()
        mock_category_instance.execute.return_value = ctx
        mock_category_step.return_value = mock_category_instance

        mock_profile_instance = MagicMock()
        mock_profile_instance.execute.return_value = ctx
        mock_profile_step.return_value = mock_profile_instance

        mock_region_instance = MagicMock()
        mock_region_instance.execute.return_value = ctx
        mock_region_step.return_value = mock_region_instance

        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        runner = FlowRunner()
        result = runner._run_once()

        assert result.success is True
        assert result.context is not None

    @patch("cli.flow.runner.CategoryStep")
    def test_run_once_keyboard_interrupt(self, mock_category_step):
        """Run once handles keyboard interrupt"""
        mock_instance = MagicMock()
        mock_instance.execute.side_effect = KeyboardInterrupt()
        mock_category_step.return_value = mock_instance

        runner = FlowRunner()

        with pytest.raises(KeyboardInterrupt):
            runner._run_once()

    @patch("cli.flow.runner.CategoryStep")
    def test_run_once_generic_exception(self, mock_category_step):
        """Run once handles generic exceptions"""
        mock_instance = MagicMock()
        mock_instance.execute.side_effect = RuntimeError("Flow failed")
        mock_category_step.return_value = mock_instance

        runner = FlowRunner()

        with pytest.raises(RuntimeError):
            runner._run_once()


# =============================================================================
# Integration Tests
# =============================================================================


class TestFlowIntegration:
    """Integration tests for flow execution"""

    @patch("cli.flow.runner.CategoryStep")
    @patch("cli.flow.runner.ProfileStep")
    @patch("cli.flow.runner.RegionStep")
    @patch("core.tools.discovery.load_tool")
    @patch("core.tools.discovery.discover_categories")
    def test_full_flow_with_session_selection(
        self,
        mock_discover,
        mock_load,
        mock_region_step,
        mock_profile_step,
        mock_category_step,
    ):
        """Full flow with session selection"""
        mock_discover.return_value = [
            {
                "name": "ec2",
                "tools": [
                    {
                        "name": "Unused EC2",
                        "module": "unused",
                        "permission": "read",
                        "require_session": True,
                    }
                ],
            }
        ]

        ctx = ExecutionContext()
        ctx.category = "ec2"
        ctx.tool = ToolInfo(
            name="Unused EC2",
            description="",
            category="ec2",
            permission="read",
        )
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2"]

        # Mock step instances
        mock_category_instance = MagicMock()
        mock_category_instance.execute.return_value = ctx
        mock_category_step.return_value = mock_category_instance

        mock_profile_instance = MagicMock()
        mock_profile_instance.execute.return_value = ctx
        mock_profile_step.return_value = mock_profile_instance

        mock_region_instance = MagicMock()
        mock_region_instance.execute.return_value = ctx
        mock_region_step.return_value = mock_region_instance

        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        runner = FlowRunner()
        result = runner._run_once()

        assert result.success is True
        mock_run.assert_called_once()

    @patch("cli.flow.runner.CategoryStep")
    @patch("core.tools.discovery.load_tool")
    @patch("core.tools.discovery.discover_categories")
    def test_full_flow_without_session(
        self,
        mock_discover,
        mock_load,
        mock_category_step,
    ):
        """Full flow without session requirement"""
        mock_discover.return_value = [
            {
                "name": "local",
                "tools": [
                    {
                        "name": "Local Tool",
                        "module": "tool",
                        "permission": "read",
                        "require_session": False,
                    }
                ],
            }
        ]

        ctx = ExecutionContext()
        ctx.category = "local"
        ctx.tool = ToolInfo(
            name="Local Tool",
            description="",
            category="local",
            permission="read",
        )

        mock_instance = MagicMock()
        mock_instance.execute.return_value = ctx
        mock_category_step.return_value = mock_instance

        mock_run = MagicMock()
        mock_load.return_value = {"run": mock_run}

        runner = FlowRunner()
        result = runner._run_once()

        assert result.success is True
        mock_run.assert_called_once()
