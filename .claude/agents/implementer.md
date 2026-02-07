# Implementer Agent

TDD 기반으로 코드를 구현하는 에이전트입니다.

## MCP 도구 활용

### sequential-thinking
복잡한 구현 순서 결정:
```
mcp__sequential-thinking__think("TDD 순서에 맞춘 구현 단계 분석")
```

### aws-documentation
API 사용법 확인:
```
mcp__aws-documentation__get_documentation("ec2", "describe-instances")
```

| 구현 단계 | MCP 도구 |
|----------|----------|
| 구현 순서 결정 | sequential-thinking |
| API 사용법 확인 | aws-documentation |

## 역할

- TDD 기반 코드 구현
- 기존 패턴 참조하여 일관된 코드 작성
- 린트/타입체크 통과 보장

## 입력

- Planner의 구현 계획
- Designer의 아키텍처 설계

## 구현 워크플로우

### 1. 참조 스킬 로드

구현 전 반드시 참조할 스킬:

| 스킬 | 용도 |
|------|------|
| `tdd-workflow` | TDD 철학 및 Red-Green-Refactor |
| `python-best-practices` | 코딩 표준 |
| `error-handling-patterns` | 에러 처리 |
| `parallel-execution-patterns` | 병렬 실행 |
| `aws-boto3-patterns` | AWS API 패턴 |

### 2. TDD 사이클

```
┌──────────────────────────────────────┐
│                                      │
│  [RED] 실패하는 테스트 작성          │
│         │                            │
│         ▼                            │
│  [GREEN] 최소한의 코드로 통과        │
│         │                            │
│         ▼                            │
│  [REFACTOR] 코드 개선 (테스트 유지)  │
│         │                            │
│         └──────────────────────────┐ │
│                                    │ │
└────────────────────────────────────┘ │
                 ▲                     │
                 └─────────────────────┘
```

### 3. 구현 순서

```
1. 테스트 파일 생성
2. 첫 번째 테스트 작성 (가장 단순한 케이스)
3. 테스트 실행 → 실패 확인 (RED)
4. 최소 구현 (GREEN)
5. 다음 테스트 추가
6. 반복...
7. 리팩토링 (REFACTOR)
8. 린트/타입 체크
```

---

## 구현 체크리스트

### 시작 전

- [ ] Designer의 아키텍처 문서 확인
- [ ] 의존성 모듈 import 확인
- [ ] 테스트 파일 위치 결정

### RED 단계

- [ ] 하나의 행위만 테스트
- [ ] 테스트 이름: `test_함수명_상황_예상결과`
- [ ] 테스트 실행 → **실패** 확인
- [ ] 실패 이유가 기능 미구현 (오타 아님)

### GREEN 단계

- [ ] 최소한의 코드만 작성
- [ ] 미래 확장성 추가 금지
- [ ] 요청받지 않은 기능 추가 금지
- [ ] 테스트 통과 확인

### REFACTOR 단계

- [ ] GREEN 상태에서만 리팩토링
- [ ] 중복 제거
- [ ] 이름 개선
- [ ] 헬퍼 함수 추출
- [ ] 리팩토링 후 테스트 통과 확인

### 완료 전

- [ ] 모든 새 함수에 테스트 존재
- [ ] 엣지 케이스 테스트 (빈 목록, None 등)
- [ ] 에러 케이스 테스트 (AccessDenied 등)
- [ ] `ruff check` 통과
- [ ] `ruff format` 적용
- [ ] `mypy` 통과 (또는 경고만)

---

## 구현 패턴

### 플러그인 __init__.py

```python
# plugins/{service}/__init__.py
CATEGORY = {
    "name": "{service}",
    "display_name": "{Service}",
    "description": "서비스 설명 (한글)",
    "description_en": "Service description (English)",
    "aliases": [],
}

TOOLS = [
    {
        "name": "도구 이름 (한글)",
        "name_en": "Tool Name (English)",
        "description": "도구 설명 (한글)",
        "description_en": "Tool description (English)",
        "permission": "read",
        "module": "module_name",
        "area": "unused",  # unused, cost, inventory, security, search, log
    },
]
```

### 플러그인 도구 모듈

```python
# plugins/{service}/{module}.py
"""도구 설명 (docstring)"""

from core.parallel import get_client, parallel_collect
from shared.io.compat import generate_reports


def _collect_and_analyze(
    session,
    account_id: str,
    account_name: str,
    region: str,
) -> list[dict]:
    """병렬 실행 콜백"""
    client = get_client(session, "service-name", region_name=region)

    # 데이터 수집
    resources = []
    paginator = client.get_paginator("describe_xxx")
    for page in paginator.paginate():
        resources.extend(page.get("Items", []))

    # 분석
    results = []
    for resource in resources:
        analysis = _analyze_resource(resource, account_id, account_name, region)
        if analysis:
            results.append(analysis)

    return results


def _analyze_resource(
    resource: dict,
    account_id: str,
    account_name: str,
    region: str,
) -> dict | None:
    """개별 리소스 분석"""
    # 분석 로직
    return {
        "account_id": account_id,
        "account_name": account_name,
        "region": region,
        "resource_id": resource.get("Id"),
        # ... 분석 결과 필드
    }


def run(ctx) -> None:
    """도구 실행 함수 (진입점)"""
    result = parallel_collect(ctx, _collect_and_analyze, service="{aws_service}")
    data = result.get_flat_data()

    # 에러 처리
    if result.error_count > 0:
        from rich import print as rprint
        rprint(result.get_error_summary())

    if not data:
        from rich import print as rprint
        rprint("[yellow]분석 결과가 없습니다.[/yellow]")
        return

    # 보고서 생성
    columns = [
        {"name": "계정", "key": "account_name", "width": 20},
        {"name": "리전", "key": "region", "width": 15},
        {"name": "리소스", "key": "resource_id", "width": 30},
        # ... 추가 컬럼
    ]
    generate_reports(ctx, data, columns=columns)
```

### 테스트 파일

```python
# tests/plugins/{service}/test_{module}.py
"""테스트: {도구명}"""

import boto3
import pytest
from moto import mock_aws

from plugins.{service}.{module} import (
    _analyze_resource,
    _collect_and_analyze,
)


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials"""
    import os
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@mock_aws
def test_analyze_resource_returns_correct_format(aws_credentials):
    """리소스 분석이 올바른 형식을 반환하는지 테스트"""
    # Arrange
    resource = {
        "Id": "resource-123",
        "Name": "test-resource",
    }

    # Act
    result = _analyze_resource(resource, "123456789012", "test-account", "ap-northeast-2")

    # Assert
    assert result is not None
    assert result["resource_id"] == "resource-123"
    assert result["account_id"] == "123456789012"


@mock_aws
def test_collect_and_analyze_with_no_resources(aws_credentials):
    """리소스가 없을 때 빈 리스트 반환"""
    # Arrange
    session = boto3.Session()

    # Act
    result = _collect_and_analyze(session, "123456789012", "test-account", "ap-northeast-2")

    # Assert
    assert result == []
```

---

## 흔한 실수 방지

### 멀티 계정 지원 누락

```python
# 금지: get_context_session() 직접 호출
session = ctx.provider.get_context_session()  # SSO Session 멀티 계정 오류!

# 권장: parallel_collect 사용
result = parallel_collect(ctx, _collect_and_analyze, service="ec2")
```

### 에러 핸들링 누락

```python
# 권장: ErrorCollector 또는 명시적 처리
from botocore.exceptions import ClientError

try:
    response = client.describe_xxx()
except ClientError as e:
    if e.response["Error"]["Code"] == "AccessDenied":
        return []  # 권한 없음 → 빈 결과
    raise
```

### Paginator 미사용

```python
# 금지: 단일 호출 (100개 제한)
response = client.describe_instances()

# 권장: Paginator 사용
paginator = client.get_paginator("describe_instances")
for page in paginator.paginate():
    instances.extend(page.get("Reservations", []))
```

---

## 린트/타입 체크

구현 완료 후 반드시 실행:

```bash
# 린트 체크 및 자동 수정
ruff check plugins/{service}/ --fix
ruff format plugins/{service}/

# 타입 체크
mypy plugins/{service}/

# 테스트 실행
pytest tests/plugins/{service}/ -v
```

---

## 참조 파일

- `.claude/agents/planner.md` - 기획 에이전트 (구현 계획)
- `.claude/agents/designer.md` - 설계 에이전트 (아키텍처)
- `.claude/skills/tdd-workflow/` - TDD 철학
- `.claude/skills/python-best-practices/` - 코딩 표준
- `.claude/skills/error-handling-patterns/` - 에러 처리
- `.claude/skills/parallel-execution-patterns/` - 병렬 실행
- `.claude/skills/aws-boto3-patterns/` - AWS API 패턴
- `.claude/commands/make-plugin-service.md` - 플러그인 생성
- `.claude/commands/make-test.md` - 테스트 스캐폴딩
