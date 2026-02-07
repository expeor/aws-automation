# 디버깅 & 트러블슈팅 가이드

분석기 실패 및 테스트 문제 진단 가이드입니다.

## 테스트 환경

### moto로 AWS 모킹

```python
import pytest
from moto import mock_aws

@mock_aws
def test_collect_instances():
    """moto로 AWS 환경 모킹"""
    import boto3
    ec2 = boto3.client("ec2", region_name="ap-northeast-2")
    ec2.run_instances(ImageId="ami-test", MinCount=1, MaxCount=1)

    # 테스트 대상 호출
    result = collect_instances(session, "123456789012", "test", "ap-northeast-2")
    assert len(result) == 1
```

### conftest.py 픽스처

`tests/conftest.py`에서 제공하는 공통 픽스처:

```python
# mock_context: 테스트용 ExecutionContext
def test_run(mock_context):
    mock_context.category = "ec2"
    mock_context.tool = ToolInfo(name="unused", module="unused")
    run(mock_context)

# mock_provider: 테스트용 Provider (MockProvider)
def test_auth(mock_provider):
    assert mock_provider._authenticated is True

# mock_account_info: 테스트용 계정 정보
def test_account(mock_account_info):
    assert mock_account_info.account_id == "123456789012"

# create_mock_client_error: ClientError 생성 헬퍼
def test_error_handling():
    from tests.conftest import create_mock_client_error
    error = create_mock_client_error("AccessDeniedException", "Not authorized")
    # error를 사용하여 에러 처리 테스트
```

### 테스트에서 모듈 mock하기

```python
from unittest.mock import MagicMock, patch

class TestRun:
    @patch("analyzers.ec2.unused.parallel_collect")
    @patch("analyzers.ec2.unused.console")
    def test_no_results(self, mock_console, mock_parallel):
        mock_result = MagicMock()
        mock_result.get_data.return_value = []
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        run(MagicMock())
        # 결과 없음 메시지 확인
```

## 일반적인 실패 패턴

### 1. Throttling 에러

```python
from core.parallel.types import ErrorCategory

# 진단: result에서 에러 확인
result = parallel_collect(ctx, callback, service="ec2")
for error in result.errors:
    if error.category == ErrorCategory.THROTTLING:
        print(f"Throttled: {error.operation} in {error.region}")

# 해결: max_workers 줄이기
result = parallel_collect(ctx, callback, service="ec2", max_workers=5)
```

### 2. 부분 실패 (일부 리전/계정만 실패)

```python
result = parallel_collect(ctx, callback, service="ec2")

# 데이터와 에러 모두 있는 경우
if result.error_count > 0 and result.get_data():
    console.print(f"[yellow]일부 오류: {result.error_count}건[/yellow]")
    console.print(result.get_error_summary())

    # 성공한 데이터만 처리 (None 필터링)
    valid_data = [d for d in result.get_data() if d is not None]
```

### 3. AccessDenied

```python
# ErrorCollector에서 자동으로 WARNING → INFO 다운그레이드
errors = ErrorCollector(service="ec2")
try:
    client.describe_instances()
except ClientError as e:
    errors.collect(e, account_id, account_name, region,
                   operation="describe_instances",
                   severity=ErrorSeverity.WARNING)
    # AccessDenied면 자동으로 INFO로 변환됨

# 진단: 어떤 계정/리전에서 발생했는지 확인
by_account = errors.get_by_account()
```

### 4. quiet_mode 관련 문제

`quiet_mode`는 컨텍스트 매니저로 스레드-로컬 상태를 관리:

```python
from core.parallel import quiet_mode

# 올바른 사용
with quiet_mode():
    result = parallel_collect(ctx, callback)

# 주의: quiet_mode는 현재 스레드에만 영향
# 워커 스레드에서는 별도로 관리됨
```

### 5. 테스트에서 import 실패

```python
# 문제: shared.io.output (deprecated) 사용
from shared.io.output import OutputPath  # DeprecationWarning

# 해결: shared.io.output 사용
from shared.io.output import OutputPath
from shared.io.output.helpers import create_output_path
```

## 디버깅 기법

### 에러 요약 확인

```python
# parallel_collect 결과의 에러 요약
result = parallel_collect(ctx, callback, service="ec2")
if result.error_count > 0:
    print(result.get_error_summary())
    # 출력: "ap-northeast-2: AccessDenied (2건), us-east-1: Throttling (1건)"
```

### ErrorCollector 상세 분석

```python
errors = ErrorCollector(service="ec2")

# 전체 에러 목록
for err in errors.all_errors:
    print(f"{err.account_id}/{err.region}: {err.category.name} - {err.message}")

# 심각도별 필터링
critical = errors.critical_errors  # 즉시 조치 필요
warnings = errors.warning_errors   # 검토 필요
info = errors.info_errors          # 정보성

# 카테고리별 카운트
print(f"Access Denied: {sum(1 for e in errors.all_errors if e.category == ErrorCategory.ACCESS_DENIED)}")
print(f"Throttling: {sum(1 for e in errors.all_errors if e.category == ErrorCategory.THROTTLING)}")
```

### 테스트 실행

```bash
# 특정 모듈 테스트
pytest tests/analyzers/rds/ -v

# 특정 클래스
pytest tests/analyzers/rds/test_plugins_rds.py::TestAnalyzeInstances -v

# 특정 테스트
pytest tests/analyzers/rds/test_plugins_rds.py::TestAnalyzeInstances::test_unused_instance -v

# 실패 시 디버깅
pytest tests/ -v --tb=long  # 상세 트레이스백
pytest tests/ -v -s         # print 출력 표시
```

## 참조

- `tests/conftest.py` - 공통 픽스처 (mock_context, MockProvider, create_mock_client_error)
- `core/parallel/errors.py` - ErrorCollector
- `core/parallel/types.py` - ErrorCategory, TaskError
- `core/parallel/decorators.py` - categorize_error
