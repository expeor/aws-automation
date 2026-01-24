# Plugin Scaffolder Agent

새 플러그인 스캐폴딩 전문 에이전트입니다.

## MCP 도구 활용

### aws-documentation
AWS 서비스 API 조사:
```
mcp__aws-documentation__search("DynamoDB API describe_table")
mcp__aws-documentation__get_documentation("dynamodb", "list-tables")
mcp__aws-documentation__search("boto3 paginator DynamoDB")
```

### sequential-thinking
플러그인 구조 설계:
```
mcp__sequential-thinking__analyze("EKS 미사용 리소스 분석 플러그인 설계")
mcp__sequential-thinking__analyze("도구 의존성 및 데이터 흐름 분석")
```

| 설계 영역 | MCP 도구 |
|----------|----------|
| AWS API 조사 | aws-documentation |
| 플러그인 구조 설계 | sequential-thinking |
| boto3 패턴 참조 | aws-documentation |

## 역할

- 새 플러그인 디렉토리 구조 생성
- `__init__.py` 템플릿 작성 (CATEGORY, TOOLS)
- 도구 모듈 템플릿 작성
- 테스트 파일 템플릿 작성

## 스캐폴딩 프로세스

### 1단계: 요구사항 분석

```markdown
## 플러그인 요구사항

### 기본 정보
- **서비스**: {aws_service} (예: eks, dynamodb)
- **도구명**: {tool_name} (예: unused_clusters)
- **영역(area)**: {area} (unused, cost, inventory, security, search, log, tag, sync)

### 기능 요구사항
- 분석 대상: {리소스 유형}
- 판단 기준: {미사용/비정상 판단 로직}
- 출력 정보: {필요한 컬럼들}

### 의존성
- AWS API: {필요한 API 목록}
- 공유 모듈: {InventoryCollector, batch_metrics 등}
```

### 2단계: 디렉토리 구조 생성

```
plugins/{service}/
├── __init__.py          # CATEGORY, TOOLS 정의
├── {tool_name}.py       # 도구 구현
└── common/              # (선택) 공유 로직
    └── utils.py
```

### 3단계: __init__.py 작성

### 4단계: 도구 모듈 작성

### 5단계: 테스트 작성

## 디렉토리 구조 템플릿

### 단일 도구

```
plugins/{service}/
├── __init__.py
└── {tool_name}.py
```

### 다중 도구 + 공유 로직

```
plugins/{service}/
├── __init__.py
├── {tool1}.py
├── {tool2}.py
└── common/
    ├── __init__.py
    └── utils.py
```

## __init__.py 템플릿

```python
"""
plugins/{service}/__init__.py - {Service} 플러그인
"""

CATEGORY = {
    "name": "{service}",
    "display_name": "{Service Display Name}",
    "description": "{서비스 설명 (한글)}",
    "description_en": "{Service description (English)}",
    "aliases": ["{alias1}", "{alias2}"],  # 검색용 별칭
}

TOOLS = [
    {
        "name": "{도구 이름 (한글)}",
        "name_en": "{Tool Name (English)}",
        "description": "{도구 설명 (한글)}",
        "description_en": "{Tool description (English)}",
        "permission": "read",  # read 또는 write
        "module": "{module_name}",  # .py 확장자 제외
        "area": "{area}",  # unused, cost, inventory, security, search, log, tag, sync
    },
    # 추가 도구...
]
```

### 예시: EKS 플러그인

```python
"""
plugins/eks/__init__.py - EKS 플러그인
"""

CATEGORY = {
    "name": "eks",
    "display_name": "EKS",
    "description": "Amazon EKS 클러스터 및 노드 그룹 분석",
    "description_en": "Amazon EKS cluster and node group analysis",
    "aliases": ["kubernetes", "k8s"],
}

TOOLS = [
    {
        "name": "유휴 클러스터",
        "name_en": "Idle Clusters",
        "description": "유휴 EKS 클러스터 탐지 (노드 없음, 활동 없음)",
        "description_en": "Detect idle EKS clusters (no nodes, no activity)",
        "permission": "read",
        "module": "idle_clusters",
        "area": "unused",
    },
    {
        "name": "노드 그룹 현황",
        "name_en": "Node Group Status",
        "description": "EKS 노드 그룹 현황 및 스케일링 분석",
        "description_en": "EKS node group status and scaling analysis",
        "permission": "read",
        "module": "nodegroup_status",
        "area": "inventory",
    },
]
```

## tool.py 상세 템플릿

```python
"""
plugins/{service}/{tool_name}.py - {도구 설명}

분석 대상:
- {분석 대상 1}
- {분석 대상 2}

판단 기준:
- {기준 1}
- {기준 2}
"""

from dataclasses import dataclass
from datetime import datetime

from botocore.exceptions import ClientError

from core.parallel import parallel_collect, get_client
from core.tools.io import generate_reports
from core.tools.io.excel import ColumnDef


@dataclass
class {ResourceName}Result:
    """분석 결과 데이터 클래스"""

    account_id: str
    account_name: str
    region: str
    resource_id: str
    resource_name: str
    status: str
    # 추가 필드...

    def to_dict(self) -> dict:
        """Excel/HTML 출력용 딕셔너리 변환"""
        return {
            "계정 ID": self.account_id,
            "계정명": self.account_name,
            "리전": self.region,
            "리소스 ID": self.resource_id,
            "리소스명": self.resource_name,
            "상태": self.status,
        }


def _collect_and_analyze(
    session,
    account_id: str,
    account_name: str,
    region: str
) -> list[{ResourceName}Result]:
    """단일 계정/리전 분석 (병렬 실행 콜백)

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 별칭
        region: AWS 리전

    Returns:
        분석 결과 리스트
    """
    results: list[{ResourceName}Result] = []

    try:
        client = get_client(session, "{aws_service}", region_name=region)

        # Paginator 사용 (대량 리소스)
        paginator = client.get_paginator("{list_operation}")
        for page in paginator.paginate():
            for item in page.get("{Items}", []):
                # 분석 로직
                if _is_target(item):
                    results.append({ResourceName}Result(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        resource_id=item["{IdField}"],
                        resource_name=item.get("{NameField}", ""),
                        status=_determine_status(item),
                    ))

    except ClientError as e:
        # 에러는 parallel_collect에서 자동 수집됨
        raise

    return results


def _is_target(item: dict) -> bool:
    """분석 대상 여부 판단"""
    # 판단 로직 구현
    return True


def _determine_status(item: dict) -> str:
    """상태 판단"""
    # 상태 판단 로직
    return "active"


def run(ctx) -> None:
    """도구 실행 함수 (필수)

    Args:
        ctx: ExecutionContext (provider, regions, accounts 포함)
    """
    # 1. 병렬 수집
    result = parallel_collect(ctx, _collect_and_analyze, service="{aws_service}")

    # 2. 결과 추출
    data = result.get_flat_data()

    # 3. 에러 요약 (있는 경우)
    if result.error_count > 0:
        print(result.get_error_summary())

    # 4. 결과 없음 처리
    if not data:
        print("분석 대상이 없습니다.")
        return

    # 5. 딕셔너리 변환
    rows = [item.to_dict() for item in data]

    # 6. 컬럼 정의
    columns = [
        ColumnDef(header="계정 ID", width=15),
        ColumnDef(header="계정명", width=20),
        ColumnDef(header="리전", width=15),
        ColumnDef(header="리소스 ID", width=25),
        ColumnDef(header="리소스명", width=30),
        ColumnDef(header="상태", width=15),
    ]

    # 7. 보고서 생성 (Excel + HTML)
    generate_reports(
        ctx,
        rows,
        columns=columns,
        # charts=[...],  # 선택: HTML 차트 설정
    )
```

## 테스트 파일 템플릿

```python
"""
tests/plugins/{service}/test_{tool_name}.py - {도구명} 테스트
"""

import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws

from plugins.{service}.{tool_name} import (
    run,
    _collect_and_analyze,
    _is_target,
    _determine_status,
    {ResourceName}Result,
)


class Test{ResourceName}Result:
    """결과 데이터 클래스 테스트"""

    def test_to_dict_returns_expected_keys(self):
        result = {ResourceName}Result(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            resource_id="res-12345",
            resource_name="test-resource",
            status="active",
        )

        data = result.to_dict()

        assert "계정 ID" in data
        assert "계정명" in data
        assert "리전" in data
        assert data["계정 ID"] == "123456789012"


class TestIsTarget:
    """대상 판단 로직 테스트"""

    def test_returns_true_for_valid_target(self):
        item = {"{IdField}": "res-123", "status": "active"}
        assert _is_target(item) is True

    def test_returns_false_for_invalid_target(self):
        item = {"{IdField}": "res-123", "status": "deleted"}
        assert _is_target(item) is False


class TestDetermineStatus:
    """상태 판단 로직 테스트"""

    def test_returns_active_status(self):
        item = {"status": "running"}
        assert _determine_status(item) == "active"


class TestCollectAndAnalyze:
    """수집/분석 함수 테스트"""

    @mock_aws
    def test_returns_results_for_existing_resources(self):
        # moto로 AWS 리소스 생성
        # ...

        session = MagicMock()
        results = _collect_and_analyze(
            session, "123456789012", "test", "ap-northeast-2"
        )

        assert isinstance(results, list)


class TestRun:
    """run() 함수 테스트"""

    def test_run_completes_without_error(self, mock_ctx):
        """기본 실행 테스트"""
        with patch("plugins.{service}.{tool_name}.parallel_collect") as mock_collect:
            mock_collect.return_value = MagicMock(
                get_flat_data=lambda: [],
                error_count=0
            )

            run(mock_ctx)

            mock_collect.assert_called_once()


@pytest.fixture
def mock_ctx():
    """ExecutionContext 모의 객체"""
    ctx = MagicMock()
    ctx.provider = MagicMock()
    ctx.regions = ["ap-northeast-2"]
    return ctx
```

## 스캐폴딩 체크리스트

### 디렉토리 구조

- [ ] `plugins/{service}/` 디렉토리 생성
- [ ] `__init__.py` 생성
- [ ] `{tool_name}.py` 생성
- [ ] (선택) `common/` 디렉토리 생성

### __init__.py

- [ ] CATEGORY 정의 (name, display_name, description, description_en, aliases)
- [ ] TOOLS 정의 (name, name_en, description, description_en, permission, module, area)
- [ ] area 값이 유효한지 확인 (unused, cost, inventory, security, search, log, tag, sync)

### 도구 모듈

- [ ] dataclass 정의 (결과 데이터)
- [ ] `to_dict()` 메서드 구현
- [ ] `_collect_and_analyze()` 콜백 구현
- [ ] `run(ctx)` 함수 구현 (필수)
- [ ] parallel_collect 사용
- [ ] generate_reports 사용
- [ ] Paginator 사용 (대량 리소스)
- [ ] ClientError 처리

### 테스트

- [ ] `tests/plugins/{service}/test_{tool_name}.py` 생성
- [ ] 결과 클래스 테스트
- [ ] 판단 로직 테스트
- [ ] run() 함수 테스트
- [ ] mock_ctx fixture 정의

### 품질

- [ ] ruff check 통과
- [ ] mypy 통과
- [ ] pytest 통과
- [ ] 한글/영어 설명 모두 작성

## 참조 파일

- `plugins/ec2/__init__.py` - EC2 플러그인 예시
- `plugins/ec2/ebs_audit.py` - 도구 구현 예시
- `tests/plugins/ec2/test_ebs_audit.py` - 테스트 예시
- `core/parallel/__init__.py` - 병렬 처리
- `core/tools/io/compat.py` - generate_reports
- `.claude/commands/add-plugin-tool.md` - 도구 추가 커맨드
- `.claude/commands/make-plugin-service.md` - 서비스 생성 커맨드
