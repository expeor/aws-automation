"""
plugins/fn/common/collector.py - Lambda 함수 수집

Lambda 함수 정보 및 CloudWatch 메트릭 수집 공통 로직

최적화:
- CloudWatch GetMetricData API 사용 (배치 조회)
- 기존: 함수당 5-6 API 호출 → 최적화: 전체 1-2 API 호출
- 예: 50개 함수 × 6 메트릭 = 300 API → 1 API
"""

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from core.parallel import ErrorSeverity, get_client, try_or_default
from plugins.cloudwatch.common import MetricQuery, batch_get_metrics, sanitize_metric_id

logger = logging.getLogger(__name__)


@dataclass
class LambdaMetrics:
    """Lambda 함수 CloudWatch 메트릭"""

    # 호출 메트릭
    invocations: int = 0
    errors: int = 0
    throttles: int = 0

    # 성능 메트릭
    duration_avg_ms: float = 0.0
    duration_max_ms: float = 0.0
    duration_min_ms: float = 0.0

    # 동시성 메트릭
    concurrent_executions_max: int = 0

    # 조회 기간
    period_days: int = 30
    last_invocation_time: datetime | None = None


@dataclass
class LambdaFunctionInfo:
    """Lambda 함수 정보"""

    # 기본 정보
    function_name: str
    function_arn: str
    runtime: str
    handler: str
    description: str

    # 설정
    memory_mb: int
    timeout_seconds: int
    code_size_bytes: int
    last_modified: datetime | None

    # 실행 환경
    role: str
    vpc_config: dict | None = None
    environment_variables: int = 0

    # 메타
    account_id: str = ""
    account_name: str = ""
    region: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    # 메트릭 (나중에 채워짐)
    metrics: LambdaMetrics | None = None

    # Provisioned Concurrency (있는 경우)
    provisioned_concurrency: int = 0
    reserved_concurrency: int | None = None

    # 비용 추정
    estimated_monthly_cost: float = 0.0

    @property
    def is_unused(self) -> bool:
        """미사용 여부 (30일간 호출 없음)"""
        if self.metrics is None:
            return False
        return self.metrics.invocations == 0

    @property
    def code_size_mb(self) -> float:
        """코드 크기 (MB)"""
        return self.code_size_bytes / (1024 * 1024)

    @property
    def has_vpc(self) -> bool:
        """VPC 연결 여부"""
        if not self.vpc_config:
            return False
        return bool(self.vpc_config.get("SubnetIds"))


def collect_functions(
    session,
    account_id: str,
    account_name: str,
    region: str,
) -> list[LambdaFunctionInfo]:
    """Lambda 함수 목록 수집

    Args:
        session: boto3 세션
        account_id: AWS 계정 ID
        account_name: 계정명
        region: AWS 리전

    Returns:
        Lambda 함수 정보 리스트
    """
    from botocore.exceptions import ClientError

    functions = []

    try:
        lambda_client = get_client(session, "lambda", region_name=region)

        # 함수 목록 조회
        paginator = lambda_client.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                # 기본 정보
                function_name = fn.get("FunctionName", "")

                # 태그 조회 (옵션 - 실패해도 계속)
                fn_arn = fn.get("FunctionArn", "")
                tags: dict[str, str] = try_or_default(
                    lambda arn=fn_arn: lambda_client.list_tags(Resource=arn).get(  # type: ignore[misc]
                        "Tags", {}
                    ),
                    default={},
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    operation="list_tags",
                    severity=ErrorSeverity.DEBUG,
                )

                # VPC 설정
                vpc_config = fn.get("VpcConfig")
                if vpc_config and not vpc_config.get("SubnetIds"):
                    vpc_config = None

                # 환경 변수 개수
                env_vars = fn.get("Environment", {}).get("Variables", {})

                # 마지막 수정 시간 파싱
                last_modified = None
                lm_str = fn.get("LastModified")
                if lm_str:
                    with contextlib.suppress(ValueError):
                        # ISO 8601 형식 파싱
                        last_modified = datetime.fromisoformat(lm_str.replace("Z", "+00:00"))

                func_info = LambdaFunctionInfo(
                    function_name=function_name,
                    function_arn=fn.get("FunctionArn", ""),
                    runtime=fn.get("Runtime", "unknown"),
                    handler=fn.get("Handler", ""),
                    description=fn.get("Description", ""),
                    memory_mb=fn.get("MemorySize", 128),
                    timeout_seconds=fn.get("Timeout", 3),
                    code_size_bytes=fn.get("CodeSize", 0),
                    last_modified=last_modified,
                    role=fn.get("Role", ""),
                    vpc_config=vpc_config,
                    environment_variables=len(env_vars),
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    tags=tags,
                )

                # Provisioned Concurrency 조회 (옵션)
                pc_configs: list[dict[str, Any]] = try_or_default(
                    lambda fname=function_name: lambda_client.list_provisioned_concurrency_configs(  # type: ignore[misc]
                        FunctionName=fname
                    ).get("ProvisionedConcurrencyConfigs", []),
                    default=[],
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    operation="list_provisioned_concurrency_configs",
                    severity=ErrorSeverity.DEBUG,
                )
                for pc in pc_configs:
                    func_info.provisioned_concurrency += pc.get("AllocatedProvisionedConcurrentExecutions", 0)

                # Reserved Concurrency 조회 (옵션)
                reserved: int | None = try_or_default(
                    lambda fname=function_name: lambda_client.get_function_concurrency(  # type: ignore[misc]
                        FunctionName=fname
                    ).get("ReservedConcurrentExecutions"),
                    default=None,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    operation="get_function_concurrency",
                    severity=ErrorSeverity.DEBUG,
                )
                func_info.reserved_concurrency = reserved

                functions.append(func_info)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"[{account_name}/{region}] Lambda list_functions 실패: {error_code}")

    return functions


def collect_function_metrics(
    session,
    region: str,
    function_name: str,
    days: int = 30,
) -> LambdaMetrics:
    """Lambda 함수 CloudWatch 메트릭 수집 (단일 함수용, 하위 호환)

    Note:
        여러 함수의 메트릭을 조회할 때는 collect_all_function_metrics()를 사용하세요.
        이 함수는 하위 호환성을 위해 유지됩니다.

    Args:
        session: boto3 세션
        region: AWS 리전
        function_name: Lambda 함수 이름
        days: 조회 기간 (일)

    Returns:
        Lambda 메트릭
    """
    from botocore.exceptions import ClientError

    metrics = LambdaMetrics(period_days=days)

    try:
        cloudwatch = get_client(session, "cloudwatch", region_name=region)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        # 배치 API 사용하여 모든 메트릭 한번에 조회
        queries = _build_lambda_queries([function_name])
        results = batch_get_metrics(cloudwatch, queries, start_time, end_time, period=86400)

        # 결과 매핑
        safe_id = sanitize_metric_id(function_name)
        metrics = _parse_lambda_metrics(safe_id, results, days)

        # 마지막 호출 시간 추정 (호출이 있었던 경우만)
        if metrics.invocations > 0:
            metrics.last_invocation_time = _get_last_invocation_time(cloudwatch, function_name, start_time, end_time)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"Lambda 메트릭 수집 실패 [{function_name}]: {error_code}")

    return metrics


def collect_all_function_metrics(
    session,
    region: str,
    function_names: list[str],
    days: int = 30,
) -> dict[str, LambdaMetrics]:
    """여러 Lambda 함수의 CloudWatch 메트릭 배치 수집 (최적화)

    기존: 함수당 5-6 API 호출 → 최적화: 전체 1-2 API 호출
    예: 50개 함수 × 6 메트릭 = 300 API → 1 API

    Args:
        session: boto3 세션
        region: AWS 리전
        function_names: Lambda 함수 이름 목록
        days: 조회 기간 (일)

    Returns:
        {function_name: LambdaMetrics} 딕셔너리
    """
    from botocore.exceptions import ClientError

    if not function_names:
        return {}

    results_map: dict[str, LambdaMetrics] = {}

    # 기본 메트릭 초기화
    for func_name in function_names:
        results_map[func_name] = LambdaMetrics(period_days=days)

    try:
        cloudwatch = get_client(session, "cloudwatch", region_name=region)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        # 모든 함수에 대한 메트릭 쿼리 생성
        queries = _build_lambda_queries(function_names)

        # 배치 조회 (최대 500개씩 자동 분할)
        raw_results = batch_get_metrics(cloudwatch, queries, start_time, end_time, period=86400)

        # 함수별 결과 매핑
        for func_name in function_names:
            safe_id = sanitize_metric_id(func_name)
            results_map[func_name] = _parse_lambda_metrics(safe_id, raw_results, days)

        # 호출이 있었던 함수들의 마지막 호출 시간 조회
        # (이 부분은 추가 API 호출이 필요하므로 필요시만 조회)
        funcs_with_invocations = [fn for fn in function_names if results_map[fn].invocations > 0]

        if funcs_with_invocations:
            # 일별 호출 데이터 배치 조회
            daily_queries = [
                MetricQuery(
                    id=f"{sanitize_metric_id(fn)}_daily_inv",
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions={"FunctionName": fn},
                    stat="Sum",
                )
                for fn in funcs_with_invocations
            ]

            daily_results = batch_get_metrics(cloudwatch, daily_queries, start_time, end_time, period=86400)

            # 일별 데이터에서 마지막 호출 시간 추정
            # Note: GetMetricData는 타임스탬프를 반환하지 않아 정확한 시간 추정 어려움
            # 대략적으로 최근 호출이 있음을 표시
            for fn in funcs_with_invocations:
                safe_id = sanitize_metric_id(fn)
                daily_key = f"{safe_id}_daily_inv"
                if daily_results.get(daily_key, 0) > 0:
                    # 최근 호출이 있음을 표시 (정확한 시간은 별도 조회 필요)
                    results_map[fn].last_invocation_time = end_time

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"Lambda 배치 메트릭 수집 실패 [{region}]: {error_code}")

    return results_map


def _build_lambda_queries(function_names: list[str]) -> list[MetricQuery]:
    """Lambda 메트릭 쿼리 목록 생성"""
    queries = []

    for func_name in function_names:
        safe_id = sanitize_metric_id(func_name)
        dimensions = {"FunctionName": func_name}

        # Invocations (Sum)
        queries.append(
            MetricQuery(
                id=f"{safe_id}_invocations",
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions=dimensions,
                stat="Sum",
            )
        )

        # Errors (Sum)
        queries.append(
            MetricQuery(
                id=f"{safe_id}_errors",
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions=dimensions,
                stat="Sum",
            )
        )

        # Throttles (Sum)
        queries.append(
            MetricQuery(
                id=f"{safe_id}_throttles",
                namespace="AWS/Lambda",
                metric_name="Throttles",
                dimensions=dimensions,
                stat="Sum",
            )
        )

        # Duration (Average, Maximum, Minimum)
        for stat, suffix in [("Average", "_avg"), ("Maximum", "_max"), ("Minimum", "_min")]:
            queries.append(
                MetricQuery(
                    id=f"{safe_id}_duration{suffix}",
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions=dimensions,
                    stat=stat,
                )
            )

        # ConcurrentExecutions (Maximum)
        queries.append(
            MetricQuery(
                id=f"{safe_id}_concurrent",
                namespace="AWS/Lambda",
                metric_name="ConcurrentExecutions",
                dimensions=dimensions,
                stat="Maximum",
            )
        )

    return queries


def _parse_lambda_metrics(safe_id: str, results: dict[str, float], days: int) -> LambdaMetrics:
    """배치 조회 결과를 LambdaMetrics로 변환"""
    return LambdaMetrics(
        period_days=days,
        invocations=int(results.get(f"{safe_id}_invocations", 0)),
        errors=int(results.get(f"{safe_id}_errors", 0)),
        throttles=int(results.get(f"{safe_id}_throttles", 0)),
        duration_avg_ms=results.get(f"{safe_id}_duration_avg", 0.0),
        duration_max_ms=results.get(f"{safe_id}_duration_max", 0.0),
        duration_min_ms=results.get(f"{safe_id}_duration_min", 0.0),
        concurrent_executions_max=int(results.get(f"{safe_id}_concurrent", 0)),
    )


def _get_last_invocation_time(
    cloudwatch, function_name: str, start_time: datetime, end_time: datetime
) -> datetime | None:
    """마지막 호출 시간 조회 (일별 데이터 기반)

    Note: 추가 API 호출이 필요하므로 필요한 경우에만 사용
    """
    from botocore.exceptions import ClientError

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=["Sum"],
        )

        datapoints = sorted(
            response.get("Datapoints", []),
            key=lambda x: x.get("Timestamp", datetime.min),
            reverse=True,
        )

        for dp in datapoints:
            if dp.get("Sum", 0) > 0:
                return dp.get("Timestamp")

    except ClientError:
        pass

    return None


def collect_functions_with_metrics(
    session,
    account_id: str,
    account_name: str,
    region: str,
    metric_days: int = 30,
) -> list[LambdaFunctionInfo]:
    """Lambda 함수 목록과 메트릭을 함께 수집 (배치 최적화)

    최적화:
    - 기존: 함수당 5-6 API 호출 (50개 함수 = 300 API)
    - 최적화: 전체 1-2 API 호출 (99% 감소)

    Args:
        session: boto3 세션
        account_id: AWS 계정 ID
        account_name: 계정명
        region: AWS 리전
        metric_days: 메트릭 조회 기간 (일)

    Returns:
        메트릭이 포함된 Lambda 함수 정보 리스트
    """
    functions = collect_functions(session, account_id, account_name, region)

    if not functions:
        return functions

    # 모든 함수의 메트릭을 배치로 수집 (최적화)
    function_names = [f.function_name for f in functions]
    metrics_map = collect_all_function_metrics(session, region, function_names, metric_days)

    # 결과 매핑
    for func in functions:
        func.metrics = metrics_map.get(func.function_name, LambdaMetrics(period_days=metric_days))

    return functions
