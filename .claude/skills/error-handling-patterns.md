# 에러 핸들링 패턴

프로젝트의 표준 에러 처리 패턴입니다.

## 권장 패턴: core/parallel/errors

```python
from core.parallel.errors import ErrorCollector, ErrorSeverity, try_or_default
```

## ErrorCollector 사용

### 기본 사용법

```python
from botocore.exceptions import ClientError
from core.parallel.errors import ErrorCollector, ErrorSeverity

def collect_resources(session, account_id: str, account_name: str, region: str):
    errors = ErrorCollector(service="ec2")
    client = get_client(session, "ec2", region_name=region)
    results = []

    try:
        response = client.describe_instances()
        results = response.get("Reservations", [])
    except ClientError as e:
        errors.collect(
            e,
            account_id=account_id,
            account_name=account_name,
            region=region,
            operation="describe_instances",
            severity=ErrorSeverity.WARNING,
        )

    return results, errors
```

### ErrorSeverity 레벨

| 레벨 | 용도 | 자동 다운그레이드 |
|------|------|------------------|
| `CRITICAL` | 핵심 기능 실패 | - |
| `WARNING` | 부분 실패, 계속 진행 | AccessDenied → INFO |
| `INFO` | 정보성 (권한 없음 등) | - |
| `DEBUG` | 개발/디버깅용 | - |

### 에러 조회

```python
# 에러 존재 여부
if errors.has_errors:
    print(errors.get_summary())  # "에러 3건 (warning: 2건, info: 1건)"

# 심각도별 조회
critical = errors.critical_errors
warnings = errors.warning_errors

# 계정별 그룹핑
by_account = errors.get_by_account()
for account, account_errors in by_account.items():
    print(f"{account}: {len(account_errors)}건")
```

## try_or_default 함수

단일 API 호출에 간편하게 사용:

```python
from core.parallel.errors import try_or_default, ErrorSeverity

def get_instance_tags(client, instance_id: str, errors: ErrorCollector) -> dict:
    """태그 조회 - 실패해도 기본값 반환"""
    return try_or_default(
        lambda: client.describe_tags(
            Filters=[{"Name": "resource-id", "Values": [instance_id]}]
        ).get("Tags", []),
        default={},
        collector=errors,
        account_id=account_id,
        account_name=account_name,
        region=region,
        operation="describe_tags",
        severity=ErrorSeverity.DEBUG,  # 태그는 옵션이라 DEBUG
    )
```

### 옵션 데이터 조회 패턴

```python
def collect_volume_info(client, volume_id: str, errors: ErrorCollector):
    # 필수 데이터
    volume = client.describe_volumes(VolumeIds=[volume_id])["Volumes"][0]

    # 옵션 데이터 (실패해도 계속)
    tags = try_or_default(
        lambda: client.describe_tags(...)["Tags"],
        default=[],
        collector=errors,
        operation="describe_tags",
        severity=ErrorSeverity.DEBUG,
    )

    snapshots = try_or_default(
        lambda: client.describe_snapshots(...)["Snapshots"],
        default=[],
        collector=errors,
        operation="describe_snapshots",
        severity=ErrorSeverity.DEBUG,
    )

    return VolumeInfo(volume=volume, tags=tags, snapshots=snapshots)
```

## 에러 카테고리 자동 분류

`ErrorCollector`는 에러 코드를 자동 분류:

| 카테고리 | 에러 코드 예시 |
|----------|---------------|
| `ACCESS_DENIED` | AccessDenied, Unauthorized, Forbidden |
| `NOT_FOUND` | NotFound, NoSuch, DoesNotExist |
| `THROTTLING` | Throttling, RateLimit, TooManyRequests |
| `TIMEOUT` | Timeout, TimedOut |
| `INVALID_REQUEST` | Invalid, Validation, Malformed |
| `SERVICE_ERROR` | Internal, ServiceUnavailable |
| `UNKNOWN` | 기타 |

## 병렬 처리와 에러 핸들링

```python
from core.parallel import parallel_collect
from core.parallel.errors import ErrorCollector

def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """병렬 콜백 - 에러는 내부에서 처리"""
    errors = ErrorCollector(service="ec2")
    client = get_client(session, "ec2", region_name=region)

    try:
        # 수집
        volumes = client.describe_volumes()["Volumes"]
    except ClientError as e:
        errors.collect(e, account_id, account_name, region, "describe_volumes")
        return None  # 또는 빈 결과 반환

    # 분석 및 반환
    return AnalysisResult(data=volumes, errors=errors)

def run(ctx):
    result = parallel_collect(ctx, _collect_and_analyze, service="ec2")

    # parallel_collect의 에러 카운트
    if result.error_count > 0:
        console.print(f"[yellow]오류 {result.error_count}건[/yellow]")
        console.print(result.get_error_summary())
```

## 레거시 패턴 (사용 지양)

```python
# ❌ 단순 try-except
try:
    result = client.describe_instances()
except Exception as e:
    print(f"Error: {e}")
    return []

# ❌ 빈 except
except:
    pass

# ❌ print로 에러 출력
except ClientError as e:
    print(f"Error in {region}: {e}")
```

## 권장 패턴

```python
# ✅ ErrorCollector 사용
from core.parallel.errors import ErrorCollector, ErrorSeverity

errors = ErrorCollector(service="ec2")

try:
    result = client.describe_instances()
except ClientError as e:
    errors.collect(
        e,
        account_id=account_id,
        account_name=account_name,
        region=region,
        operation="describe_instances",
        severity=ErrorSeverity.WARNING,
    )
    return []

# ✅ try_or_default로 간소화
tags = try_or_default(
    lambda: client.describe_tags(...)["Tags"],
    default=[],
    collector=errors,
    operation="describe_tags",
)
```

## 전체 예시

```python
from botocore.exceptions import ClientError
from core.parallel import get_client, parallel_collect
from core.parallel.errors import ErrorCollector, ErrorSeverity, try_or_default

def _collect_volumes(session, account_id: str, account_name: str, region: str):
    """볼륨 수집 (병렬 콜백)"""
    errors = ErrorCollector(service="ec2")
    client = get_client(session, "ec2", region_name=region)

    volumes = []
    try:
        paginator = client.get_paginator("describe_volumes")
        for page in paginator.paginate():
            for vol in page.get("Volumes", []):
                # 옵션 데이터: 스냅샷 개수
                snapshot_count = try_or_default(
                    lambda vid=vol["VolumeId"]: len(
                        client.describe_snapshots(
                            Filters=[{"Name": "volume-id", "Values": [vid]}]
                        ).get("Snapshots", [])
                    ),
                    default=0,
                    collector=errors,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    operation="describe_snapshots",
                    severity=ErrorSeverity.DEBUG,
                )
                volumes.append({**vol, "SnapshotCount": snapshot_count})

    except ClientError as e:
        errors.collect(
            e, account_id, account_name, region,
            operation="describe_volumes",
            severity=ErrorSeverity.WARNING,
        )

    return {"volumes": volumes, "errors": errors}

def run(ctx):
    result = parallel_collect(ctx, _collect_volumes, service="ec2")

    # 결과 집계
    all_volumes = []
    for r in result.get_data():
        if r:
            all_volumes.extend(r["volumes"])

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류: {result.error_count}건[/yellow]")
```

## 참조

- `core/parallel/errors.py` - ErrorCollector, try_or_default
- `core/parallel/types.py` - ErrorCategory, TaskError
