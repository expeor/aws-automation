"""
shared/aws/metrics/batch_metrics.py - CloudWatch Batch Metrics Utility

GetMetricData API를 사용한 배치 메트릭 조회 (85% API 호출 감소)

기존 get_metric_statistics()는 메트릭당 1 API 호출이 필요하지만,
get_metric_data()는 최대 500개 메트릭을 1회 호출로 조회 가능.

예시:
    Lambda 50개 함수 × 6개 메트릭 = 300 API 호출 → 1회 호출로 감소
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from .session_cache import MetricSessionCache

logger = logging.getLogger(__name__)


@dataclass
class MetricQuery:
    """CloudWatch 메트릭 쿼리 정의

    Attributes:
        id: 쿼리 식별자 (결과 매핑용, 영문/숫자/_ 만 허용)
        namespace: AWS 네임스페이스 (예: "AWS/Lambda")
        metric_name: 메트릭 이름 (예: "Invocations")
        dimensions: 차원 딕셔너리 (예: {"FunctionName": "my-func"})
        stat: 통계 타입 (Sum, Average, Maximum, Minimum)
    """

    id: str
    namespace: str
    metric_name: str
    dimensions: dict[str, str]
    stat: str = "Sum"


def batch_get_metrics(
    cloudwatch_client: Any,
    queries: list[MetricQuery],
    start_time: datetime,
    end_time: datetime,
    period: int = 86400,
    max_retries: int = 3,
    cache: MetricSessionCache | None = None,
) -> dict[str, float]:
    """CloudWatch 메트릭 배치 조회 (Pagination + Retry + 캐싱 지원)

    Args:
        cloudwatch_client: boto3 CloudWatch client
        queries: 메트릭 쿼리 목록 (최대 500개씩 분할 처리)
        start_time: 조회 시작 시간
        end_time: 조회 종료 시간
        period: 집계 주기 (초, 기본 86400=1일)
        max_retries: Throttling 시 재시도 횟수
        cache: 세션 캐시 (선택적, None이면 전역 캐시 자동 사용)

    Returns:
        {query_id: aggregated_value} 딕셔너리

    Note:
        - GetMetricData API 제한: 50 TPS/리전
        - 요청당 최대 500개 메트릭
        - Throttling 시 exponential backoff 적용
        - cache=None이면 전역 캐시(get_global_cache()) 자동 사용
    """
    if not queries:
        return {}

    # 전역 캐시 자동 사용
    if cache is None:
        from .session_cache import get_global_cache

        cache = get_global_cache()

    results: dict[str, float] = {}
    queries_to_fetch: list[MetricQuery] = []

    # 캐시 키 생성 함수
    def make_cache_key(q: MetricQuery) -> str:
        dims = "|".join(f"{k}={v}" for k, v in sorted(q.dimensions.items()))
        return f"{q.namespace}|{q.metric_name}|{dims}|{q.stat}|{period}|{start_time.isoformat()}|{end_time.isoformat()}"

    # 캐시에서 먼저 조회
    if cache:
        for q in queries:
            cache_key = make_cache_key(q)
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                results[q.id] = cached_value
            else:
                queries_to_fetch.append(q)

        if queries_to_fetch:
            logger.debug(
                f"CloudWatch 캐시: {len(queries) - len(queries_to_fetch)}/{len(queries)} 히트, "
                f"{len(queries_to_fetch)}개 API 호출 필요"
            )
    else:
        queries_to_fetch = queries

    # 캐시 미스된 쿼리만 API 호출
    if queries_to_fetch:
        fetched = _fetch_metrics(cloudwatch_client, queries_to_fetch, start_time, end_time, period, max_retries)
        results.update(fetched)

        # 결과를 캐시에 저장
        if cache:
            for q in queries_to_fetch:
                cache_key = make_cache_key(q)
                cache.set(cache_key, fetched.get(q.id, 0.0))

    return results


def _fetch_metrics(
    cloudwatch_client: Any,
    queries: list[MetricQuery],
    start_time: datetime,
    end_time: datetime,
    period: int,
    max_retries: int,
) -> dict[str, float]:
    """CloudWatch API 호출 (내부 함수)

    Args:
        cloudwatch_client: boto3 CloudWatch client
        queries: 메트릭 쿼리 목록
        start_time: 조회 시작 시간
        end_time: 조회 종료 시간
        period: 집계 주기 (초)
        max_retries: Throttling 시 재시도 횟수

    Returns:
        {query_id: aggregated_value} 딕셔너리
    """
    results: dict[str, float] = {}

    # 500개 단위로 분할 (API 제한)
    for chunk in _chunks(queries, 500):
        metric_data_queries = [
            {
                "Id": q.id,
                "MetricStat": {
                    "Metric": {
                        "Namespace": q.namespace,
                        "MetricName": q.metric_name,
                        "Dimensions": [{"Name": k, "Value": v} for k, v in q.dimensions.items()],
                    },
                    "Period": period,
                    "Stat": q.stat,
                },
            }
            for q in chunk
        ]

        # Pagination + Retry loop
        next_token = None
        retries = 0

        while True:
            try:
                params: dict[str, Any] = {
                    "MetricDataQueries": metric_data_queries,
                    "StartTime": start_time,
                    "EndTime": end_time,
                }
                if next_token:
                    params["NextToken"] = next_token

                response = cloudwatch_client.get_metric_data(**params)

                # 결과 처리
                for result in response.get("MetricDataResults", []):
                    values = result.get("Values", [])
                    query_id = result["Id"]

                    # 기존 값과 합산 (pagination)
                    if values:
                        current = results.get(query_id, 0.0)
                        results[query_id] = current + sum(values)
                    elif query_id not in results:
                        results[query_id] = 0.0

                # 다음 페이지 확인
                next_token = response.get("NextToken")
                if not next_token:
                    break

                retries = 0  # 성공 시 재시도 카운터 리셋

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "Throttling" and retries < max_retries:
                    retries += 1
                    wait_time = 2**retries  # Exponential backoff
                    logger.debug(f"CloudWatch Throttling, retry {retries}/{max_retries} after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                logger.warning(f"CloudWatch batch_get_metrics 오류: {error_code}")
                raise

    return results


def batch_get_metrics_with_stats(
    cloudwatch_client: Any,
    queries: list[MetricQuery],
    start_time: datetime,
    end_time: datetime,
    period: int = 86400,
    max_retries: int = 3,
) -> dict[str, dict[str, float]]:
    """여러 통계를 포함한 CloudWatch 메트릭 배치 조회

    동일 메트릭에 대해 여러 통계(Sum, Average, Maximum 등)를 조회할 때 사용.
    query.id 에 통계 타입을 포함시켜 구분.

    Args:
        cloudwatch_client: boto3 CloudWatch client
        queries: 메트릭 쿼리 목록 (동일 메트릭, 다른 stat 가능)
        start_time: 조회 시작 시간
        end_time: 조회 종료 시간
        period: 집계 주기 (초)
        max_retries: 재시도 횟수

    Returns:
        {base_id: {stat: value}} 중첩 딕셔너리

    Example:
        queries = [
            MetricQuery(id="func1_duration_avg", ..., stat="Average"),
            MetricQuery(id="func1_duration_max", ..., stat="Maximum"),
        ]
        result = batch_get_metrics_with_stats(cw, queries, ...)
        # {"func1_duration": {"avg": 100.0, "max": 500.0}}
    """
    raw_results = batch_get_metrics(cloudwatch_client, queries, start_time, end_time, period, max_retries)

    # ID에서 stat 타입 분리하여 중첩 딕셔너리 생성
    parsed: dict[str, dict[str, float]] = {}
    stat_suffixes = ["_sum", "_avg", "_max", "_min", "_average", "_maximum", "_minimum"]

    for query_id, value in raw_results.items():
        base_id = query_id
        stat_key = "sum"  # default

        for suffix in stat_suffixes:
            if query_id.endswith(suffix):
                base_id = query_id[: -len(suffix)]
                stat_key = suffix[1:]  # "_avg" -> "avg"
                break

        if base_id not in parsed:
            parsed[base_id] = {}
        parsed[base_id][stat_key] = value

    return parsed


def _chunks(lst: list, n: int):
    """리스트를 n개씩 분할"""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def sanitize_metric_id(name: str) -> str:
    """AWS MetricDataQuery ID 규칙에 맞게 변환

    AWS 제약:
    - 영문자로 시작
    - 영숫자, `_`만 허용
    - `-`, `.` 등 특수문자 불가
    - 대소문자 구분
    - 최대 255자

    Example:
        sanitize_metric_id("my-lambda-func.prod")  # "my_lambda_func_prod"
        sanitize_metric_id("123-func")             # "m_123_func"
    """
    # 특수문자를 _로 변환
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    # 연속 underscore 정리
    sanitized = re.sub(r"_+", "_", sanitized)

    # 숫자로 시작하면 prefix 추가
    if sanitized and sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"

    # 빈 문자열 방지
    if not sanitized:
        sanitized = "metric"

    # 최대 길이 제한 (255자, 접미사 공간 확보를 위해 200자로 제한)
    return sanitized[:200]


# =============================================================================
# 서비스별 헬퍼 함수
# =============================================================================


def build_lambda_metric_queries(
    function_names: list[str],
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """Lambda 함수용 메트릭 쿼리 생성

    Args:
        function_names: Lambda 함수 이름 목록
        metrics: 조회할 메트릭 목록 (기본: 모든 메트릭)

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = ["Invocations", "Errors", "Throttles", "Duration", "ConcurrentExecutions"]

    queries = []
    for func_name in function_names:
        safe_id = sanitize_metric_id(func_name)
        dimensions = {"FunctionName": func_name}

        for metric in metrics:
            metric_lower = metric.lower()

            if metric == "Duration":
                # Duration은 여러 통계 필요
                for stat, suffix in [("Average", "_avg"), ("Maximum", "_max"), ("Minimum", "_min")]:
                    queries.append(
                        MetricQuery(
                            id=f"{safe_id}_{metric_lower}{suffix}",
                            namespace="AWS/Lambda",
                            metric_name=metric,
                            dimensions=dimensions,
                            stat=stat,
                        )
                    )
            elif metric == "ConcurrentExecutions":
                queries.append(
                    MetricQuery(
                        id=f"{safe_id}_{metric_lower}_max",
                        namespace="AWS/Lambda",
                        metric_name=metric,
                        dimensions=dimensions,
                        stat="Maximum",
                    )
                )
            else:
                queries.append(
                    MetricQuery(
                        id=f"{safe_id}_{metric_lower}_sum",
                        namespace="AWS/Lambda",
                        metric_name=metric,
                        dimensions=dimensions,
                        stat="Sum",
                    )
                )

    return queries


def build_rds_metric_queries(
    instance_ids: list[str],
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """RDS 인스턴스용 메트릭 쿼리 생성

    Args:
        instance_ids: RDS 인스턴스 ID 목록
        metrics: 조회할 메트릭 목록

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = ["DatabaseConnections", "CPUUtilization", "ReadIOPS", "WriteIOPS"]

    queries = []
    for db_id in instance_ids:
        safe_id = sanitize_metric_id(db_id)
        dimensions = {"DBInstanceIdentifier": db_id}

        for metric in metrics:
            metric_lower = metric.lower()
            queries.append(
                MetricQuery(
                    id=f"{safe_id}_{metric_lower}_avg",
                    namespace="AWS/RDS",
                    metric_name=metric,
                    dimensions=dimensions,
                    stat="Average",
                )
            )

    return queries


def build_elasticache_metric_queries(
    cluster_ids: list[str],
    dimension_name: str = "ReplicationGroupId",
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """ElastiCache 클러스터용 메트릭 쿼리 생성

    Args:
        cluster_ids: 클러스터 ID 목록
        dimension_name: 차원 이름 (ReplicationGroupId 또는 CacheClusterId)
        metrics: 조회할 메트릭 목록

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = ["CurrConnections", "CPUUtilization"]

    queries = []
    for cluster_id in cluster_ids:
        safe_id = sanitize_metric_id(cluster_id)
        dimensions = {dimension_name: cluster_id}

        for metric in metrics:
            metric_lower = metric.lower()
            queries.append(
                MetricQuery(
                    id=f"{safe_id}_{metric_lower}_avg",
                    namespace="AWS/ElastiCache",
                    metric_name=metric,
                    dimensions=dimensions,
                    stat="Average",
                )
            )

    return queries


def build_nat_metric_queries(
    nat_gateway_ids: list[str],
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """NAT Gateway용 메트릭 쿼리 생성

    Args:
        nat_gateway_ids: NAT Gateway ID 목록
        metrics: 조회할 메트릭 목록

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = [
            "BytesOutToDestination",
            "BytesInFromSource",
            "PacketsOutToDestination",
            "PacketsInFromSource",
            "ActiveConnectionCount",
            "ConnectionAttemptCount",
        ]

    queries = []
    for nat_id in nat_gateway_ids:
        safe_id = sanitize_metric_id(nat_id)
        dimensions = {"NatGatewayId": nat_id}

        for metric in metrics:
            metric_lower = metric.lower()
            queries.append(
                MetricQuery(
                    id=f"{safe_id}_{metric_lower}_sum",
                    namespace="AWS/NATGateway",
                    metric_name=metric,
                    dimensions=dimensions,
                    stat="Sum",
                )
            )

    return queries


def build_ec2_metric_queries(
    instance_ids: list[str],
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """EC2 인스턴스용 메트릭 쿼리 생성

    Args:
        instance_ids: EC2 인스턴스 ID 목록
        metrics: 조회할 메트릭 목록

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = ["CPUUtilization", "NetworkIn", "NetworkOut"]

    queries = []
    for instance_id in instance_ids:
        safe_id = sanitize_metric_id(instance_id)
        dimensions = {"InstanceId": instance_id}

        for metric in metrics:
            metric_lower = metric.lower()
            if metric == "CPUUtilization":
                # CPU는 Average와 Maximum 모두 필요
                for stat, suffix in [("Average", "_avg"), ("Maximum", "_max")]:
                    queries.append(
                        MetricQuery(
                            id=f"{safe_id}_{metric_lower}{suffix}",
                            namespace="AWS/EC2",
                            metric_name=metric,
                            dimensions=dimensions,
                            stat=stat,
                        )
                    )
            else:
                # Network 메트릭은 Sum
                queries.append(
                    MetricQuery(
                        id=f"{safe_id}_{metric_lower}_sum",
                        namespace="AWS/EC2",
                        metric_name=metric,
                        dimensions=dimensions,
                        stat="Sum",
                    )
                )

    return queries


def build_sagemaker_endpoint_metric_queries(
    endpoint_names: list[str],
    metrics: list[str] | None = None,
) -> list[MetricQuery]:
    """SageMaker Endpoint용 메트릭 쿼리 생성

    Args:
        endpoint_names: Endpoint 이름 목록
        metrics: 조회할 메트릭 목록

    Returns:
        MetricQuery 목록
    """
    if metrics is None:
        metrics = ["Invocations", "InvocationsPerInstance"]

    queries = []
    for endpoint_name in endpoint_names:
        safe_id = sanitize_metric_id(endpoint_name)
        dimensions = {"EndpointName": endpoint_name}

        for metric in metrics:
            metric_lower = metric.lower()
            queries.append(
                MetricQuery(
                    id=f"{safe_id}_{metric_lower}_sum",
                    namespace="AWS/SageMaker",
                    metric_name=metric,
                    dimensions=dimensions,
                    stat="Sum",
                )
            )

    return queries
