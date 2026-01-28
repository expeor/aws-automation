# /make-test - 플러그인 테스트 스캐폴딩

플러그인 모듈에 대한 테스트 파일을 자동 생성합니다.

## 사용법

```
/make-test <service>/<module>
```

예시:
```
/make-test efs/unused
/make-test ec2/security
/make-test vpc/sg_audit
```

---

## MCP 도구 활용

테스트 작성 시 다음 MCP 도구를 활용합니다.

### context7
pytest, moto 문서 참조:
```
mcp__context7__resolve("pytest")
mcp__context7__get_library_docs("pytest", "fixtures")
mcp__context7__get_library_docs("moto", "mock_aws decorator")
```

### aws-documentation
AWS API 응답 구조 확인:
```
mcp__aws-documentation__search("EC2 describe_instances response")
mcp__aws-documentation__get_documentation("ec2", "describe-instances")
```

| 테스트 영역 | MCP 도구 |
|------------|----------|
| pytest 패턴 | context7 |
| moto 모킹 | context7 |
| AWS 응답 구조 | aws-documentation |

---

## 테스트 전략

### 테스트 피라미드

```
        /\
       /  \     E2E (run 함수 통합)
      /────\
     /      \   Integration (collect + analyze)
    /────────\
   /          \ Unit (개별 함수)
  /────────────\
```

### 커버리지 목표

| 함수 유형 | 필수 테스트 | 권장 테스트 |
|----------|------------|------------|
| `collect_*` | 정상, 빈 결과, AccessDenied | Throttling, Timeout |
| `analyze_*` | 정상, 빈 입력 | 엣지 케이스 |
| `run` | 정상, 결과 없음 | 부분 실패 |

---

## 실행 순서

### 1. 대상 모듈 확인

사용자 입력 `$ARGUMENTS`에서 서비스와 모듈명 추출:
- 형식: `{service}/{module}` (예: `efs/unused`)
- 대상 파일: `plugins/{service}/{module}.py`

파일이 존재하지 않으면 오류 메시지 출력 후 종료.

### 2. 모듈 분석

대상 플러그인 파일에서 다음 정보 추출:
- **run() 함수**: 존재 여부 확인 (필수)
- **collect_* 함수**: 수집 함수 목록
- **analyze_* 함수**: 분석 함수 목록
- **dataclass**: 데이터 클래스 목록
- **AWS 서비스**: `get_client(session, "서비스명")` 패턴에서 추출
- **사용 모듈**: import 문 분석

### 3. 테스트 파일 생성

생성 경로: `tests/plugins/{service}/test_{module}.py`

#### 템플릿 구조

```python
"""
tests/plugins/{service}/test_{module}.py - {도구명} 테스트
"""
import pytest
from unittest.mock import MagicMock, patch

# moto 사용 가능 여부 확인
try:
    import moto
    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False


class TestCollect{Resource}:
    """collect_{resources}() 함수 테스트"""

    def test_collect_normal(self, mock_context, mock_boto3_session):
        """정상 수집 케이스"""
        # Arrange
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.return_value = {{
            # 샘플 응답 구조
        }}

        # Act
        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # Assert
        assert isinstance(result, list)

    def test_collect_empty(self, mock_context, mock_boto3_session):
        """빈 결과 케이스"""
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.return_value = {{}}

        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        assert result == []

    def test_collect_access_denied(self, mock_context, mock_boto3_session):
        """권한 없음 에러 케이스"""
        from botocore.exceptions import ClientError
        from plugins.{service}.{module} import collect_{resource}

        mock_client = MagicMock()
        mock_boto3_session.client.return_value = mock_client
        mock_client.{api_method}.side_effect = ClientError(
            {{"Error": {{"Code": "AccessDenied", "Message": "Access Denied"}}}},
            "{api_method}"
        )

        result = collect_{resource}(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        assert result == []


class TestAnalyze{Resource}:
    """analyze_{resources}() 함수 테스트"""

    def test_analyze_normal(self):
        """정상 분석 케이스"""
        from plugins.{service}.{module} import analyze_{resource}

        # Arrange
        test_data = [
            # 테스트 데이터
        ]

        # Act
        result = analyze_{resource}(
            test_data,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # Assert
        assert result is not None

    def test_analyze_empty_input(self):
        """빈 입력 케이스"""
        from plugins.{service}.{module} import analyze_{resource}

        result = analyze_{resource}(
            [],
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2"
        )

        # 빈 결과 또는 기본값 반환 확인
        assert result is not None


class TestRun:
    """run() 통합 테스트"""

    @patch("plugins.{service}.{module}.parallel_collect")
    @patch("plugins.{service}.{module}.generate_reports")
    def test_run_success(self, mock_reports, mock_parallel, mock_context):
        """정상 실행"""
        from plugins.{service}.{module} import run

        # Arrange
        mock_result = MagicMock()
        mock_result.get_data.return_value = [MagicMock()]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result
        mock_reports.return_value = {
            "excel": "/tmp/test_report.xlsx",
            "html": "/tmp/test_report.html",
        }

        # Act
        run(mock_context)

        # Assert
        mock_parallel.assert_called_once()
        mock_reports.assert_called_once()

    @patch("plugins.{service}.{module}.parallel_collect")
    def test_run_no_results(self, mock_parallel, mock_context):
        """결과 없음"""
        from plugins.{service}.{module} import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = []
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # Should complete without error
        run(mock_context)

    @patch("plugins.{service}.{module}.parallel_collect")
    def test_run_with_errors(self, mock_parallel, mock_context):
        """부분 실패"""
        from plugins.{service}.{module} import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [MagicMock()]
        mock_result.error_count = 2
        mock_parallel.return_value = mock_result

        # Should complete even with some errors
        run(mock_context)


# =============================================================================
# moto 기반 통합 테스트 (선택적)
# =============================================================================

@pytest.mark.skipif(not HAS_MOTO, reason="moto not installed")
class TestWithMoto:
    """moto를 사용한 AWS 모킹 테스트"""

    def test_collect_with_moto(self, moto_{aws_service}):
        """실제 AWS API 모킹 테스트"""
        # moto로 실제 리소스 생성 후 테스트
        pass
```

### 4. fixture 확인

테스트에서 사용하는 fixture 확인 (`tests/conftest.py`):
- `mock_context`: ExecutionContext 모킹
- `mock_provider`: Provider 모킹
- `mock_boto3_session`: boto3.Session 모킹
- `mock_ec2_client`: EC2 클라이언트 모킹
- `moto_ec2`: moto 기반 EC2 모킹
- `moto_s3`: moto 기반 S3 모킹
- `moto_iam`: moto 기반 IAM 모킹

필요한 fixture가 conftest.py에 없으면 추가 안내.

### 5. 디렉토리 생성

`tests/plugins/{service}/` 디렉토리가 없으면 생성.
`__init__.py` 파일이 없으면 빈 파일 생성.

### 6. 파일 작성 및 검증

생성된 테스트 파일이 문법적으로 올바른지 확인:
```bash
python -m py_compile tests/plugins/{service}/test_{module}.py
```

## 출력 예시

```
/make-test efs/unused 실행 중...

[분석] plugins/efs/unused.py
  - run() 함수: 있음
  - collect 함수: collect_efs_filesystems
  - analyze 함수: analyze_filesystems
  - AWS 서비스: efs, cloudwatch
  - 데이터클래스: EFSInfo, EFSFinding, EFSAnalysisResult

[생성] tests/plugins/efs/test_unused.py
  - TestCollectEfsFilesystems (3개 테스트)
  - TestAnalyzeFilesystems (2개 테스트)
  - TestRun (3개 테스트)
  - TestWithMoto (1개 테스트)

[검증] 문법 검사 통과

완료! 생성된 테스트 파일:
  tests/plugins/efs/test_unused.py

실행 방법:
  pytest tests/plugins/efs/test_unused.py -v
```

---

## 테스트 데이터 팩토리

테스트 데이터 생성을 위한 팩토리 패턴을 활용합니다.

### 리소스 팩토리 패턴

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import random
import string


@dataclass
class EC2InstanceFactory:
    """EC2 인스턴스 테스트 데이터 팩토리"""

    instance_id: str = ""
    instance_type: str = "t3.micro"
    state: str = "running"
    launch_time: datetime = field(default_factory=datetime.now)
    tags: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.instance_id:
            self.instance_id = f"i-{''.join(random.choices(string.hexdigits.lower(), k=17))}"

    def build(self) -> dict:
        """boto3 응답 형식으로 반환"""
        return {
            "InstanceId": self.instance_id,
            "InstanceType": self.instance_type,
            "State": {"Name": self.state},
            "LaunchTime": self.launch_time,
            "Tags": self.tags,
        }

    def with_name(self, name: str) -> "EC2InstanceFactory":
        self.tags.append({"Key": "Name", "Value": name})
        return self

    def stopped(self) -> "EC2InstanceFactory":
        self.state = "stopped"
        return self

    def running(self) -> "EC2InstanceFactory":
        self.state = "running"
        return self


@dataclass
class EBSVolumeFactory:
    """EBS 볼륨 테스트 데이터 팩토리"""

    volume_id: str = ""
    size: int = 100
    state: str = "available"
    attachments: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.volume_id:
            self.volume_id = f"vol-{''.join(random.choices(string.hexdigits.lower(), k=17))}"

    def build(self) -> dict:
        return {
            "VolumeId": self.volume_id,
            "Size": self.size,
            "State": self.state,
            "Attachments": self.attachments,
        }

    def attached_to(self, instance_id: str) -> "EBSVolumeFactory":
        self.state = "in-use"
        self.attachments = [{"InstanceId": instance_id, "State": "attached"}]
        return self

    def unattached(self) -> "EBSVolumeFactory":
        self.state = "available"
        self.attachments = []
        return self


# 사용 예시
def test_with_factory():
    instance = EC2InstanceFactory().with_name("web-server").running().build()
    volume = EBSVolumeFactory().unattached().build()
    attached_vol = EBSVolumeFactory().attached_to(instance["InstanceId"]).build()

    assert instance["State"]["Name"] == "running"
    assert volume["State"] == "available"
    assert attached_vol["State"] == "in-use"
```

### Fixture 기반 팩토리

```python
@pytest.fixture
def ec2_instance_factory():
    """EC2 인스턴스 팩토리 fixture"""
    return EC2InstanceFactory


@pytest.fixture
def sample_instances(ec2_instance_factory):
    """샘플 인스턴스 세트"""
    return [
        ec2_instance_factory().with_name("web-1").running().build(),
        ec2_instance_factory().with_name("web-2").running().build(),
        ec2_instance_factory().with_name("batch").stopped().build(),
    ]
```

---

## 성능 벤치마크 테스트

pytest-benchmark를 사용한 성능 측정:

```python
import pytest


class TestPerformanceBenchmarks:
    """성능 벤치마크 테스트"""

    @pytest.mark.benchmark(group="parallel")
    def test_parallel_collect_performance(self, benchmark, mock_ctx):
        """병렬 수집 성능 벤치마크"""
        from core.parallel import parallel_collect

        def _collect(session, account_id, account_name, region):
            return [{"id": f"res-{i}"} for i in range(100)]

        result = benchmark(
            parallel_collect,
            mock_ctx,
            _collect,
            service="ec2"
        )

        assert result.get_flat_data() is not None

    @pytest.mark.benchmark(group="metrics")
    def test_batch_metrics_performance(self, benchmark):
        """배치 메트릭 조회 성능 벤치마크"""
        from shared.aws.metrics import (
            build_lambda_metric_queries,
        )

        function_names = [f"func-{i}" for i in range(100)]

        queries = benchmark(
            build_lambda_metric_queries,
            function_names,
            ["Invocations", "Errors"]
        )

        assert len(queries) == 200  # 100 함수 × 2 메트릭
```

### pytest.ini 벤치마크 설정

```ini
[tool.pytest.ini_options]
markers = [
    "benchmark: 성능 벤치마크 테스트",
    "memory: 메모리 프로파일링 테스트",
    "e2e: End-to-End 테스트",
    "integration: 통합 테스트",
]
```

벤치마크 실행:
```bash
pytest tests/ -m benchmark --benchmark-only
```

---

## 메모리 프로파일링

tracemalloc을 사용한 메모리 사용량 테스트:

```python
import pytest
import tracemalloc


class TestMemoryUsage:
    """메모리 사용량 테스트"""

    @pytest.mark.memory
    def test_large_dataset_memory(self):
        """대용량 데이터 메모리 사용량 테스트"""
        tracemalloc.start()

        # 대용량 데이터 생성
        data = [
            {"id": f"res-{i}", "name": f"resource-{i}", "size": i * 100}
            for i in range(10000)
        ]

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 피크 메모리 200MB 미만
        assert peak < 200 * 1024 * 1024, f"Peak memory: {peak / 1024 / 1024:.1f}MB"

    @pytest.mark.memory
    def test_streaming_vs_batch_memory(self):
        """스트리밍 vs 배치 메모리 비교"""
        tracemalloc.start()

        # 스트리밍 처리
        def stream_process():
            for i in range(10000):
                yield {"id": i}

        list(stream_process())

        stream_current, stream_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        tracemalloc.start()

        # 배치 처리
        batch_data = [{"id": i} for i in range(10000)]

        batch_current, batch_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 스트리밍이 더 효율적
        assert stream_peak <= batch_peak
```

메모리 테스트 실행:
```bash
pytest tests/ -m memory
```

---

## 검증 체크리스트

### 생성 전 확인
- [ ] 대상 플러그인 파일 존재: `plugins/{service}/{module}.py`
- [ ] `run(ctx)` 함수 존재 확인
- [ ] 테스트 디렉토리 확인: `tests/plugins/{service}/`

### 생성 후 확인
- [ ] 문법 검사: `python -m py_compile tests/plugins/{service}/test_{module}.py`
- [ ] 테스트 실행: `pytest tests/plugins/{service}/test_{module}.py -v`
- [ ] 커버리지 확인: `pytest --cov=plugins/{service}/{module}`

### 품질 기준
- [ ] 최소 3개 테스트 케이스 (정상, 빈 결과, 에러)
- [ ] moto 또는 MagicMock 사용
- [ ] AAA 패턴 준수 (Arrange-Act-Assert)

---

## 참조 파일

### 코드 참조
- `tests/conftest.py` - 공통 fixture 정의
- `tests/plugins/` - 기존 테스트 예시

### Skills 참조
- `.claude/skills/tdd-workflow/SKILL.md` - TDD 가이드
- `.claude/skills/python-best-practices/SKILL.md` - 코딩 스타일

## 주의사항

1. **기존 파일 덮어쓰기 금지**: 테스트 파일이 이미 존재하면 확인 요청
2. **import 경로 확인**: 프로젝트 루트 기준 import 사용
3. **moto 호환성**: moto가 지원하지 않는 서비스는 MagicMock 사용
4. **fixture 활용**: conftest.py의 fixture 최대한 활용
5. **팩토리 패턴**: 반복되는 테스트 데이터는 팩토리로 추출
6. **벤치마크**: 성능 중요 함수는 @pytest.mark.benchmark 추가
