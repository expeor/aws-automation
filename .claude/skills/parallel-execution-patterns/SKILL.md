---
name: parallel-execution-patterns
description: 병렬 실행 패턴. parallel_collect, Rate Limiter, Service Quotas 확인.
---

# 병렬 실행 패턴

멀티 계정/리전 병렬 처리 패턴입니다.

## 권장 패턴: parallel_collect

```python
from core.parallel import parallel_collect, get_client
```

## 기본 사용법

### 1. 콜백 함수 정의

```python
def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """병렬 실행 콜백 (단일 계정/리전)

    Args:
        session: boto3 Session (자동 제공)
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 리전 코드

    Returns:
        분석 결과 또는 None (결과 없음)
    """
    client = get_client(session, "ec2", region_name=region)

    # 수집
    volumes = client.describe_volumes()["Volumes"]
    if not volumes:
        return None

    # 분석
    return analyze_volumes(volumes, account_id, account_name, region)
```

### 2. parallel_collect 호출

```python
def run(ctx) -> None:
    result = parallel_collect(
        ctx,
        _collect_and_analyze,
        max_workers=20,      # 동시 실행 수 (기본: 20)
        service="ec2",       # 서비스명 (Rate limiter용)
    )

    # 결과 처리
    data = result.get_data()           # list[T | None]
    flat_data = result.get_flat_data()  # 평탄화 (결과가 list일 때)

    # 에러 처리
    if result.error_count > 0:
        console.print(f"[yellow]오류: {result.error_count}건[/yellow]")
        console.print(result.get_error_summary())
```

## ParallelExecutionResult

`parallel_collect` 반환값:

| 속성/메서드 | 설명 |
|------------|------|
| `get_data()` | 모든 결과 리스트 (None 포함) |
| `get_flat_data()` | 평탄화된 결과 (결과가 list일 때) |
| `success_count` | 성공 개수 |
| `error_count` | 에러 개수 |
| `total_count` | 전체 작업 개수 |
| `get_error_summary()` | 에러 요약 문자열 |
| `errors` | 에러 목록 |

```python
result = parallel_collect(ctx, callback, service="ec2")

# None 제외
results = [r for r in result.get_data() if r is not None]

# 통계
print(f"성공: {result.success_count}, 실패: {result.error_count}")
```

## get_client 사용

세션에서 클라이언트 생성 (재시도 로직 포함):

```python
from core.parallel import get_client

def _collect(session, account_id: str, account_name: str, region: str):
    # 권장: get_client 사용
    ec2 = get_client(session, "ec2", region_name=region)
    s3 = get_client(session, "s3", region_name=region)

    # 직접 client 생성 (재시도 없음) - 사용 지양
    # ec2 = session.client("ec2", region_name=region)
```

## Progress Tracking

진행 상황 표시:

```python
from core.parallel import parallel_collect, quiet_mode
from cli.ui import parallel_progress

def run(ctx):
    with parallel_progress("리소스 수집") as tracker:
        with quiet_mode():  # 진행 바 표시 중 로그 억제
            result = parallel_collect(
                ctx,
                _collect_and_analyze,
                progress_tracker=tracker,
                service="ec2",
            )

    success, failed, total = tracker.stats
    console.print(f"완료: {success}개 성공, {failed}개 실패 (총 {total}개)")
```

### progress_tracker 상세 사용

```python
from cli.ui import parallel_progress, console

def run(ctx):
    # 진행 바 컨텍스트 매니저
    with parallel_progress("VPC 분석") as tracker:
        # tracker.update(current, total) - 수동 업데이트
        # tracker.increment() - 1 증가
        # tracker.set_description("새 설명") - 설명 변경

        with quiet_mode():
            result = parallel_collect(
                ctx,
                _collect_vpcs,
                progress_tracker=tracker,  # 자동 업데이트
                service="ec2",
            )

    # tracker.stats: (success, failed, total) 튜플
    success, failed, total = tracker.stats

    if failed > 0:
        console.print(f"[yellow]! 일부 실패: {failed}/{total}[/yellow]")
    else:
        console.print(f"[green]✓ 전체 성공: {success}/{total}[/green]")
```

### quiet_mode() 컨텍스트 매니저

```python
from core.parallel import quiet_mode, is_quiet, set_quiet

# 컨텍스트 매니저 (권장)
with quiet_mode():
    # 이 블록 내에서 로그 출력 억제
    result = parallel_collect(ctx, callback, service="ec2")

# 수동 제어
set_quiet(True)   # 조용한 모드 활성화
set_quiet(False)  # 조용한 모드 비활성화

# 현재 상태 확인
if is_quiet():
    # 로그 출력 안함
    pass
else:
    console.print("상세 로그...")
```

### 다단계 진행 표시

```python
def run(ctx):
    console.print("[bold]Step 1: 리소스 수집[/bold]")

    with parallel_progress("VPC 수집") as tracker1:
        with quiet_mode():
            vpcs_result = parallel_collect(ctx, _collect_vpcs, progress_tracker=tracker1, service="ec2")

    s1, f1, t1 = tracker1.stats
    console.print(f"  VPCs: {s1} 성공, {f1} 실패")

    console.print("[bold]Step 2: 보안 그룹 수집[/bold]")

    with parallel_progress("SG 수집") as tracker2:
        with quiet_mode():
            sgs_result = parallel_collect(ctx, _collect_sgs, progress_tracker=tracker2, service="ec2")

    s2, f2, t2 = tracker2.stats
    console.print(f"  SGs: {s2} 성공, {f2} 실패")

    # 전체 요약
    total_success = s1 + s2
    total_failed = f1 + f2
    console.print(f"\n[bold]전체: {total_success} 성공, {total_failed} 실패[/bold]")
```

## 상세 제어: ParallelSessionExecutor

더 세밀한 제어가 필요할 때:

```python
from core.parallel import ParallelSessionExecutor, ParallelConfig

config = ParallelConfig(
    max_workers=30,          # 동시 실행 수
    timeout=300,             # 작업당 타임아웃 (초)
    retry_count=3,           # 재시도 횟수
    retry_delay=1.0,         # 재시도 간격 (초)
)

executor = ParallelSessionExecutor(ctx, config)
result = executor.execute(_collect_func, service="ec2")
```

## Rate Limiter

API 쓰로틀링 방지:

```python
from core.parallel import get_rate_limiter, create_rate_limiter, RateLimiterConfig

# 기본 Rate limiter 사용 (service 파라미터로 자동 적용)
result = parallel_collect(ctx, callback, service="ec2")

# 커스텀 Rate limiter
config = RateLimiterConfig(
    tokens_per_second=10,
    max_tokens=100,
)
limiter = create_rate_limiter("custom", config)
```

## 콜백 함수 패턴

### 결과 반환 패턴

```python
# 단일 객체 반환
def _collect(session, account_id, account_name, region) -> AnalysisResult | None:
    data = collect_data(...)
    if not data:
        return None
    return AnalysisResult(data=data)

# 리스트 반환 (get_flat_data로 평탄화)
def _collect(session, account_id, account_name, region) -> list[Volume]:
    volumes = client.describe_volumes()["Volumes"]
    return [Volume.from_aws(v) for v in volumes]
```

### 에러 처리 패턴

```python
from botocore.exceptions import ClientError

def _collect(session, account_id, account_name, region):
    client = get_client(session, "ec2", region_name=region)

    try:
        volumes = client.describe_volumes()["Volumes"]
    except ClientError as e:
        # 권한 없음: None 반환 (정상적인 상황)
        if e.response["Error"]["Code"] == "AccessDenied":
            return None
        # 그 외: 예외 발생 (error_count에 집계)
        raise

    return volumes
```

## Service Quotas 확인

운영 전 서비스 한도 확인:

```python
from core.parallel import get_quota_checker, QuotaStatus

def run(ctx):
    session = ctx.provider.get_session()
    checker = get_quota_checker(session, "ap-northeast-2")

    # 특정 쿼터 확인
    quota = checker.get_quota("ec2", "Running On-Demand")
    if quota and quota.usage_percent > 80:
        console.print(f"[yellow]경고: {quota.quota_name} 사용률 {quota.usage_percent:.1f}%[/yellow]")

    # 서비스 모든 쿼터 확인
    quotas = checker.get_service_quotas("ec2")
    high_usage = [q for q in quotas if q.status in (QuotaStatus.WARNING, QuotaStatus.CRITICAL)]
```

주요 쿼터:

| 서비스 | 쿼터 코드 | 설명 |
|--------|----------|------|
| EC2 | L-1216C47A | Running On-Demand Standard instances |
| EC2 | L-34B43A08 | All Standard Spot Instance Requests |
| Lambda | L-B99A9384 | Concurrent executions |
| IAM | L-F4A5425F | Roles |

## 전체 예시

```python
from core.parallel import parallel_collect, get_client
from core.tools.output import OutputPath, open_in_explorer
from rich.console import Console

console = Console()

def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """EBS 볼륨 수집 및 분석"""
    client = get_client(session, "ec2", region_name=region)

    # 수집
    volumes = []
    paginator = client.get_paginator("describe_volumes")
    for page in paginator.paginate():
        volumes.extend(page.get("Volumes", []))

    if not volumes:
        return None

    # 분석
    unused = [v for v in volumes if v["State"] == "available"]

    return {
        "account_id": account_id,
        "account_name": account_name,
        "region": region,
        "total": len(volumes),
        "unused": len(unused),
        "volumes": unused,
    }

def run(ctx) -> None:
    console.print("[bold]EBS 분석 시작...[/bold]")

    result = parallel_collect(ctx, _collect_and_analyze, service="ec2")

    # 결과 집계
    results = [r for r in result.get_data() if r is not None]

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류: {result.error_count}건[/yellow]")

    if not results:
        console.print("[yellow]분석 결과 없음[/yellow]")
        return

    total_unused = sum(r["unused"] for r in results)
    console.print(f"미사용 볼륨: [red]{total_unused}개[/red]")

    # 보고서 생성
    output_path = OutputPath(ctx.identifier).sub("ec2", "ebs").with_date().build()
    filepath = generate_report(results, output_path)

    console.print(f"[green]완료![/green] {filepath}")
    open_in_explorer(output_path)
```

## 레거시 패턴 (사용 지양)

```python
# 순차 루프
for account in accounts:
    for region in regions:
        session = ctx.provider.get_session(account.id, region=region)
        result = analyze(session, account, region)

# 직접 ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(func, args) for args in items]
```

## 참조

- `core/parallel/__init__.py` - parallel_collect, get_client
- `core/parallel/executor.py` - ParallelSessionExecutor, ParallelConfig
- `core/parallel/rate_limiter.py` - Rate limiter
- `core/parallel/quotas.py` - ServiceQuotaChecker, QuotaStatus
- `core/parallel/types.py` - ParallelExecutionResult
