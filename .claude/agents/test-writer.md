# Test Writer Agent

pytest 테스트 코드를 작성하는 에이전트입니다.

## MCP 도구 활용

### context7
pytest/moto 라이브러리 문서 조회:
```
mcp__context7__resolve("pytest")
mcp__context7__get_library_docs("moto", "mock_aws decorator")
mcp__context7__get_library_docs("pytest", "fixtures")
```

| 용도 | MCP 도구 |
|------|----------|
| pytest fixture 문법 | context7 |
| moto 모킹 패턴 | context7 |

## 테스트 구조

```
tests/
├── conftest.py           # 공통 fixtures
├── cli/                  # CLI 테스트
├── core/                 # Core 모듈 테스트
└── plugins/              # 플러그인 테스트
    └── {service}/
        └── test_{tool}.py
```

## 테스트 패턴

### 기본 테스트

```python
import pytest
from unittest.mock import MagicMock
from plugins.ec2.unused import run, collect_volumes, analyze_volumes


class TestEbsUnused:
    def test_run_completes(self, mock_ctx):
        """run(ctx) 함수 정상 실행 테스트"""
        run(mock_ctx)

    def test_collect_volumes_returns_list(self, mock_session):
        """볼륨 수집 함수 테스트"""
        results = collect_volumes(mock_session, "123456789012", "test", "ap-northeast-2")
        assert isinstance(results, list)
```

### AWS 모킹 (moto)

```python
import boto3
from moto import mock_aws


@mock_aws
def test_describe_volumes():
    # Setup
    client = boto3.client('ec2', region_name='ap-northeast-2')
    client.create_volume(
        AvailabilityZone='ap-northeast-2a',
        Size=100,
    )

    # Test
    response = client.describe_volumes()

    # Assert
    assert len(response['Volumes']) == 1
    assert response['Volumes'][0]['Size'] == 100
```

### Fixture 사용

```python
# tests/conftest.py
import pytest
import boto3
from moto import mock_aws


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials"""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-2'


@pytest.fixture
def mock_ec2(aws_credentials):
    with mock_aws():
        client = boto3.client('ec2', region_name='ap-northeast-2')
        yield client


# 테스트에서 사용
def test_with_fixture(mock_ec2):
    mock_ec2.create_volume(AvailabilityZone='ap-northeast-2a', Size=100)
    response = mock_ec2.describe_volumes()
    assert len(response['Volumes']) == 1
```

## 테스트 케이스 유형

### 1. 정상 케이스
```python
def test_find_unused_volumes_returns_unattached():
    # 미연결 볼륨 생성
    # 함수 실행
    # 결과 검증
```

### 2. 엣지 케이스
```python
def test_find_unused_volumes_empty_region():
    # 빈 리전에서 빈 리스트 반환 검증
```

### 3. 에러 케이스
```python
def test_analyze_region_access_denied():
    # AccessDenied 시 빈 리스트 반환 검증
```

## CLI 테스트

```python
from click.testing import CliRunner
from cli.app import cli


def test_list_tools_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['list-tools'])

    assert result.exit_code == 0
    assert 'ec2' in result.output


def test_version_option():
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    assert result.exit_code == 0
```

## 테스트 명명

```python
def test_함수명_상황_예상결과():
    ...

# 예시
def test_find_unused_when_no_volumes_returns_empty():
    ...

def test_analyze_region_with_throttling_retries():
    ...
```

## 통합 테스트

### parallel_collect + InventoryCollector 연동

```python
import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws

from core.parallel import parallel_collect
from plugins.resource_explorer.common.collector import InventoryCollector


class TestParallelCollectIntegration:
    """병렬 수집 통합 테스트"""

    @mock_aws
    def test_parallel_collect_with_multiple_regions(self, mock_ctx):
        """다중 리전 병렬 수집 테스트"""
        # 여러 리전에 리소스 생성
        import boto3
        for region in ["ap-northeast-2", "us-east-1"]:
            ec2 = boto3.client("ec2", region_name=region)
            ec2.create_vpc(CidrBlock="10.0.0.0/16")

        def _collect(session, account_id, account_name, region):
            ec2 = session.client("ec2", region_name=region)
            return ec2.describe_vpcs()["Vpcs"]

        mock_ctx.regions = ["ap-northeast-2", "us-east-1"]
        result = parallel_collect(mock_ctx, _collect, service="ec2")

        data = result.get_flat_data()
        assert len(data) == 2  # 각 리전에서 1개씩


class TestInventoryCollectorIntegration:
    """인벤토리 수집기 통합 테스트"""

    @mock_aws
    def test_collector_caches_results(self, mock_ctx):
        """수집 결과 캐싱 테스트"""
        collector = InventoryCollector(mock_ctx)

        # 첫 번째 호출
        vpcs1 = collector.collect_vpcs()

        # 두 번째 호출 (캐시에서 반환)
        vpcs2 = collector.collect_vpcs()

        assert vpcs1 == vpcs2


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.provider = MagicMock()
    ctx.regions = ["ap-northeast-2"]
    ctx.provider.get_session.return_value = MagicMock()
    return ctx
```

## E2E 테스트

### CLI Headless 모드 전체 플로우

```python
import os
import pytest
from click.testing import CliRunner
from cli.app import cli


class TestHeadlessModeE2E:
    """Headless 모드 E2E 테스트"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, tmp_path):
        return str(tmp_path / "output.json")

    def test_run_tool_with_json_output(self, runner, temp_output):
        """JSON 출력 E2E 테스트"""
        result = runner.invoke(cli, [
            "run", "ec2/ebs_audit",
            "-p", "test-profile",
            "-r", "ap-northeast-2",
            "-f", "json",
            "-o", temp_output,
            "-q"  # quiet 모드
        ])

        # 명령 실행 성공 (프로파일 없으면 에러 가능)
        # 실제 E2E 테스트는 유효한 프로파일 필요
        assert result.exit_code in [0, 1]

    def test_run_tool_with_csv_output(self, runner, temp_output):
        """CSV 출력 E2E 테스트"""
        temp_csv = temp_output.replace(".json", ".csv")
        result = runner.invoke(cli, [
            "run", "vpc/eip_unused",
            "-p", "test-profile",
            "-r", "ap-northeast-2",
            "-f", "csv",
            "-o", temp_csv,
        ])

        assert result.exit_code in [0, 1]

    def test_run_with_multiple_regions(self, runner):
        """다중 리전 E2E 테스트"""
        result = runner.invoke(cli, [
            "run", "lambda/unused",
            "-p", "test-profile",
            "-r", "ap-northeast-2",
            "-r", "us-east-1",
        ])

        assert result.exit_code in [0, 1]

    def test_list_tools_command(self, runner):
        """도구 목록 조회 E2E 테스트"""
        result = runner.invoke(cli, ["list-tools"])

        assert result.exit_code == 0
        assert "ec2" in result.output.lower()
```

## 성능/벤치마크 테스트

### pytest-benchmark 사용

```python
import pytest
from unittest.mock import MagicMock


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
        from plugins.cloudwatch.common.batch_metrics import (
            build_lambda_metric_queries,
        )

        function_names = [f"func-{i}" for i in range(100)]

        queries = benchmark(
            build_lambda_metric_queries,
            function_names,
            ["Invocations", "Errors"]
        )

        assert len(queries) == 200  # 100 함수 × 2 메트릭


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.provider = MagicMock()
    ctx.regions = ["ap-northeast-2"]
    return ctx
```

### 메모리 프로파일링

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

        # 제너레이터 소비
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

### pytest.ini 벤치마크 설정

```ini
# pytest.ini 또는 pyproject.toml
[tool.pytest.ini_options]
markers = [
    "benchmark: 성능 벤치마크 테스트",
    "memory: 메모리 프로파일링 테스트",
    "e2e: End-to-End 테스트",
    "integration: 통합 테스트",
]

# 벤치마크 실행
# pytest tests/ -m benchmark --benchmark-only
# pytest tests/ -m memory
```

## 테스트 데이터 팩토리

### 리소스 팩토리 패턴

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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

    def with_state(self, state: str) -> "EC2InstanceFactory":
        self.state = state
        return self

    def stopped(self) -> "EC2InstanceFactory":
        return self.with_state("stopped")

    def running(self) -> "EC2InstanceFactory":
        return self.with_state("running")


@dataclass
class EBSVolumeFactory:
    """EBS 볼륨 테스트 데이터 팩토리"""

    volume_id: str = ""
    size: int = 100
    state: str = "available"
    volume_type: str = "gp3"
    attachments: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.volume_id:
            self.volume_id = f"vol-{''.join(random.choices(string.hexdigits.lower(), k=17))}"

    def build(self) -> dict:
        return {
            "VolumeId": self.volume_id,
            "Size": self.size,
            "State": self.state,
            "VolumeType": self.volume_type,
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
    """팩토리 사용 예시"""
    # 실행 중인 인스턴스
    instance = EC2InstanceFactory().with_name("web-server").running().build()

    # 미연결 볼륨
    volume = EBSVolumeFactory().unattached().build()

    # 연결된 볼륨
    attached_vol = EBSVolumeFactory().attached_to(instance["InstanceId"]).build()

    assert instance["State"]["Name"] == "running"
    assert volume["State"] == "available"
    assert attached_vol["State"] == "in-use"
```

### Fixture 기반 팩토리

```python
import pytest


@pytest.fixture
def ec2_instance_factory():
    """EC2 인스턴스 팩토리 fixture"""
    return EC2InstanceFactory


@pytest.fixture
def ebs_volume_factory():
    """EBS 볼륨 팩토리 fixture"""
    return EBSVolumeFactory


@pytest.fixture
def sample_instances(ec2_instance_factory):
    """샘플 인스턴스 세트"""
    return [
        ec2_instance_factory().with_name("web-1").running().build(),
        ec2_instance_factory().with_name("web-2").running().build(),
        ec2_instance_factory().with_name("batch").stopped().build(),
    ]


def test_with_factory_fixture(sample_instances):
    """fixture로 생성된 인스턴스 테스트"""
    running = [i for i in sample_instances if i["State"]["Name"] == "running"]
    assert len(running) == 2
```

## 테스트 작성 체크리스트

```markdown
## 테스트 체크리스트

### 커버리지
- [ ] 정상 케이스
- [ ] 엣지 케이스 (빈 리스트, None)
- [ ] 에러 케이스 (AccessDenied, Throttling)

### 품질
- [ ] 독립적인 테스트 (순서 무관)
- [ ] 명확한 테스트 이름
- [ ] 적절한 assertion

### AWS 모킹
- [ ] @mock_aws 데코레이터
- [ ] 필요한 리소스 생성
- [ ] Fixture 활용

### 통합 테스트
- [ ] parallel_collect 연동 테스트
- [ ] InventoryCollector 캐싱 테스트
- [ ] 다중 계정/리전 시나리오

### E2E 테스트
- [ ] CLI Headless 모드 테스트
- [ ] 출력 형식별 테스트 (JSON, CSV)
- [ ] 에러 시나리오 테스트

### 성능 테스트
- [ ] 벤치마크 테스트 (@pytest.mark.benchmark)
- [ ] 메모리 사용량 테스트 (@pytest.mark.memory)
- [ ] 대용량 데이터 처리 테스트
```

## 테스트 실행

```bash
# 전체
pytest tests/ -v

# 특정 파일
pytest tests/plugins/ec2/test_ebs_audit.py -v

# 커버리지
pytest tests/ --cov=plugins --cov-report=html

# 실패 시 즉시 중단
pytest tests/ -x
```
