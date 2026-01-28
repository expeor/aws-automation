# CloudWatch Metrics 배치 조회 패턴

`shared/aws/metrics/batch_metrics.py` 모듈의 사용 패턴입니다.

GetMetricData API를 사용하여 최대 500개 메트릭을 1회 호출로 조회합니다.
(기존 get_metric_statistics()는 메트릭당 1 API 호출 필요)

예시: Lambda 50개 함수 × 6개 메트릭 = 300 API 호출 → 1회 호출로 감소 (85% 절감)

## 권장 패턴

```python
from shared.aws.metrics import (
    MetricQuery,
    batch_get_metrics,
    sanitize_metric_id,
    build_lambda_metric_queries,
    build_ec2_metric_queries,
    build_rds_metric_queries,
    build_elasticache_metric_queries,
    build_nat_metric_queries,
    build_sagemaker_endpoint_metric_queries,
)
```

---

## MetricQuery 데이터클래스

```python
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
```

### 쿼리 생성 예시

```python
# 단일 쿼리
query = MetricQuery(
    id="my_lambda_invocations_sum",
    namespace="AWS/Lambda",
    metric_name="Invocations",
    dimensions={"FunctionName": "my-lambda-func"},
    stat="Sum",
)

# 여러 통계 조회 (동일 메트릭)
queries = [
    MetricQuery(
        id="my_lambda_duration_avg",
        namespace="AWS/Lambda",
        metric_name="Duration",
        dimensions={"FunctionName": "my-lambda-func"},
        stat="Average",
    ),
    MetricQuery(
        id="my_lambda_duration_max",
        namespace="AWS/Lambda",
        metric_name="Duration",
        dimensions={"FunctionName": "my-lambda-func"},
        stat="Maximum",
    ),
]
```

---

## batch_get_metrics() 함수

```python
def batch_get_metrics(
    cloudwatch_client: Any,
    queries: list[MetricQuery],
    start_time: datetime,
    end_time: datetime,
    period: int = 86400,
    max_retries: int = 3,
) -> dict[str, float]:
    """CloudWatch 메트릭 배치 조회 (Pagination + Retry 포함)

    Args:
        cloudwatch_client: boto3 CloudWatch client
        queries: 메트릭 쿼리 목록 (최대 500개씩 분할 처리)
        start_time: 조회 시작 시간
        end_time: 조회 종료 시간
        period: 집계 주기 (초, 기본 86400=1일)
        max_retries: Throttling 시 재시도 횟수

    Returns:
        {query_id: aggregated_value} 딕셔너리
    """
```

### 기본 사용법

```python
from datetime import datetime, timedelta
from core.parallel import get_client
from shared.aws.metrics import MetricQuery, batch_get_metrics

def _collect_with_metrics(session, account_id: str, account_name: str, region: str):
    cw = get_client(session, "cloudwatch", region_name=region)

    # 시간 범위 설정
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=14)

    # 쿼리 생성
    queries = [
        MetricQuery(
            id="func1_invocations",
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions={"FunctionName": "func1"},
            stat="Sum",
        ),
        # ... 더 많은 쿼리
    ]

    # 배치 조회 (500개씩 자동 분할)
    metrics = batch_get_metrics(cw, queries, start_time, end_time)

    # 결과 사용
    func1_invocations = metrics.get("func1_invocations", 0)
```

### API 제한 사항

| 제한 | 값 | 처리 방식 |
|------|-----|----------|
| 요청당 최대 메트릭 | 500개 | 자동 분할 처리 |
| API Rate | 50 TPS/리전 | Throttling 시 exponential backoff |
| 쿼리 ID 형식 | 영문자로 시작, 영숫자/_ | `sanitize_metric_id()` 사용 |

---

## batch_get_metrics_with_stats() 함수

동일 메트릭에 대해 여러 통계를 조회할 때 사용:

```python
from shared.aws.metrics import batch_get_metrics_with_stats

queries = [
    MetricQuery(id="func1_duration_avg", ..., stat="Average"),
    MetricQuery(id="func1_duration_max", ..., stat="Maximum"),
]

# 결과: {"func1_duration": {"avg": 100.0, "max": 500.0}}
result = batch_get_metrics_with_stats(cw, queries, start_time, end_time)

avg_duration = result.get("func1_duration", {}).get("avg", 0)
max_duration = result.get("func1_duration", {}).get("max", 0)
```

---

## sanitize_metric_id() 함수

AWS MetricDataQuery ID 규칙에 맞게 변환:

```python
from shared.aws.metrics import sanitize_metric_id

sanitize_metric_id("my-lambda-func.prod")  # → "my_lambda_func_prod"
sanitize_metric_id("123-func")              # → "m_123_func" (숫자 시작 방지)
sanitize_metric_id("func/with/slashes")     # → "func_with_slashes"
```

### AWS ID 규칙

- 영문자로 시작 (숫자 시작 불가)
- 영숫자, `_`만 허용
- `-`, `.`, `/` 등 특수문자 불가
- 대소문자 구분
- 최대 255자 (200자로 제한하여 접미사 공간 확보)

---

## 서비스별 쿼리 빌더

### Lambda

```python
from shared.aws.metrics import build_lambda_metric_queries

queries = build_lambda_metric_queries(
    function_names=["func1", "func2", "func3"],
    metrics=["Invocations", "Errors", "Duration"],  # 선택적
)
# 기본 메트릭: Invocations, Errors, Throttles, Duration, ConcurrentExecutions
```

**자동 생성되는 쿼리 ID 패턴:**
- `{safe_name}_invocations_sum`
- `{safe_name}_errors_sum`
- `{safe_name}_duration_avg`, `{safe_name}_duration_max`, `{safe_name}_duration_min`
- `{safe_name}_concurrentexecutions_max`

### EC2

```python
from shared.aws.metrics import build_ec2_metric_queries

queries = build_ec2_metric_queries(
    instance_ids=["i-1234567890abcdef0"],
    metrics=["CPUUtilization", "NetworkIn", "NetworkOut"],  # 선택적
)
```

**자동 생성되는 쿼리 ID 패턴:**
- `{safe_id}_cpuutilization_avg`, `{safe_id}_cpuutilization_max`
- `{safe_id}_networkin_sum`
- `{safe_id}_networkout_sum`

### RDS

```python
from shared.aws.metrics import build_rds_metric_queries

queries = build_rds_metric_queries(
    instance_ids=["mydb-instance"],
    metrics=["DatabaseConnections", "CPUUtilization", "ReadIOPS", "WriteIOPS"],
)
```

### ElastiCache

```python
from shared.aws.metrics import build_elasticache_metric_queries

# Redis Replication Group
queries = build_elasticache_metric_queries(
    cluster_ids=["my-redis-cluster"],
    dimension_name="ReplicationGroupId",  # 또는 "CacheClusterId"
    metrics=["CurrConnections", "CPUUtilization"],
)
```

### NAT Gateway

```python
from shared.aws.metrics import build_nat_metric_queries

queries = build_nat_metric_queries(
    nat_gateway_ids=["nat-0123456789abcdef0"],
    # 기본 메트릭: BytesOutToDestination, BytesInFromSource, PacketsOutToDestination,
    #             PacketsInFromSource, ActiveConnectionCount, ConnectionAttemptCount
)
```

### SageMaker Endpoint

```python
from shared.aws.metrics import build_sagemaker_endpoint_metric_queries

queries = build_sagemaker_endpoint_metric_queries(
    endpoint_names=["my-endpoint"],
    metrics=["Invocations", "InvocationsPerInstance"],
)
```

---

## 전체 예시 (Lambda 미사용 분석)

```python
from datetime import datetime, timedelta
from core.parallel import get_client, parallel_collect
from shared.aws.metrics import build_lambda_metric_queries, batch_get_metrics

def _collect_lambda_with_metrics(session, account_id: str, account_name: str, region: str):
    """Lambda 함수 수집 + CloudWatch 메트릭 조회"""
    lambda_client = get_client(session, "lambda", region_name=region)
    cw = get_client(session, "cloudwatch", region_name=region)

    # 1. Lambda 함수 목록 수집
    functions = []
    paginator = lambda_client.get_paginator("list_functions")
    for page in paginator.paginate():
        functions.extend(page.get("Functions", []))

    if not functions:
        return None

    # 2. CloudWatch 쿼리 생성
    function_names = [f["FunctionName"] for f in functions]
    queries = build_lambda_metric_queries(function_names)

    # 3. 메트릭 배치 조회 (14일)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=14)
    metrics = batch_get_metrics(cw, queries, start_time, end_time)

    # 4. 분석 - 미사용 함수 식별
    results = []
    for func in functions:
        name = func["FunctionName"]
        safe_name = sanitize_metric_id(name)

        invocations = metrics.get(f"{safe_name}_invocations_sum", 0)
        errors = metrics.get(f"{safe_name}_errors_sum", 0)

        if invocations == 0:
            results.append({
                "function_name": name,
                "status": "unused",
                "invocations_14d": invocations,
            })

    return results

def run(ctx) -> None:
    result = parallel_collect(ctx, _collect_lambda_with_metrics, service="lambda")
    # ...
```

---

## Throttling 처리

`batch_get_metrics()`는 자동으로 Throttling을 처리합니다:

1. `Throttling` 에러 발생 시 재시도
2. Exponential backoff: 2^retry 초 대기 (2초, 4초, 8초...)
3. 최대 재시도 횟수: `max_retries` (기본 3)

```python
# 커스텀 재시도 횟수
metrics = batch_get_metrics(
    cw, queries, start_time, end_time,
    max_retries=5,  # 최대 5회 재시도
)
```

---

## 참조

- `plugins/cloudwatch/common/batch_metrics.py` - 배치 메트릭 유틸리티
- `plugins/cloudwatch/common/__init__.py` - 공개 API
- `.claude/skills/parallel-execution-patterns.md` - 병렬 처리 패턴
- `.claude/skills/error-handling-patterns.md` - 에러 처리 패턴
