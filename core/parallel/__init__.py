"""
core/parallel - 병렬 처리 모듈

멀티 계정/리전 AWS 작업을 병렬로 안전하게 처리합니다.

주요 구성 요소:
- ParallelSessionExecutor: Map-Reduce 패턴 병렬 실행기
- parallel_collect: 간편한 병렬 수집 함수
- @safe_aws_call: 재시도 + Rate limiting 데코레이터
- @with_retry: 간단한 재시도 데코레이터
- TokenBucketRateLimiter: API 쓰로틀링 방지

Example (권장 - parallel_collect):
    from core.parallel import parallel_collect

    def collect_volumes(session, account_id, account_name, region):
        ec2 = session.client("ec2", region_name=region)
        return ec2.describe_volumes()["Volumes"]

    result = parallel_collect(ctx, collect_volumes, max_workers=20, service="ec2")

    all_volumes = result.get_flat_data()
    print(f"성공: {result.success_count}, 실패: {result.error_count}")

    if result.error_count > 0:
        print(result.get_error_summary())

Example (Progress tracking 사용):
    from core.parallel import parallel_collect, quiet_mode
    from cli.ui import parallel_progress

    with parallel_progress("리소스 수집") as tracker:
        with quiet_mode():
            result = parallel_collect(
                ctx, collect_volumes,
                max_workers=20,
                progress_tracker=tracker
            )

    success, failed, total = tracker.stats
    print(f"완료: {success}개 성공, {failed}개 실패")

Example (상세 제어 - Executor):
    from core.parallel import ParallelSessionExecutor, ParallelConfig

    config = ParallelConfig(max_workers=30)
    executor = ParallelSessionExecutor(ctx, config)
    result = executor.execute(collect_func, service="ec2")

Example (데코레이터 - 개별 함수):
    from core.parallel import safe_aws_call, TaskError

    @safe_aws_call(service="ec2", operation="describe_instances")
    def get_instances(session, region):
        ec2 = session.client("ec2", region_name=region)
        return ec2.describe_instances()["Reservations"]

    result = get_instances(session, region)
    if isinstance(result, TaskError):
        print(f"Error: {result.message}")
"""

from .client import get_client, get_resource
from .decorators import RetryConfig, safe_aws_call, with_retry
from .errors import (
    CollectedError,
    ErrorCollector,
    ErrorSeverity,
    safe_collect,
    try_or_default,
)
from .executor import ParallelConfig, ParallelSessionExecutor, parallel_collect
from .quiet import is_quiet, quiet_mode, set_quiet
from .rate_limiter import (
    RateLimiterConfig,
    TokenBucketRateLimiter,
    create_rate_limiter,
    get_rate_limiter,
    reset_rate_limiters,
)
from .types import ErrorCategory, ParallelExecutionResult, TaskError, TaskResult

__all__: list[str] = [
    # Executor
    "ParallelSessionExecutor",
    "ParallelConfig",
    "parallel_collect",
    # Client (retry 적용)
    "get_client",
    "get_resource",
    # Decorators
    "safe_aws_call",
    "with_retry",
    "RetryConfig",
    # Error handling
    "ErrorCollector",
    "ErrorSeverity",
    "CollectedError",
    "safe_collect",
    "try_or_default",
    # Quiet mode
    "quiet_mode",
    "is_quiet",
    "set_quiet",
    # Rate Limiter
    "TokenBucketRateLimiter",
    "RateLimiterConfig",
    "get_rate_limiter",
    "create_rate_limiter",
    "reset_rate_limiters",
    # Types
    "ErrorCategory",
    "TaskError",
    "TaskResult",
    "ParallelExecutionResult",
]
