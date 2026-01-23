# Test Writer Agent

pytest 테스트 코드를 작성하는 에이전트입니다.

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
