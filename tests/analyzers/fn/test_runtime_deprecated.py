"""
tests/analyzers/fn/test_runtime_deprecated.py - Lambda 런타임 지원 종료 분석 테스트

Test Coverage:
    - _classify_function: deprecated/soon/safe/container/unknown
    - _analyze_region: mixed functions, empty list, all deprecated
    - Data class defaults and properties
"""

from datetime import datetime, timezone

from analyzers.fn.runtime_deprecated import (
    DeprecationCategory,
    RuntimeDeprecationResult,
    _analyze_region,
    _classify_function,
)
from shared.aws.lambda_.collector import LambdaFunctionInfo

# =============================================================================
# Fixtures
# =============================================================================


def _make_function(
    name: str = "test-func",
    runtime: str = "python3.12",
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> LambdaFunctionInfo:
    """테스트용 LambdaFunctionInfo 생성"""
    return LambdaFunctionInfo(
        function_name=name,
        function_arn=f"arn:aws:lambda:{region}:{account_id}:function:{name}",
        runtime=runtime,
        handler="handler",
        description="",
        memory_mb=128,
        timeout_seconds=3,
        code_size_bytes=1024,
        last_modified=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        role="arn:aws:iam::123456789012:role/role",
        account_id=account_id,
        account_name=account_name,
        region=region,
    )


# =============================================================================
# _classify_function Tests
# =============================================================================


class TestClassifyFunction:
    """_classify_function() 테스트"""

    def test_deprecated_runtime(self):
        """이미 지원 종료된 런타임 -> DEPRECATED"""
        func = _make_function(runtime="python3.8")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.DEPRECATED
        assert finding.runtime_name == "Python 3.8"
        assert finding.os_version == "AL2"
        assert finding.recommended_upgrade == "python3.13"
        assert finding.days_remaining is not None
        assert finding.days_remaining < 0

    def test_deprecated_old_runtime(self):
        """오래된 지원 종료 런타임"""
        func = _make_function(runtime="python2.7")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.DEPRECATED
        assert finding.os_version == "AL1"
        assert finding.recommended_upgrade == "python3.13"

    def test_soon_runtime(self):
        """곧 종료될 런타임 -> SOON (365일 이내)"""
        # ruby3.2 deprecation: 2026-03-31 -> ~53 days from 2026-02-06
        func = _make_function(runtime="ruby3.2")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.SOON
        assert finding.runtime_name == "Ruby 3.2"
        assert finding.days_remaining is not None
        assert 0 < finding.days_remaining <= 365
        assert finding.recommended_upgrade == "ruby3.4"

    def test_safe_runtime_no_eol(self):
        """EOL 미정 런타임 -> SAFE"""
        func = _make_function(runtime="python3.13")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.SAFE
        assert finding.runtime_name == "Python 3.13"
        assert finding.os_version == "AL2023"
        assert finding.deprecation_date is None
        assert finding.days_remaining is None

    def test_safe_runtime_far_eol(self):
        """EOL이 365일 이상 남은 런타임 -> SAFE"""
        func = _make_function(runtime="python3.12")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.SAFE
        assert finding.days_remaining is not None
        assert finding.days_remaining > 365

    def test_container_function_unknown_runtime(self):
        """컨테이너 이미지 함수 (runtime=unknown) -> CONTAINER"""
        func = _make_function(runtime="unknown")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.CONTAINER
        assert finding.runtime_name == "Container Image"
        assert finding.os_version == ""
        assert finding.recommended_upgrade == ""

    def test_container_function_empty_runtime(self):
        """빈 런타임 -> CONTAINER"""
        func = _make_function(runtime="")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.CONTAINER

    def test_unknown_runtime_in_data(self):
        """RUNTIME_EOL_DATA에 없는 런타임 -> SAFE (보수적)"""
        func = _make_function(runtime="python4.0")
        finding = _classify_function(func)

        assert finding.category == DeprecationCategory.SAFE
        assert finding.runtime_name == "python4.0"
        assert finding.os_version == ""

    def test_finding_has_function_reference(self):
        """finding이 원본 function 참조를 갖는지 확인"""
        func = _make_function(name="my-special-func", runtime="python3.13")
        finding = _classify_function(func)

        assert finding.function is func
        assert finding.function.function_name == "my-special-func"


# =============================================================================
# _analyze_region Tests
# =============================================================================


class TestAnalyzeRegion:
    """_analyze_region() 테스트"""

    def test_mixed_functions(self):
        """다양한 런타임의 함수 분석"""
        functions = [
            _make_function(name="deprecated-func", runtime="python3.8"),
            _make_function(name="soon-func", runtime="ruby3.2"),
            _make_function(name="safe-func", runtime="python3.13"),
            _make_function(name="container-func", runtime="unknown"),
        ]

        result = _analyze_region(functions, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_functions == 4
        assert result.deprecated_count == 1
        assert result.soon_count == 1
        assert result.safe_count == 1
        assert result.container_count == 1
        assert len(result.findings) == 4

    def test_empty_functions(self):
        """빈 함수 목록"""
        result = _analyze_region([], "123456789012", "test-account", "ap-northeast-2")

        assert result.total_functions == 0
        assert result.deprecated_count == 0
        assert result.soon_count == 0
        assert result.safe_count == 0
        assert result.container_count == 0
        assert result.findings == []

    def test_all_deprecated(self):
        """모든 함수가 지원 종료된 경우"""
        functions = [
            _make_function(name="func1", runtime="python3.8"),
            _make_function(name="func2", runtime="nodejs16.x"),
            _make_function(name="func3", runtime="python2.7"),
        ]

        result = _analyze_region(functions, "123456789012", "test-account", "us-east-1")

        assert result.total_functions == 3
        assert result.deprecated_count == 3
        assert result.soon_count == 0
        assert result.safe_count == 0

    def test_all_safe(self):
        """모든 함수가 안전한 경우"""
        functions = [
            _make_function(name="func1", runtime="python3.13"),
            _make_function(name="func2", runtime="nodejs22.x"),
        ]

        result = _analyze_region(functions, "123456789012", "test-account", "us-east-1")

        assert result.total_functions == 2
        assert result.deprecated_count == 0
        assert result.safe_count == 2

    def test_result_metadata(self):
        """결과에 계정/리전 메타데이터가 포함되는지 확인"""
        result = _analyze_region([], "111222333444", "my-account", "eu-west-1")

        assert result.account_id == "111222333444"
        assert result.account_name == "my-account"
        assert result.region == "eu-west-1"


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDataClasses:
    """데이터 클래스 기본값 테스트"""

    def test_result_defaults(self):
        """RuntimeDeprecationResult 기본값"""
        result = RuntimeDeprecationResult(
            account_id="123",
            account_name="test",
            region="ap-northeast-2",
        )

        assert result.total_functions == 0
        assert result.deprecated_count == 0
        assert result.soon_count == 0
        assert result.safe_count == 0
        assert result.container_count == 0
        assert result.findings == []

    def test_deprecation_category_values(self):
        """DeprecationCategory enum 값"""
        assert DeprecationCategory.DEPRECATED.value == "deprecated"
        assert DeprecationCategory.SOON.value == "soon"
        assert DeprecationCategory.SAFE.value == "safe"
        assert DeprecationCategory.CONTAINER.value == "container"
