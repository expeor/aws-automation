# TDD 워크플로우

테스트 주도 개발 가이드입니다.

## TDD 사이클

1. **Red**: 실패하는 테스트 작성
2. **Green**: 테스트 통과하는 최소 코드 작성
3. **Refactor**: 코드 개선 (테스트 통과 유지)

## 프로젝트 테스트 구조

```
tests/
├── conftest.py           # pytest fixtures
├── cli/                  # CLI 테스트
├── core/                 # Core 모듈 테스트
└── plugins/              # 플러그인 테스트
```

## 테스트 작성 패턴

### 기본 테스트

```python
# tests/plugins/ec2/test_unused.py
import pytest
from unittest.mock import MagicMock
from plugins.ec2.unused import run, collect_volumes, analyze_volumes


class TestEbsUnused:
    def test_run_completes_without_error(self, mock_ctx):
        """run(ctx) 함수 정상 실행 테스트"""
        run(mock_ctx)
        # 에러 없이 완료되면 성공

    def test_collect_volumes_returns_list(self, mock_ec2_session):
        """볼륨 수집 함수 테스트"""
        results = collect_volumes(
            mock_ec2_session, "123456789012", "test-account", "ap-northeast-2"
        )
        assert isinstance(results, list)
```

### AWS 모킹 (moto)

```python
import boto3
from moto import mock_aws


@mock_aws
def test_describe_instances():
    # moto가 AWS를 모킹
    client = boto3.client('ec2', region_name='ap-northeast-2')

    # 테스트 데이터 생성
    client.run_instances(
        ImageId='ami-12345678',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
    )

    # 테스트 실행
    response = client.describe_instances()
    assert len(response['Reservations']) == 1
```

### Fixture 사용

```python
# tests/conftest.py
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials"""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture
def mock_ec2(aws_credentials):
    """Mocked EC2 client"""
    with mock_aws():
        yield boto3.client('ec2', region_name='ap-northeast-2')
```

## 테스트 명명 규칙

```python
def test_함수명_상황_예상결과():
    ...

# 예시
def test_find_unused_volumes_when_no_attachments_returns_volume():
    ...

def test_analyze_region_with_access_denied_returns_empty_list():
    ...
```

## 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 특정 파일
pytest tests/plugins/ec2/test_ebs_audit.py -v

# 특정 함수
pytest tests/plugins/ec2/test_ebs_audit.py::test_unused_volumes -v

# 커버리지
pytest tests/ --cov=core --cov=cli --cov=plugins --cov-report=html

# 실패 시 즉시 중단
pytest tests/ -x

# 마지막 실패 테스트만
pytest tests/ --lf
```

## 테스트 카테고리

### 단위 테스트
개별 함수/메서드 테스트:
```python
def test_validate_account_id():
    assert validate_account_id('123456789012') is True
    assert validate_account_id('invalid') is False
```

### 통합 테스트
모듈 간 상호작용 테스트:
```python
@mock_aws
def test_ebs_audit_full_workflow():
    # 데이터 생성 → 분석 → 결과 검증
```

### E2E 테스트
전체 CLI 플로우 테스트:
```python
from click.testing import CliRunner
from cli.app import cli

def test_list_tools_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['list-tools'])
    assert result.exit_code == 0
    assert 'ec2' in result.output
```

## 테스트 체크리스트

새 기능 추가 시:
- [ ] 정상 케이스 테스트
- [ ] 엣지 케이스 테스트 (빈 목록, None 등)
- [ ] 에러 케이스 테스트 (AccessDenied 등)
- [ ] moto로 AWS 모킹
- [ ] 린트 통과 확인

버그 수정 시:
- [ ] 버그 재현 테스트 먼저 작성
- [ ] 테스트 실패 확인 (Red)
- [ ] 수정 후 테스트 통과 확인 (Green)
