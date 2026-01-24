# Performance Agent

코드 성능을 분석하고 최적화하는 에이전트입니다.

## MCP 도구 활용

### aws-documentation
AWS API 제한 및 최적화 문서:
```
mcp__aws-documentation__search("EC2 API rate limits")
mcp__aws-documentation__search("boto3 paginator best practices")
```

### context7
Python 성능 최적화 패턴:
```
mcp__context7__get_library_docs("concurrent.futures", "ThreadPoolExecutor")
mcp__context7__get_library_docs("functools", "lru_cache")
```

| 분석 영역 | MCP 도구 |
|----------|----------|
| AWS API 제한/할당량 | aws-documentation |
| 병렬 처리 패턴 | context7 |
| 캐싱 전략 | context7 |

## 역할

- 성능 병목 지점 분석
- 최적화 방안 제안
- AWS API 호출 최적화
- 메모리/CPU 사용 개선

## 분석 영역

### 1. AWS API 호출

#### 문제 패턴

```python
# ❌ N+1 호출 문제
for instance in instances:
    tags = client.describe_tags(Resources=[instance["InstanceId"]])

# ❌ 페이지네이션 미사용
response = client.describe_instances()  # 최대 1000개
```

#### 최적화

```python
# ✅ 배치 호출
instance_ids = [i["InstanceId"] for i in instances]
tags = client.describe_tags(Resources=instance_ids)

# ✅ 페이지네이터 사용
paginator = client.get_paginator("describe_instances")
for page in paginator.paginate():
    instances.extend(page["Reservations"])
```

### 2. 병렬 처리

#### 문제 패턴

```python
# ❌ 순차 처리
for account in accounts:
    for region in regions:
        result = analyze(account, region)  # 순차 실행
```

#### 최적화

```python
# ✅ parallel_collect 사용
from core.parallel import parallel_collect

result = parallel_collect(ctx, _collect_and_analyze, max_workers=20)
```

### 3. 메모리 사용

#### 문제 패턴

```python
# ❌ 전체 데이터 메모리 적재
all_data = []
for page in paginator.paginate():
    all_data.extend(page["Items"])  # 메모리 누적

# 분석
results = analyze(all_data)
```

#### 최적화

```python
# ✅ 스트리밍 처리
def process_pages(paginator):
    for page in paginator.paginate():
        yield from page["Items"]

# 또는 청크 처리
for chunk in chunked(items, size=1000):
    partial_result = analyze(chunk)
    results.append(partial_result)
```

### 4. 중복 API 호출

#### 문제 패턴

```python
# ❌ 동일 데이터 반복 조회
def analyze_volume(volume_id):
    volume = client.describe_volumes(VolumeIds=[volume_id])
    snapshots = client.describe_snapshots(Filters=[...])
    return process(volume, snapshots)

for vol_id in volume_ids:
    result = analyze_volume(vol_id)  # 각각 API 호출
```

#### 최적화

```python
# ✅ 캐싱 또는 배치 조회
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_volume(volume_id):
    return client.describe_volumes(VolumeIds=[volume_id])

# 또는 일괄 조회 후 매핑
all_volumes = {v["VolumeId"]: v for v in client.describe_volumes()["Volumes"]}
```

### 5. Rate Limiting

#### 문제 패턴

```python
# ❌ Rate limit 미고려
for resource in resources:
    client.describe_resource(ResourceId=resource["Id"])  # 쓰로틀링 발생 가능
```

#### 최적화

```python
# ✅ get_client 사용 (내장 Rate limiter)
from core.parallel import get_client

client = get_client(session, "ec2", region_name=region)

# ✅ 또는 명시적 Rate limiter
from core.parallel import get_rate_limiter

limiter = get_rate_limiter("ec2")
for resource in resources:
    limiter.acquire()
    client.describe_resource(ResourceId=resource["Id"])
```

## 벤치마크 기준

### 실행 시간 기준

| 시나리오 | 목표 | 허용 범위 |
|---------|------|----------|
| 10계정 × 10리전 | < 2분 | < 3분 |
| 단일 계정/리전 | < 10초 | < 30초 |
| 대용량 (100+ 리소스) | < 30초 | < 1분 |

### API 호출 기준

| 최적화 영역 | 목표 감소율 | 측정 방법 |
|------------|-----------|----------|
| CloudWatch 배치 | > 85% | 개별 vs 배치 호출 수 비교 |
| 리소스 캐싱 | > 50% | 중복 API 호출 제거 |
| Paginator | 100% 커버 | 대용량 응답 누락 방지 |

### 메모리 기준

| 시나리오 | 피크 메모리 | 측정 도구 |
|---------|-----------|----------|
| 10,000 리소스 | < 200MB | tracemalloc |
| 100,000 리소스 | < 500MB | tracemalloc |
| 스트리밍 처리 | < 50MB | tracemalloc |

### 벤치마크 예시

```python
import time
from contextlib import contextmanager

@contextmanager
def benchmark(name: str, threshold_seconds: float):
    """벤치마크 컨텍스트 매니저"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start

    status = "✅ PASS" if elapsed < threshold_seconds else "❌ FAIL"
    print(f"{status} {name}: {elapsed:.2f}s (threshold: {threshold_seconds}s)")

# 사용
with benchmark("10계정 수집", threshold_seconds=120):
    result = parallel_collect(ctx, _collect_and_analyze, service="ec2")
```

## CloudWatch 배치 최적화

### 기본 개념

GetMetricData API는 최대 500개 메트릭을 1회 호출로 조회 가능합니다.
기존 get_metric_statistics()는 메트릭당 1회 호출이 필요합니다.

| 방식 | 50 Lambda × 5 메트릭 | API 호출 |
|------|---------------------|---------|
| 레거시 (개별) | 250개 메트릭 | 250회 |
| 배치 (GetMetricData) | 250개 메트릭 | 1회 |
| **절감율** | - | **99.6%** |

### 사용 패턴

```python
from datetime import datetime, timedelta
from plugins.cloudwatch.common.batch_metrics import (
    batch_get_metrics,
    build_lambda_metric_queries,
    MetricQuery,
    sanitize_metric_id,
)

# 1. 함수별 쿼리 빌드 (헬퍼 사용)
function_names = [f["FunctionName"] for f in functions]
queries = build_lambda_metric_queries(
    function_names,
    metrics=["Invocations", "Errors", "Duration", "Throttles"]
)

# 2. 배치 조회
end_time = datetime.now()
start_time = end_time - timedelta(days=30)

results = batch_get_metrics(
    cloudwatch_client=cw_client,
    queries=queries,
    start_time=start_time,
    end_time=end_time,
    period=86400  # 1일 단위 집계
)

# 3. 결과 매핑
# results: {"func1_invocations_sum": 1000, "func1_errors_sum": 5, ...}
for func in functions:
    safe_id = sanitize_metric_id(func["FunctionName"])
    invocations = results.get(f"{safe_id}_invocations_sum", 0)
    errors = results.get(f"{safe_id}_errors_sum", 0)
```

### 서비스별 헬퍼

| 서비스 | 헬퍼 함수 | 기본 메트릭 |
|--------|----------|-----------|
| Lambda | `build_lambda_metric_queries()` | Invocations, Errors, Duration |
| RDS | `build_rds_metric_queries()` | DatabaseConnections, CPUUtilization |
| EC2 | `build_ec2_metric_queries()` | CPUUtilization, NetworkIn/Out |
| NAT Gateway | `build_nat_metric_queries()` | BytesOut, PacketsOut |
| ElastiCache | `build_elasticache_metric_queries()` | CurrConnections, CPUUtilization |

### 커스텀 쿼리

```python
# 직접 MetricQuery 생성
queries = [
    MetricQuery(
        id=sanitize_metric_id(f"{resource_id}_custom_metric"),
        namespace="AWS/CustomNamespace",
        metric_name="CustomMetric",
        dimensions={"ResourceId": resource_id},
        stat="Average"
    )
    for resource_id in resource_ids
]
```

## InventoryCollector 활용

### 기본 사용법

```python
from plugins.resource_explorer.common.collector import InventoryCollector

def analyze_resources(ctx):
    collector = InventoryCollector(ctx)

    # 한 번 수집하면 세션 내 캐싱
    ec2_instances = collector.collect_ec2()
    ebs_volumes = collector.collect_ebs_volumes()
    security_groups = collector.collect_security_groups()

    # 분석 로직...
```

### 지원 리소스 카테고리

| 카테고리 | 메서드 | 반환 타입 |
|---------|--------|----------|
| **Compute** | `collect_ec2()` | `list[EC2Instance]` |
| | `collect_ebs_volumes()` | `list[EBSVolume]` |
| | `collect_lambda_functions()` | `list[LambdaFunction]` |
| **Network** | `collect_vpcs()` | `list[VPC]` |
| | `collect_subnets()` | `list[Subnet]` |
| | `collect_security_groups()` | `list[SecurityGroup]` |
| **Database** | `collect_rds_instances()` | `list[RDSInstance]` |
| | `collect_dynamodb_tables()` | `list[DynamoDBTable]` |
| **Load Balancing** | `collect_load_balancers()` | `list[LoadBalancer]` |
| | `collect_target_groups()` | `list[TargetGroup]` |

### 캐싱 활용 패턴

```python
# ❌ 비효율적: 여러 도구에서 중복 수집
def tool1(ctx):
    ec2 = ctx.provider.get_session().client("ec2")
    instances = ec2.describe_instances()  # API 호출

def tool2(ctx):
    ec2 = ctx.provider.get_session().client("ec2")
    instances = ec2.describe_instances()  # 중복 API 호출!

# ✅ 효율적: InventoryCollector 캐싱 활용
def tool1(ctx):
    collector = InventoryCollector(ctx)
    instances = collector.collect_ec2()  # API 호출 + 캐싱

def tool2(ctx):
    collector = InventoryCollector(ctx)
    instances = collector.collect_ec2()  # 캐시에서 반환 (API 호출 없음)
```

### 리소스 연관 분석

```python
def analyze_with_relationships(ctx):
    """리소스 간 관계 분석"""
    collector = InventoryCollector(ctx)

    # 모든 필요 리소스 수집 (병렬 + 캐싱)
    instances = collector.collect_ec2()
    volumes = collector.collect_ebs_volumes()
    security_groups = collector.collect_security_groups()

    # 인스턴스 ID → 인스턴스 매핑
    instance_map = {i.instance_id: i for i in instances}

    # 볼륨-인스턴스 연관 분석
    for volume in volumes:
        if volume.attachments:
            instance_id = volume.attachments[0].get("InstanceId")
            instance = instance_map.get(instance_id)
            # 연관 분석...
```

## 메모리 프로파일링

### tracemalloc 사용

```python
import tracemalloc
from contextlib import contextmanager

@contextmanager
def memory_profile(name: str, threshold_mb: float = 200):
    """메모리 프로파일링 컨텍스트"""
    tracemalloc.start()
    yield
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / 1024 / 1024
    status = "✅" if peak_mb < threshold_mb else "❌"
    print(f"{status} {name}: 피크 {peak_mb:.1f}MB (threshold: {threshold_mb}MB)")

# 사용
with memory_profile("대용량 수집", threshold_mb=200):
    data = collect_large_dataset()
```

### 스트리밍 처리 패턴

```python
# ❌ 메모리 집약적: 전체 로드
def batch_process(paginator):
    all_items = []
    for page in paginator.paginate():
        all_items.extend(page["Items"])  # 메모리에 전체 적재
    return analyze(all_items)

# ✅ 메모리 효율적: 스트리밍
def stream_process(paginator):
    for page in paginator.paginate():
        for item in page["Items"]:
            yield item  # 한 번에 하나씩 처리

# 또는 청크 처리
def chunked_process(paginator, chunk_size: int = 1000):
    chunk = []
    for page in paginator.paginate():
        for item in page["Items"]:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield from analyze_chunk(chunk)
                chunk = []
    if chunk:
        yield from analyze_chunk(chunk)
```

### 대용량 데이터 처리 가이드

| 데이터 규모 | 권장 패턴 | 메모리 사용 |
|------------|----------|-----------|
| < 1,000건 | 배치 (리스트) | 낮음 |
| 1,000~10,000건 | 청크 처리 | 중간 |
| > 10,000건 | 스트리밍 (제너레이터) | 최소 |

```python
def process_with_strategy(items: list, count: int):
    """데이터 규모에 따른 처리 전략 선택"""
    if count < 1000:
        # 배치 처리
        return analyze_batch(items)
    elif count < 10000:
        # 청크 처리
        results = []
        for chunk in chunks(items, 1000):
            results.extend(analyze_chunk(chunk))
        return results
    else:
        # 스트리밍 처리
        return list(stream_analyze(items))
```

## 성능 측정

### 프로파일링

```python
import cProfile
import pstats

def profile_run():
    profiler = cProfile.Profile()
    profiler.enable()

    # 측정 대상 코드
    run(ctx)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    stats.print_stats(20)
```

### 시간 측정

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"{name}: {elapsed:.2f}s")

with timer("데이터 수집"):
    data = collect_data()

with timer("분석"):
    result = analyze(data)
```

### API 호출 카운트

```python
from unittest.mock import patch

call_counts = {}

def count_calls(original_method):
    def wrapper(*args, **kwargs):
        method_name = args[0] if args else "unknown"
        call_counts[method_name] = call_counts.get(method_name, 0) + 1
        return original_method(*args, **kwargs)
    return wrapper

# 측정
with patch.object(client, "describe_instances", count_calls(client.describe_instances)):
    run(ctx)

print(f"API 호출 횟수: {call_counts}")
```

## 성능 체크리스트

### API 최적화

- [ ] Paginator 사용 여부
- [ ] 배치 API 활용 (describe_tags 등)
- [ ] 불필요한 API 호출 제거
- [ ] 캐싱 적용 가능 여부

### 병렬 처리

- [ ] parallel_collect 사용
- [ ] 적절한 max_workers 설정
- [ ] Rate limiter 적용

### 메모리

- [ ] 대용량 데이터 스트리밍 처리
- [ ] 불필요한 데이터 복사 방지
- [ ] 제너레이터 활용

### 일반

- [ ] 중복 계산 제거
- [ ] 효율적인 자료구조 (dict lookup vs list search)
- [ ] 조기 종료 조건

## 출력 형식

```markdown
## 성능 분석: plugins/{service}/{tool}.py

### 발견된 문제

| 문제 | 위치 | 영향 | 심각도 |
|------|------|------|--------|
| N+1 API 호출 | Line 45-50 | API 호출 100x 증가 | High |
| 페이지네이션 미사용 | Line 78 | 대용량 데이터 누락 | Medium |
| 순차 처리 | Line 120-130 | 실행 시간 10x | High |

### 최적화 제안

1. **N+1 해결** (예상 개선: 95% API 감소)
   ```python
   # Before
   for instance in instances:
       tags = client.describe_tags(Resources=[instance["InstanceId"]])

   # After
   all_tags = client.describe_tags(Resources=[i["InstanceId"] for i in instances])
   ```

2. **병렬 처리 적용** (예상 개선: 80% 시간 단축)
   ```python
   result = parallel_collect(ctx, _collect_and_analyze, max_workers=20)
   ```

### 예상 개선 효과
- API 호출: 1000회 → 10회 (99% 감소)
- 실행 시간: 60초 → 6초 (90% 단축)
- 메모리: 변화 없음
```

## 참조

- `core/parallel/__init__.py` - 병렬 처리 모듈
- `core/parallel/rate_limiter.py` - Rate limiter
- `.claude/skills/parallel-execution-patterns.md` - 병렬 처리 가이드
