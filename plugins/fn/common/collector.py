"""
plugins/fn/common/collector.py - Lambda 함수 수집

Lambda 함수 정보 및 CloudWatch 메트릭 수집 공통 로직
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from botocore.exceptions import ClientError

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
    last_invocation_time: Optional[datetime] = None


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
    last_modified: Optional[datetime]

    # 실행 환경
    role: str
    vpc_config: Optional[Dict] = None
    environment_variables: int = 0

    # 메타
    account_id: str = ""
    account_name: str = ""
    region: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    # 메트릭 (나중에 채워짐)
    metrics: Optional[LambdaMetrics] = None

    # Provisioned Concurrency (있는 경우)
    provisioned_concurrency: int = 0
    reserved_concurrency: Optional[int] = None

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
) -> List[LambdaFunctionInfo]:
    """Lambda 함수 목록 수집

    Args:
        session: boto3 세션
        account_id: AWS 계정 ID
        account_name: 계정명
        region: AWS 리전

    Returns:
        Lambda 함수 정보 리스트
    """
    functions = []

    try:
        lambda_client = session.client("lambda", region_name=region)

        # 함수 목록 조회
        paginator = lambda_client.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                # 기본 정보
                function_name = fn.get("FunctionName", "")

                # 태그 조회
                tags = {}
                try:
                    tag_response = lambda_client.list_tags(Resource=fn.get("FunctionArn", ""))
                    tags = tag_response.get("Tags", {})
                except ClientError:
                    pass

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
                    try:
                        # ISO 8601 형식 파싱
                        last_modified = datetime.fromisoformat(lm_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

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

                # Provisioned Concurrency 조회
                try:
                    pc_response = lambda_client.list_provisioned_concurrency_configs(
                        FunctionName=function_name
                    )
                    for pc in pc_response.get("ProvisionedConcurrencyConfigs", []):
                        func_info.provisioned_concurrency += pc.get("AllocatedProvisionedConcurrentExecutions", 0)
                except ClientError:
                    pass

                # Reserved Concurrency 조회
                try:
                    concurrency = lambda_client.get_function_concurrency(FunctionName=function_name)
                    func_info.reserved_concurrency = concurrency.get("ReservedConcurrentExecutions")
                except ClientError:
                    pass

                functions.append(func_info)

    except ClientError as e:
        logger.warning(f"Lambda 함수 수집 실패 [{account_id}/{region}]: {e}")

    return functions


def collect_function_metrics(
    session,
    region: str,
    function_name: str,
    days: int = 30,
) -> LambdaMetrics:
    """Lambda 함수 CloudWatch 메트릭 수집

    Args:
        session: boto3 세션
        region: AWS 리전
        function_name: Lambda 함수 이름
        days: 조회 기간 (일)

    Returns:
        Lambda 메트릭
    """
    metrics = LambdaMetrics(period_days=days)

    try:
        cloudwatch = session.client("cloudwatch", region_name=region)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        dimensions = [{"Name": "FunctionName", "Value": function_name}]

        # Invocations
        invocations_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,  # 전체 기간
            Statistics=["Sum"],
        )
        for dp in invocations_response.get("Datapoints", []):
            metrics.invocations += int(dp.get("Sum", 0))

        # Errors
        errors_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Errors",
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,
            Statistics=["Sum"],
        )
        for dp in errors_response.get("Datapoints", []):
            metrics.errors += int(dp.get("Sum", 0))

        # Throttles
        throttles_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Throttles",
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,
            Statistics=["Sum"],
        )
        for dp in throttles_response.get("Datapoints", []):
            metrics.throttles += int(dp.get("Sum", 0))

        # Duration (평균, 최대, 최소)
        duration_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Duration",
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,
            Statistics=["Average", "Maximum", "Minimum"],
        )
        for dp in duration_response.get("Datapoints", []):
            metrics.duration_avg_ms = dp.get("Average", 0)
            metrics.duration_max_ms = dp.get("Maximum", 0)
            metrics.duration_min_ms = dp.get("Minimum", 0)

        # ConcurrentExecutions
        concurrent_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="ConcurrentExecutions",
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,
            Statistics=["Maximum"],
        )
        for dp in concurrent_response.get("Datapoints", []):
            val = int(dp.get("Maximum", 0))
            if val > metrics.concurrent_executions_max:
                metrics.concurrent_executions_max = val

        # 마지막 호출 시간 추정 (일별 데이터에서)
        if metrics.invocations > 0:
            daily_response = cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,  # 1일
                Statistics=["Sum"],
            )
            datapoints = sorted(
                daily_response.get("Datapoints", []),
                key=lambda x: x.get("Timestamp", datetime.min),
                reverse=True,
            )
            for dp in datapoints:
                if dp.get("Sum", 0) > 0:
                    metrics.last_invocation_time = dp.get("Timestamp")
                    break

    except ClientError as e:
        logger.warning(f"Lambda 메트릭 수집 실패 [{function_name}]: {e}")

    return metrics


def collect_functions_with_metrics(
    session,
    account_id: str,
    account_name: str,
    region: str,
    metric_days: int = 30,
) -> List[LambdaFunctionInfo]:
    """Lambda 함수 목록과 메트릭을 함께 수집

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

    for func in functions:
        func.metrics = collect_function_metrics(session, region, func.function_name, metric_days)

    return functions
