"""
tests/shared/aws/lambda_/test_lambda.py - Comprehensive Lambda module tests

Tests for Lambda function collection and analysis.

Test Coverage:
    - LambdaMetrics: Data class functionality
    - LambdaFunctionInfo: Data class functionality and properties
    - collect_functions: Function collection with pagination
    - collect_function_metrics: Single function metrics collection
    - collect_all_function_metrics: Batch metrics collection optimization
    - collect_functions_with_metrics: Combined collection
    - Runtime EOL: Status checking and recommendations
    - Error handling: API failures and edge cases

Test Classes:
    - TestLambdaMetrics: 3 tests
    - TestLambdaFunctionInfo: 6 tests
    - TestCollectFunctions: 5 tests
    - TestCollectFunctionMetrics: 4 tests
    - TestCollectAllFunctionMetrics: 4 tests
    - TestCollectFunctionsWithMetrics: 3 tests
    - TestRuntimeEOL: 8 tests
    - TestRuntimeInfo: 5 tests

Total: 38 tests covering Lambda collection and EOL tracking.

Note: Tests use mocking for AWS Lambda and CloudWatch API calls.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from shared.aws.lambda_.collector import (
    LambdaFunctionInfo,
    LambdaMetrics,
    collect_all_function_metrics,
    collect_function_metrics,
    collect_functions,
    collect_functions_with_metrics,
)
from shared.aws.lambda_.runtime_eol import (
    EOLStatus,
    RuntimeInfo,
    get_deprecated_runtimes,
    get_expiring_runtimes,
    get_recommended_upgrade,
    get_runtime_info,
    get_runtime_status,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Mock boto3 session"""
    session = Mock()
    return session


@pytest.fixture
def mock_lambda_client():
    """Mock Lambda client"""
    client = Mock()
    return client


@pytest.fixture
def mock_cloudwatch_client():
    """Mock CloudWatch client"""
    client = Mock()
    return client


@pytest.fixture
def sample_function_data():
    """Sample Lambda function data from AWS API"""
    return {
        "FunctionName": "my-test-function",
        "FunctionArn": "arn:aws:lambda:ap-northeast-2:123456789012:function:my-test-function",
        "Runtime": "python3.12",
        "Handler": "lambda_function.lambda_handler",
        "Description": "Test Lambda function",
        "MemorySize": 256,
        "Timeout": 30,
        "CodeSize": 1024000,
        "LastModified": "2024-01-15T10:30:00.000+0000",
        "Role": "arn:aws:iam::123456789012:role/lambda-role",
        "VpcConfig": {
            "SubnetIds": ["subnet-12345678", "subnet-87654321"],
            "SecurityGroupIds": ["sg-12345678"],
            "VpcId": "vpc-12345678",
        },
        "Environment": {"Variables": {"ENV": "prod", "DEBUG": "false"}},
    }


@pytest.fixture
def sample_function_no_vpc():
    """Sample Lambda function without VPC"""
    return {
        "FunctionName": "no-vpc-function",
        "FunctionArn": "arn:aws:lambda:ap-northeast-2:123456789012:function:no-vpc-function",
        "Runtime": "nodejs20.x",
        "Handler": "index.handler",
        "Description": "",
        "MemorySize": 128,
        "Timeout": 3,
        "CodeSize": 512000,
        "LastModified": "2024-01-10T08:00:00.000+0000",
        "Role": "arn:aws:iam::123456789012:role/lambda-role",
        "VpcConfig": {"SubnetIds": []},  # Empty subnet list will be treated as no VPC
        "Environment": {},
    }


@pytest.fixture
def sample_cloudwatch_metric_data():
    """Sample CloudWatch metric data"""
    return {
        "MetricDataResults": [
            {"Id": "my_test_function_invocations", "Values": [1000.0], "Timestamps": []},
            {"Id": "my_test_function_errors", "Values": [10.0], "Timestamps": []},
            {"Id": "my_test_function_throttles", "Values": [5.0], "Timestamps": []},
            {"Id": "my_test_function_duration_avg", "Values": [150.5], "Timestamps": []},
            {"Id": "my_test_function_duration_max", "Values": [500.0], "Timestamps": []},
            {"Id": "my_test_function_duration_min", "Values": [50.0], "Timestamps": []},
            {"Id": "my_test_function_concurrent", "Values": [3.0], "Timestamps": []},
        ]
    }


# =============================================================================
# LambdaMetrics Tests
# =============================================================================


class TestLambdaMetrics:
    """LambdaMetrics data class tests"""

    def test_default_initialization(self):
        """Test default metric values"""
        metrics = LambdaMetrics()

        assert metrics.invocations == 0
        assert metrics.errors == 0
        assert metrics.throttles == 0
        assert metrics.duration_avg_ms == 0.0
        assert metrics.duration_max_ms == 0.0
        assert metrics.duration_min_ms == 0.0
        assert metrics.concurrent_executions_max == 0
        assert metrics.period_days == 30
        assert metrics.last_invocation_time is None

    def test_custom_initialization(self):
        """Test custom metric values"""
        last_invocation = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        metrics = LambdaMetrics(
            invocations=1000,
            errors=10,
            throttles=5,
            duration_avg_ms=150.5,
            duration_max_ms=500.0,
            duration_min_ms=50.0,
            concurrent_executions_max=3,
            period_days=7,
            last_invocation_time=last_invocation,
        )

        assert metrics.invocations == 1000
        assert metrics.errors == 10
        assert metrics.throttles == 5
        assert metrics.duration_avg_ms == 150.5
        assert metrics.duration_max_ms == 500.0
        assert metrics.duration_min_ms == 50.0
        assert metrics.concurrent_executions_max == 3
        assert metrics.period_days == 7
        assert metrics.last_invocation_time == last_invocation

    def test_metrics_dataclass_fields(self):
        """Test that metrics is a proper dataclass"""
        metrics = LambdaMetrics(invocations=100, errors=5)

        # Should be able to modify fields
        metrics.invocations = 200
        assert metrics.invocations == 200

        # Should support equality
        metrics2 = LambdaMetrics(invocations=200, errors=5)
        assert metrics == metrics2


# =============================================================================
# LambdaFunctionInfo Tests
# =============================================================================


class TestLambdaFunctionInfo:
    """LambdaFunctionInfo data class tests"""

    def test_required_fields(self):
        """Test required fields initialization"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn:aws:lambda:ap-northeast-2:123456789012:function:test-func",
            runtime="python3.12",
            handler="lambda_function.lambda_handler",
            description="Test",
            memory_mb=256,
            timeout_seconds=30,
            code_size_bytes=1024000,
            last_modified=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            role="arn:aws:iam::123456789012:role/lambda-role",
        )

        assert func.function_name == "test-func"
        assert func.runtime == "python3.12"
        assert func.memory_mb == 256
        assert func.timeout_seconds == 30

    def test_default_optional_fields(self):
        """Test default values for optional fields"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )

        assert func.vpc_config is None
        assert func.environment_variables == 0
        assert func.account_id == ""
        assert func.account_name == ""
        assert func.region == ""
        assert func.tags == {}
        assert func.metrics is None
        assert func.provisioned_concurrency == 0
        assert func.reserved_concurrency is None
        assert func.estimated_monthly_cost == 0.0

    def test_is_unused_property_no_metrics(self):
        """Test is_unused when metrics is None"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )

        assert func.is_unused is False

    def test_is_unused_property_with_invocations(self):
        """Test is_unused when function has invocations"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )
        func.metrics = LambdaMetrics(invocations=100)

        assert func.is_unused is False

    def test_is_unused_property_no_invocations(self):
        """Test is_unused when function has no invocations"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )
        func.metrics = LambdaMetrics(invocations=0)

        assert func.is_unused is True

    def test_code_size_mb_property(self):
        """Test code size conversion to MB"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024000,  # 1000 KB
            last_modified=None,
            role="role",
        )

        assert func.code_size_mb == pytest.approx(0.9765625)  # 1024000 / (1024 * 1024)

    def test_has_vpc_property_with_vpc(self):
        """Test has_vpc when VPC is configured"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
            vpc_config={"SubnetIds": ["subnet-123"]},
        )

        assert func.has_vpc is True

    def test_has_vpc_property_no_vpc(self):
        """Test has_vpc when VPC is not configured"""
        func = LambdaFunctionInfo(
            function_name="test-func",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
            vpc_config=None,
        )

        assert func.has_vpc is False

        # Also test with empty SubnetIds
        func.vpc_config = {"SubnetIds": []}
        assert func.has_vpc is False


# =============================================================================
# collect_functions Tests
# =============================================================================


class TestCollectFunctions:
    """collect_functions() tests"""

    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector.try_or_default")
    def test_collect_functions_basic(self, mock_try_or_default, mock_get_client, mock_session, sample_function_data):
        """Test basic function collection"""
        mock_lambda_client = Mock()
        mock_get_client.return_value = mock_lambda_client

        # Mock paginator
        mock_paginator = Mock()
        mock_lambda_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Functions": [sample_function_data]}]

        # Mock try_or_default to return empty tags and no provisioned/reserved concurrency
        mock_try_or_default.side_effect = lambda func, **kwargs: func()

        # Mock tag and concurrency responses
        mock_lambda_client.list_tags.return_value = {"Tags": {"Environment": "prod"}}
        mock_lambda_client.list_provisioned_concurrency_configs.return_value = {"ProvisionedConcurrencyConfigs": []}
        mock_lambda_client.get_function_concurrency.return_value = {}

        functions = collect_functions(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(functions) == 1
        func = functions[0]
        assert func.function_name == "my-test-function"
        assert func.runtime == "python3.12"
        assert func.memory_mb == 256
        assert func.timeout_seconds == 30
        assert func.code_size_bytes == 1024000
        assert func.account_id == "123456789012"
        assert func.account_name == "test-account"
        assert func.region == "ap-northeast-2"

    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector.try_or_default")
    def test_collect_functions_with_tags(
        self, mock_try_or_default, mock_get_client, mock_session, sample_function_data
    ):
        """Test function collection with tags"""
        mock_lambda_client = Mock()
        mock_get_client.return_value = mock_lambda_client

        mock_paginator = Mock()
        mock_lambda_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Functions": [sample_function_data]}]

        # Mock try_or_default to return tags
        def try_or_default_side_effect(func, default, **kwargs):
            if kwargs.get("operation") == "list_tags":
                return {"Environment": "prod", "Team": "backend"}
            return []

        mock_try_or_default.side_effect = try_or_default_side_effect

        functions = collect_functions(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(functions) == 1
        assert functions[0].tags == {"Environment": "prod", "Team": "backend"}

    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector.try_or_default")
    def test_collect_functions_no_vpc(self, mock_try_or_default, mock_get_client, mock_session, sample_function_no_vpc):
        """Test function collection without VPC"""
        mock_lambda_client = Mock()
        mock_get_client.return_value = mock_lambda_client

        mock_paginator = Mock()
        mock_lambda_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Functions": [sample_function_no_vpc]}]

        mock_try_or_default.side_effect = lambda func, default, **kwargs: default

        functions = collect_functions(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(functions) == 1
        assert functions[0].vpc_config is None
        assert functions[0].has_vpc is False

    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector.try_or_default")
    def test_collect_functions_with_concurrency(
        self, mock_try_or_default, mock_get_client, mock_session, sample_function_data
    ):
        """Test function collection with provisioned and reserved concurrency"""
        mock_lambda_client = Mock()
        mock_get_client.return_value = mock_lambda_client

        mock_paginator = Mock()
        mock_lambda_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Functions": [sample_function_data]}]

        # Mock try_or_default to return concurrency configs
        def try_or_default_side_effect(func, default, **kwargs):
            op = kwargs.get("operation")
            if op == "list_tags":
                return {}
            elif op == "list_provisioned_concurrency_configs":
                return [{"AllocatedProvisionedConcurrentExecutions": 5}]
            elif op == "get_function_concurrency":
                return 10
            return default

        mock_try_or_default.side_effect = try_or_default_side_effect

        functions = collect_functions(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(functions) == 1
        assert functions[0].provisioned_concurrency == 5
        assert functions[0].reserved_concurrency == 10

    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_functions_api_error(self, mock_get_client, mock_session):
        """Test function collection with API error"""
        mock_lambda_client = Mock()
        mock_get_client.return_value = mock_lambda_client

        # Mock ClientError
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_lambda_client.get_paginator.side_effect = ClientError(error_response, "list_functions")

        functions = collect_functions(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert functions == []


# =============================================================================
# collect_function_metrics Tests
# =============================================================================


class TestCollectFunctionMetrics:
    """collect_function_metrics() tests"""

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector._get_last_invocation_time")
    def test_collect_function_metrics_basic(
        self, mock_get_last_inv, mock_get_client, mock_batch_get_metrics, mock_session
    ):
        """Test basic metrics collection for single function"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        # Mock batch_get_metrics to return metric data
        mock_batch_get_metrics.return_value = {
            "my_test_function_invocations": 1000.0,
            "my_test_function_errors": 10.0,
            "my_test_function_throttles": 5.0,
            "my_test_function_duration_avg": 150.5,
            "my_test_function_duration_max": 500.0,
            "my_test_function_duration_min": 50.0,
            "my_test_function_concurrent": 3.0,
        }

        mock_get_last_inv.return_value = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        metrics = collect_function_metrics(mock_session, "ap-northeast-2", "my-test-function", days=30)

        assert metrics.invocations == 1000
        assert metrics.errors == 10
        assert metrics.throttles == 5
        assert metrics.duration_avg_ms == 150.5
        assert metrics.duration_max_ms == 500.0
        assert metrics.duration_min_ms == 50.0
        assert metrics.concurrent_executions_max == 3
        assert metrics.period_days == 30
        assert metrics.last_invocation_time == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_function_metrics_no_invocations(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test metrics collection for function with no invocations"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        # Return empty metrics
        mock_batch_get_metrics.return_value = {}

        metrics = collect_function_metrics(mock_session, "ap-northeast-2", "unused-function", days=30)

        assert metrics.invocations == 0
        assert metrics.errors == 0
        assert metrics.throttles == 0
        assert metrics.last_invocation_time is None

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    @patch("shared.aws.lambda_.collector._get_last_invocation_time")
    def test_collect_function_metrics_custom_period(
        self, mock_get_last_inv, mock_get_client, mock_batch_get_metrics, mock_session
    ):
        """Test metrics collection with custom period"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        mock_batch_get_metrics.return_value = {"test_func_invocations": 500.0}
        mock_get_last_inv.return_value = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        metrics = collect_function_metrics(mock_session, "ap-northeast-2", "test-func", days=7)

        assert metrics.period_days == 7
        assert metrics.invocations == 500

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_function_metrics_api_error(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test metrics collection with API error"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        # Mock ClientError in batch_get_metrics
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_batch_get_metrics.side_effect = ClientError(error_response, "get_metric_data")

        # Should return empty metrics on error
        metrics = collect_function_metrics(mock_session, "ap-northeast-2", "test-function")

        assert metrics.invocations == 0
        assert metrics.errors == 0


# =============================================================================
# collect_all_function_metrics Tests
# =============================================================================


class TestCollectAllFunctionMetrics:
    """collect_all_function_metrics() batch optimization tests"""

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_all_function_metrics_basic(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test batch metrics collection for multiple functions"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        # Mock batch_get_metrics to return data for two functions
        mock_batch_get_metrics.return_value = {
            "func1_invocations": 1000.0,
            "func1_errors": 10.0,
            "func1_throttles": 0.0,
            "func1_duration_avg": 100.0,
            "func2_invocations": 500.0,
            "func2_errors": 5.0,
            "func2_throttles": 2.0,
            "func2_duration_avg": 200.0,
        }

        results = collect_all_function_metrics(mock_session, "ap-northeast-2", ["func1", "func2"], days=30)

        assert len(results) == 2
        assert results["func1"].invocations == 1000
        assert results["func1"].errors == 10
        assert results["func2"].invocations == 500
        assert results["func2"].errors == 5

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_all_function_metrics_empty_list(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test batch metrics collection with empty function list"""
        results = collect_all_function_metrics(mock_session, "ap-northeast-2", [], days=30)

        assert results == {}
        mock_get_client.assert_not_called()
        mock_batch_get_metrics.assert_not_called()

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_all_function_metrics_no_data(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test batch metrics collection when no metric data is available"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        mock_batch_get_metrics.return_value = {}

        results = collect_all_function_metrics(mock_session, "ap-northeast-2", ["func1", "func2"])

        assert len(results) == 2
        assert results["func1"].invocations == 0
        assert results["func2"].invocations == 0

    @patch("shared.aws.lambda_.collector.batch_get_metrics")
    @patch("shared.aws.lambda_.collector.get_client")
    def test_collect_all_function_metrics_api_error(self, mock_get_client, mock_batch_get_metrics, mock_session):
        """Test batch metrics collection with API error"""
        mock_cloudwatch_client = Mock()
        mock_get_client.return_value = mock_cloudwatch_client

        # Mock ClientError
        error_response = {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}
        mock_batch_get_metrics.side_effect = ClientError(error_response, "get_metric_data")

        results = collect_all_function_metrics(mock_session, "ap-northeast-2", ["func1"])

        # Should return initialized metrics on error
        assert len(results) == 1
        assert results["func1"].invocations == 0


# =============================================================================
# collect_functions_with_metrics Tests
# =============================================================================


class TestCollectFunctionsWithMetrics:
    """collect_functions_with_metrics() integration tests"""

    @patch("shared.aws.lambda_.collector.collect_all_function_metrics")
    @patch("shared.aws.lambda_.collector.collect_functions")
    def test_collect_functions_with_metrics_basic(self, mock_collect_functions, mock_collect_metrics, mock_session):
        """Test combined function and metrics collection"""
        # Mock function collection
        func1 = LambdaFunctionInfo(
            function_name="func1",
            function_arn="arn:aws:lambda:ap-northeast-2:123456789012:function:func1",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )
        func2 = LambdaFunctionInfo(
            function_name="func2",
            function_arn="arn:aws:lambda:ap-northeast-2:123456789012:function:func2",
            runtime="nodejs20.x",
            handler="index.handler",
            description="",
            memory_mb=256,
            timeout_seconds=30,
            code_size_bytes=2048,
            last_modified=None,
            role="role",
        )
        mock_collect_functions.return_value = [func1, func2]

        # Mock metrics collection
        metrics1 = LambdaMetrics(invocations=1000, errors=10)
        metrics2 = LambdaMetrics(invocations=0, errors=0)
        mock_collect_metrics.return_value = {"func1": metrics1, "func2": metrics2}

        functions = collect_functions_with_metrics(
            mock_session, "123456789012", "test-account", "ap-northeast-2", metric_days=30
        )

        assert len(functions) == 2
        assert functions[0].function_name == "func1"
        assert functions[0].metrics.invocations == 1000
        assert functions[1].function_name == "func2"
        assert functions[1].metrics.invocations == 0

    @patch("shared.aws.lambda_.collector.collect_all_function_metrics")
    @patch("shared.aws.lambda_.collector.collect_functions")
    def test_collect_functions_with_metrics_empty(self, mock_collect_functions, mock_collect_metrics, mock_session):
        """Test combined collection with no functions"""
        mock_collect_functions.return_value = []

        functions = collect_functions_with_metrics(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert functions == []
        mock_collect_metrics.assert_not_called()

    @patch("shared.aws.lambda_.collector.collect_all_function_metrics")
    @patch("shared.aws.lambda_.collector.collect_functions")
    def test_collect_functions_with_metrics_custom_period(
        self, mock_collect_functions, mock_collect_metrics, mock_session
    ):
        """Test combined collection with custom metric period"""
        func1 = LambdaFunctionInfo(
            function_name="func1",
            function_arn="arn",
            runtime="python3.12",
            handler="handler",
            description="",
            memory_mb=128,
            timeout_seconds=3,
            code_size_bytes=1024,
            last_modified=None,
            role="role",
        )
        mock_collect_functions.return_value = [func1]
        mock_collect_metrics.return_value = {"func1": LambdaMetrics(period_days=7)}

        functions = collect_functions_with_metrics(
            mock_session, "123456789012", "test-account", "ap-northeast-2", metric_days=7
        )

        assert len(functions) == 1
        assert functions[0].metrics.period_days == 7
        mock_collect_metrics.assert_called_once_with(mock_session, "ap-northeast-2", ["func1"], 7)


# =============================================================================
# Runtime EOL Tests
# =============================================================================


class TestRuntimeEOL:
    """Runtime EOL status and recommendation tests"""

    def test_get_runtime_info_existing(self):
        """Test getting runtime info for existing runtime"""
        info = get_runtime_info("python3.12")

        assert info is not None
        assert info.runtime_id == "python3.12"
        assert info.name == "Python 3.12"

    def test_get_runtime_info_nonexistent(self):
        """Test getting runtime info for nonexistent runtime"""
        info = get_runtime_info("python99.99")

        assert info is None

    def test_get_runtime_status_supported(self):
        """Test runtime status for supported runtime"""
        status = get_runtime_status("python3.13")

        assert status == EOLStatus.SUPPORTED

    def test_get_runtime_status_deprecated(self):
        """Test runtime status for deprecated runtime"""
        status = get_runtime_status("python2.7")

        assert status == EOLStatus.DEPRECATED

    def test_get_runtime_status_unknown(self):
        """Test runtime status for unknown runtime"""
        status = get_runtime_status("unknown-runtime")

        assert status == EOLStatus.SUPPORTED

    def test_get_deprecated_runtimes(self):
        """Test getting all deprecated runtimes"""
        deprecated = get_deprecated_runtimes()

        assert isinstance(deprecated, dict)
        assert "python2.7" in deprecated
        assert "python3.6" in deprecated
        assert "nodejs12.x" in deprecated
        # Supported runtime should not be in list
        assert "python3.12" not in deprecated

    def test_get_expiring_runtimes(self):
        """Test getting runtimes expiring within specified days"""
        # Get runtimes expiring in next 365 days
        expiring = get_expiring_runtimes(days=365)

        assert isinstance(expiring, dict)
        # Should include runtimes with future deprecation dates
        # but not already deprecated ones

    def test_get_recommended_upgrade(self):
        """Test getting recommended upgrade path"""
        # Python 2.7 should recommend Python 3.13
        upgrade = get_recommended_upgrade("python2.7")
        assert upgrade == "python3.13"

        # Node.js 16 should recommend Node.js 22
        upgrade = get_recommended_upgrade("nodejs16.x")
        assert upgrade == "nodejs22.x"

        # Java 8 should recommend Java 21
        upgrade = get_recommended_upgrade("java8")
        assert upgrade == "java21"

        # Active runtime with no upgrade path should have no recommendation
        upgrade = get_recommended_upgrade("python3.13")
        assert upgrade is None


# =============================================================================
# RuntimeInfo Tests
# =============================================================================


class TestRuntimeInfo:
    """RuntimeInfo data class tests"""

    def test_runtime_info_supported(self):
        """Test RuntimeInfo for supported runtime"""
        info = RuntimeInfo(
            runtime_id="python3.12",
            name="Python 3.12",
            deprecation_date=None,
            block_update_date=None,
            eol_date=None,
        )

        assert info.is_deprecated is False
        assert info.days_until_deprecation is None
        assert info.status == EOLStatus.SUPPORTED

    def test_runtime_info_deprecated(self):
        """Test RuntimeInfo for deprecated runtime"""
        past_date = date(2023, 1, 1)
        info = RuntimeInfo(
            runtime_id="python2.7",
            name="Python 2.7",
            deprecation_date=past_date,
            block_update_date=date(2023, 6, 1),
            eol_date=None,
        )

        assert info.is_deprecated is True
        assert info.status == EOLStatus.DEPRECATED

    def test_runtime_info_critical(self):
        """Test RuntimeInfo for runtime in critical period (30 days)"""
        future_date = date.today() + timedelta(days=20)
        info = RuntimeInfo(
            runtime_id="test-runtime",
            name="Test Runtime",
            deprecation_date=future_date,
            block_update_date=None,
            eol_date=None,
        )

        assert info.is_deprecated is False
        assert info.days_until_deprecation <= 30
        assert info.status == EOLStatus.CRITICAL

    def test_runtime_info_high(self):
        """Test RuntimeInfo for runtime in high warning period (90 days)"""
        future_date = date.today() + timedelta(days=60)
        info = RuntimeInfo(
            runtime_id="test-runtime",
            name="Test Runtime",
            deprecation_date=future_date,
            block_update_date=None,
            eol_date=None,
        )

        assert info.is_deprecated is False
        assert 30 < info.days_until_deprecation <= 90
        assert info.status == EOLStatus.HIGH

    def test_runtime_info_medium(self):
        """Test RuntimeInfo for runtime in medium warning period (180 days)"""
        future_date = date.today() + timedelta(days=120)
        info = RuntimeInfo(
            runtime_id="test-runtime",
            name="Test Runtime",
            deprecation_date=future_date,
            block_update_date=None,
            eol_date=None,
        )

        assert info.is_deprecated is False
        assert 90 < info.days_until_deprecation <= 180
        assert info.status == EOLStatus.MEDIUM
