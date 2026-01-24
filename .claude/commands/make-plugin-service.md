---
description: 새로운 AWS 서비스 플러그인 생성 (폴더 + __init__.py + tool.py + discovery 등록)
---

# 새 AWS Plugin Service 생성

**새로운 AWS 서비스**를 처음 추가할 때 사용합니다.
기존 서비스에 도구만 추가하려면 `/add-plugin-tool`을 사용하세요.

## 입력

$ARGUMENTS

---

## MCP 도구 활용

플러그인 생성 시 다음 MCP 도구를 활용하여 정확한 AWS API 정보를 조사하고 구조를 설계합니다.

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

### context7

라이브러리 문서 참조:
```
mcp__context7__resolve("boto3")
mcp__context7__get_library_docs("boto3", "paginator")
```

| 설계 영역 | MCP 도구 |
|----------|----------|
| AWS API 조사 | aws-documentation |
| boto3 패턴 참조 | aws-documentation, context7 |
| 플러그인 구조 설계 | sequential-thinking |

---

## 생성할 파일 목록

1. `plugins/{service}/__init__.py` - 카테고리 메타데이터
2. `plugins/{service}/{type}.py` - 도구 구현 (파일명 = 타입명)
3. `core/tools/discovery.py` 수정 - `AWS_SERVICE_NAMES`에 등록

---

## 타입 체계 (중요!)

### ReportType (10개) - 상태 점검 보고서 (read-only)

| 타입 | 파일명 | 용도 | 키워드 |
|------|--------|------|--------|
| `inventory` | `inventory.py` | 리소스 현황 파악 | 목록, 현황, 인벤토리 |
| `security` | `security.py` | 보안 취약점 탐지 | 보안, 취약점, 권한, 노출 |
| `cost` | `cost.py` | 비용 최적화 기회 | 비용, 절감, 최적화 |
| `unused` | `unused.py` | 미사용 리소스 식별 | 미사용, unused, idle, 삭제 |
| `audit` | `audit.py` | 구성 설정 점검 | 설정, 구성, 베스트프랙티스 |
| `compliance` | `compliance.py` | 규정 준수 검증 | 규정, 정책, 표준 |
| `performance` | `performance.py` | 성능 병목 분석 | 성능, 병목, 느림 |
| `network` | `network.py` | 네트워크 구조 분석 | 네트워크, 연결, 라우팅 |
| `backup` | `backup.py` | 백업 체계 점검 | 백업, 복구, 스냅샷 |
| `quota` | `quota.py` | 서비스 한도 모니터링 | 한도, 쿼터, 제한 |

### ToolType (5개) - 도구 (active operations)

| 타입 | 파일명 | 용도 | 키워드 |
|------|--------|------|--------|
| `log` | `log.py` | 로그 분석 및 검색 | 로그, 분석, 검색 |
| `search` | `search.py` | 리소스 역추적 | 검색, 찾기, 추적 |
| `cleanup` | `cleanup.py` | 리소스 정리/삭제 | 정리, 삭제, 제거 |
| `tag` | `tag.py` | 태그 일괄 적용 | 태그, 레이블 |
| `sync` | `sync.py` | 설정/태그 동기화 | 동기화, 복제 |

---

## 프롬프트 분석

프롬프트에서 다음 정보를 추출하세요:

| 항목 | 예시 |
|------|------|
| **service** (소문자) | `efs`, `bedrock`, `glue` |
| **display_name** | `EFS`, `Bedrock`, `Glue` |
| **tool_name** (한글) | `미사용 EFS 파일시스템 분석` |
| **type** (타입명) | `unused`, `security`, `cost` 등 |
| **aws_service** (boto3 서비스명) | `efs`, `bedrock-runtime`, `glue` |

**타입 분류 질문:**
- "돈 아낄 수 있나?" → `cost`
- "안 쓰는 거 있나?" → `unused`
- "보안 문제 있나?" → `security`
- "뭐가 있나?" → `inventory`
- "설정 잘 되어있나?" → `audit`

---

## 파일 생성

### 1. `core/tools/discovery.py` 수정

```python
# 라인 94~148의 AWS_SERVICE_NAMES에 추가
AWS_SERVICE_NAMES = {
    # ... 기존 서비스들 ...
    "{service}",  # 새로 추가
}
```

### 2. `plugins/{service}/__init__.py`

```python
"""
plugins/{service} - {display_name} 관리 도구
"""

CATEGORY = {
    "name": "{service}",
    "display_name": "{display_name}",
    "description": "{service_description}",
    "description_en": "{service_description_en}",
    "aliases": [],
}

TOOLS = [
    {
        "name": "{tool_name}",
        "name_en": "{tool_name_en}",
        "description": "{tool_description}",
        "description_en": "{tool_description_en}",
        "permission": "read",
        "module": "{type}",  # 파일명 = 타입명
        "area": "{type}",    # ReportType 또는 ToolType
    },
]
```

### 3. `plugins/{service}/{type}.py`

**파일명은 반드시 타입명과 일치해야 합니다!**

```python
"""
plugins/{service}/{type}.py - {tool_name}

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from rich.console import Console

from core.parallel import get_client, parallel_collect
from core.tools.output import OutputPath, open_in_explorer

console = Console()

REQUIRED_PERMISSIONS = {
    "read": [
        "{aws_service}:{Permission1}",
        "{aws_service}:{Permission2}",
    ],
}


class {Resource}Status(Enum):
    NORMAL = "normal"
    UNUSED = "unused"


@dataclass
class {Resource}Info:
    account_id: str
    account_name: str
    region: str
    id: str
    name: str
    # TODO: 리소스별 속성


@dataclass
class {Resource}AnalysisResult:
    account_id: str
    account_name: str
    region: str
    total_count: int = 0
    unused_count: int = 0
    findings: list = field(default_factory=list)


def collect_{resources}(session, account_id: str, account_name: str, region: str) -> list[{Resource}Info]:
    """리소스 수집"""
    from botocore.exceptions import ClientError

    client = get_client(session, "{aws_service}", region_name=region)
    resources = []

    try:
        # TODO: AWS API 호출
        # paginator = client.get_paginator("list_{resources}")
        # for page in paginator.paginate():
        #     for item in page.get("{Resources}", []):
        #         resources.append({Resource}Info(...))
        pass
    except ClientError:
        pass

    return resources


def analyze_{resources}(resources: list[{Resource}Info], account_id: str, account_name: str, region: str) -> {Resource}AnalysisResult:
    """리소스 분석"""
    result = {Resource}AnalysisResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_count=len(resources),
    )
    # TODO: 분석 로직
    return result


def _save_excel(results: list[{Resource}AnalysisResult], output_dir: str) -> str:
    """Excel 보고서 생성 (내부 함수)"""
    from core.tools.io.excel import Workbook, ColumnDef, Styles

    wb = Workbook()

    # Summary 시트
    summary = wb.new_summary_sheet()
    summary.add_title("{display_name} 분석 보고서")
    summary.add_section("요약")
    summary.add_item("전체 리소스", sum(r.total_count for r in results))
    summary.add_item("미사용", sum(r.unused_count for r in results), highlight="danger")

    # Detail 시트
    columns = [
        ColumnDef(header="Account", width=20),
        ColumnDef(header="Region", width=15),
        ColumnDef(header="Resource ID", width=25),
        # TODO: 리소스별 컬럼 추가
    ]
    sheet = wb.new_sheet("Details", columns)

    for r in results:
        for finding in r.findings:
            sheet.add_row([
                r.account_name,
                r.region,
                finding.id,
                # TODO: 리소스별 데이터
            ])

    return str(wb.save_as(output_dir, "{Service}_{Type}"))


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> {Resource}AnalysisResult | None:
    """병렬 실행용 래퍼"""
    resources = collect_{resources}(session, account_id, account_name, region)
    if not resources:
        return None
    return analyze_{resources}(resources, account_id, account_name, region)


def run(ctx) -> None:
    """{tool_name}"""
    from core.tools.io.compat import generate_reports

    console.print("[bold]{display_name} 분석 시작...[/bold]\n")

    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="{aws_service}")
    results = [r for r in result.get_data() if r is not None]

    if not results:
        console.print("[yellow]분석 결과 없음[/yellow]")
        return

    # 결과 요약
    total = sum(r.total_count for r in results)
    unused = sum(r.unused_count for r in results)
    console.print(f"전체: {total}개, 미사용: [red]{unused}개[/red]")

    # HTML용 flat 데이터 준비
    flat_data = [
        {
            "account_id": r.account_id,
            "account_name": r.account_name,
            "region": r.region,
            "resource_id": f.id,
            "status": f.status,
            "reason": f.reason,
            # TODO: 리소스별 추가 필드
        }
        for r in results
        for f in r.findings
    ]

    # 보고서 경로 - 형식: output/{identifier}/{service}/{type}/{date}/
    identifier = ctx.accounts[0].id if ctx.accounts else ctx.profile_name or "default"
    output_path = OutputPath(identifier).sub("{service}", "{type}").with_date().build()

    # Excel + HTML 동시 생성 (ctx.output_config에 따라)
    report_paths = generate_reports(
        ctx,
        data=flat_data,
        excel_generator=lambda d: _save_excel(results, d),
        html_config={
            "title": "{tool_name}",
            "service": "{display_name}",
            "tool_name": "{type}",
            "total": total,
            "found": unused,
        },
        output_dir=output_path,
    )

    console.print("\n[bold green]완료![/bold green]")
    for fmt, path in report_paths.items():
        console.print(f"  {fmt.upper()}: {path}")
```

---

## Output 경로 설정 가이드

```python
from core.tools.output import OutputPath, open_in_explorer

# 경로 형식: output/{identifier}/{service}/{type}/{date}/
output_path = OutputPath(identifier)  # identifier: 계정ID 또는 프로파일명
    .sub("{service}", "{type}")        # 서비스, 타입 (2개 인자)
    .with_date()                       # 날짜 폴더 추가 (YYYY-MM-DD)
    .build()                           # 최종 경로 반환

# 예시 결과:
# output/123456789012/efs/unused/2025-01-06/
# output/my-profile/cloudtrail/security/2025-01-06/
```

---

## 서브타입이 있는 서비스 (ELB, RDS 등)

AWS 서비스 중 여러 하위 타입이 있는 경우 (예: ELB → ALB, NLB, CLB, GWLB):

### 파일명 프리픽스 패턴 (권장)

```
plugins/elb/
├── __init__.py
├── common.py           # 공통 유틸리티 (선택)
├── alb_unused.py       # ALB 미사용
├── alb_security.py     # ALB 보안
├── nlb_unused.py       # NLB 미사용
├── clb_unused.py       # CLB 미사용
└── gwlb_inventory.py   # GWLB 인벤토리
```

### `__init__.py` 예시

```python
CATEGORY = {
    "name": "elb",
    "display_name": "ELB",
    "description": "Elastic Load Balancer 관리 도구",
    "description_en": "Elastic Load Balancer Management Tools",
    "aliases": ["alb", "nlb", "clb", "gwlb", "loadbalancer"],
}

TOOLS = [
    {
        "name": "ALB 미사용 분석",
        "name_en": "ALB Unused Analysis",
        "description": "미사용 ALB 탐지",
        "description_en": "Detect unused ALBs",
        "permission": "read",
        "module": "alb_unused",
        "area": "unused",
    },
    # ... 다른 도구들도 동일한 형식
]
```

### `common.py` 예시 (공통 유틸리티)

```python
from enum import Enum

class LBType(Enum):
    ALB = "application"
    NLB = "network"
    GWLB = "gateway"
    CLB = "classic"

# 공통 데이터클래스, boto3 클라이언트 헬퍼 등
# ALB/NLB/GWLB: elbv2 클라이언트
# CLB: elb 클라이언트
```

### 적용 대상 서비스

| 서비스 | 서브타입 | 파일명 프리픽스 | boto3 |
|--------|----------|-----------------|-------|
| `elb` | ALB, NLB, GWLB, CLB | `alb_`, `nlb_`, `gwlb_`, `clb_` | `elbv2`, `elb` |
| `elasticache` | Redis, Memcached | `redis_`, `memcached_` | `elasticache` |
| `mq` | RabbitMQ, ActiveMQ | `rabbitmq_`, `activemq_` | `mq` |
| `fsx` | Windows, Lustre, ONTAP, OpenZFS | `windows_`, `lustre_`, `ontap_`, `openzfs_` | `fsx` |

---

## 확장 가이드

### 같은 서비스에 다른 타입 도구 추가

기존 서비스 폴더에 새 타입 파일 추가:
```
plugins/efs/
├── __init__.py     # TOOLS 배열에 새 항목 추가
├── unused.py       # 기존
└── security.py     # 새로 추가
```

### 같은 타입에 기능 확장

기존 타입 파일에 함수 추가 (파일 분리 X):
```python
# plugins/ec2/unused.py
def analyze_eip(...): ...      # 기존
def analyze_snapshot(...): ... # 기존
def analyze_ami(...): ...      # 새로 추가
def run(ctx): ...              # 통합 실행
```

---

## Core 유틸리티 참조

### 필수 import

```python
# 병렬 처리 (필수)
from core.parallel import get_client, parallel_collect

# Output 경로 (필수)
from core.tools.output import OutputPath, open_in_explorer

# 리포트 출력 - Excel + HTML 동시 생성 (권장)
from core.tools.io.compat import generate_reports
```

### 선택 import

```python
# 출력 설정
from core.tools.io import OutputConfig, OutputFormat

# Quiet 모드 체크 (진행 표시 제어)
from core.parallel import is_quiet, quiet_mode, set_quiet

# Excel 유틸리티 (openpyxl 래퍼 - 더 간단한 API)
from core.tools.io.excel import Workbook, ColumnDef, Styles

# HTML 유틸리티
from core.tools.io.html import AWSReport, ResourceItem, create_aws_report

# 타입 체계 상수
from core.tools.output import ReportType, ToolType
```

---

## 참조 파일

생성 전 반드시 확인:
- `plugins/efs/__init__.py` - 메타데이터 예시
- `plugins/efs/unused.py` - 전체 구현 예시
- `plugins/ec2/unused.py` - Excel + HTML 통합 출력 예시
- `core/tools/output/report_types.py` - 타입 정의
- `core/tools/io/config.py` - OutputConfig, OutputFormat
- `core/tools/io/compat.py` - generate_reports 헬퍼
- `.claude/skills/output-patterns.md` - 리포트 출력 패턴 가이드

---

## 예시

**입력:**
```
/make-plugin-service Bedrock 모델 사용량 분석 도구
```

**분석:**
- service: `bedrock`
- display_name: `Bedrock`
- tool_name: `모델 사용량 분석`
- type: `cost` (사용량 분석 → 비용 관련)

**생성:**
1. `core/tools/discovery.py` - `"bedrock"` 추가
2. `plugins/bedrock/__init__.py`
3. `plugins/bedrock/cost.py`
