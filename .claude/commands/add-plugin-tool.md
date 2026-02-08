---
description: 기존 AWS 서비스에 새 도구 추가 (tool.py + TOOLS 배열 업데이트)
---

# 기존 서비스에 도구 추가

**이미 존재하는 AWS 서비스**에 새 도구를 추가할 때 사용합니다.
새로운 서비스를 처음 만들려면 `/make-plugin-service`를 사용하세요.

> **⚠️ 중요: 멀티 계정 지원 필수**
>
> 모든 도구는 반드시 `parallel_collect` 패턴을 사용해야 합니다.
> SSO Session에서 여러 계정을 선택할 수 있으므로, 단일 세션만 처리하면 오류가 발생합니다.
>
> - ✅ `parallel_collect(ctx, callback, service="ec2")` - 사용
> - ❌ `get_context_session(ctx, "us-east-1")` - 사용 금지
>
> 자세한 패턴은 `.claude/skills/parallel-execution-patterns/SKILL.md` 참조

## 입력

$ARGUMENTS

---

## MCP 도구 활용

도구 추가 시 다음 MCP 도구를 활용합니다.

### aws-documentation
AWS API 조사:
```
mcp__aws-documentation__search("EC2 describe security groups")
mcp__aws-documentation__get_documentation("ec2", "describe-security-groups")
```

### context7
라이브러리 문서 참조:
```
mcp__context7__resolve("boto3")
mcp__context7__get_library_docs("boto3", "EC2 paginator")
```

---

## 결정 플로우

```
프롬프트 분석
    │
    ▼
plugins/{service}/ 존재?
    │
    ├─ NO → /make-plugin-service 사용
    │
    └─ YES
        │
        ▼
    타입 결정 (unused/security/cost/...)
        │
        ▼
    plugins/{service}/{type}.py 존재?
        │
        ├─ YES → 기존 파일에 함수 추가 (Case 2)
        │
        └─ NO → 새 파일 생성 (Case 1)
```

---

## 타입 체계 (중요!)

### ReportType (10개) - 상태 점검 보고서 (read-only)

| 타입 | 파일명 | 용도 |
|------|--------|------|
| `inventory` | `inventory.py` | 리소스 현황 파악 |
| `security` | `security.py` | 보안 취약점 탐지 |
| `cost` | `cost.py` | 비용 최적화 기회 |
| `unused` | `unused.py` | 미사용 리소스 식별 |
| `audit` | `audit.py` | 구성 설정 점검 |
| `compliance` | `compliance.py` | 규정 준수 검증 |
| `performance` | `performance.py` | 성능 병목 분석 |
| `network` | `network.py` | 네트워크 구조 분석 |
| `backup` | `backup.py` | 백업 체계 점검 |
| `quota` | `quota.py` | 서비스 한도 모니터링 |

### ToolType (5개) - 도구 (active operations)

| 타입 | 파일명 | 용도 |
|------|--------|------|
| `log` | `log.py` | 로그 분석 및 검색 |
| `search` | `search.py` | 리소스 역추적 |
| `cleanup` | `cleanup.py` | 리소스 정리/삭제 |
| `tag` | `tag.py` | 태그 일괄 적용 |
| `sync` | `sync.py` | 설정/태그 동기화 |

---

## 생성/수정할 파일

**Case 1: 새로운 타입 추가**
1. `plugins/{service}/{type}.py` - 새 도구 구현 (생성)
2. `plugins/{service}/__init__.py` - TOOLS 배열에 항목 추가 (수정)

**Case 2: 기존 타입에 기능 확장**
1. `plugins/{service}/{type}.py` - 기존 파일에 함수 추가 (수정)
2. `plugins/{service}/__init__.py` - 필요시 TOOLS 업데이트 (수정)

---

## 프롬프트 분석

| 항목 | 예시 |
|------|------|
| **service** (기존 폴더명) | `ec2`, `efs`, `rds` |
| **tool_name** (한글) | `AMI 수명 분석` |
| **type** (타입명) | `unused`, `security`, `cost` 등 |

**타입 분류 질문:**

- "돈 아낄 수 있나?" → `cost`
- "안 쓰는 거 있나?" → `unused`
- "보안 문제 있나?" → `security`
- "뭐가 있나?" → `inventory`
- "설정 잘 되어있나?" → `audit`
- "로그 분석해줘" → `log`
- "이거 어디서 쓰이나?" → `search`

---

## 파일 수정/생성

### 1. 기존 타입 파일이 있는 경우 (확장)

**기존 파일에 함수 추가** (새 파일 생성 X):

```python
# plugins/ec2/unused.py - 기존 파일
def analyze_eip(...): ...       # 기존
def analyze_snapshot(...): ...  # 기존
def analyze_ami(...): ...       # 새로 추가!

def run(ctx):
    """통합 실행 - 모든 분석 포함"""
    # EIP, Snapshot, AMI 모두 분석
```

### 2. 새로운 타입 추가하는 경우

#### `plugins/{service}/__init__.py` 수정

TOOLS 배열에 새 항목 추가:

```python
TOOLS = [
    # ... 기존 도구들 ...
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

#### `plugins/{service}/{type}.py` 생성

**파일명은 반드시 타입명과 일치해야 합니다!**

```python
"""
plugins/{service}/{type}.py - {tool_name}

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console

from core.parallel import get_client, parallel_collect
from core.shared.io.output import OutputPath, open_in_explorer

console = Console()

REQUIRED_PERMISSIONS = {
    "read": [
        # TODO: 필요한 AWS 권한
    ],
}


@dataclass
class {Resource}Info:
    account_id: str
    account_name: str
    region: str
    id: str
    name: str


@dataclass
class {Resource}AnalysisResult:
    account_id: str
    account_name: str
    region: str
    total_count: int = 0
    findings: list = field(default_factory=list)


def collect_{resources}(session, account_id: str, account_name: str, region: str) -> list[{Resource}Info]:
    """리소스 수집"""
    from botocore.exceptions import ClientError

    client = get_client(session, "{aws_service}", region_name=region)
    resources = []

    try:
        # TODO: AWS API 호출
        pass
    except ClientError:
        pass

    return resources


def analyze_{resources}(resources, account_id, account_name, region) -> {Resource}AnalysisResult:
    """리소스 분석"""
    # TODO: 분석 로직
    return {Resource}AnalysisResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_count=len(resources),
    )


def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """병렬 실행용"""
    resources = collect_{resources}(session, account_id, account_name, region)
    if not resources:
        return None
    return analyze_{resources}(resources, account_id, account_name, region)


def run(ctx) -> None:
    """{tool_name}"""
    from core.shared.io.compat import generate_reports

    console.print("[bold]분석 시작...[/bold]\n")

    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="{aws_service}")
    results = [r for r in result.get_data() if r is not None]

    if not results:
        console.print("[yellow]분석 결과 없음[/yellow]")
        return

    total = sum(r.total_count for r in results)
    console.print(f"전체: {total}개")

    # HTML용 flat 데이터 준비
    flat_data = [
        {
            "account_id": r.account_id,
            "account_name": r.account_name,
            "region": r.region,
            # TODO: 리소스별 필드 추가
        }
        for r in results
    ]

    # 보고서 경로 - 형식: output/{identifier}/{service}/{type}/{date}/
    identifier = ctx.accounts[0].id if ctx.accounts else ctx.profile_name or "default"
    output_path = OutputPath(identifier).sub("{service}", "{type}").with_date().build()

    # Excel + HTML 동시 생성 (ctx.output_config에 따라)
    report_paths = generate_reports(
        ctx,
        data=flat_data,
        excel_generator=lambda d: _save_excel(results, d),  # TODO: Excel 생성 함수 구현
        html_config={
            "title": "{tool_name}",
            "service": "{Service}",
            "tool_name": "{type}",
            "total": total,
            "found": len(flat_data),
        },
        output_dir=output_path,
    )

    console.print("\n[bold green]완료![/bold green]")
    for fmt, path in report_paths.items():
        console.print(f"  {fmt.upper()}: {path}")
```

---

## Output 경로 설정

```python
from core.shared.io.output import OutputPath, open_in_explorer

# 경로 형식: output/{identifier}/{service}/{type}/{date}/
output_path = OutputPath(identifier).sub("{service}", "{type}").with_date().build()

# 예시:
# output/123456789012/ec2/unused/2025-01-06/
# output/my-profile/vpc/security/2025-01-06/
```

---

## Core 유틸리티 참조

```python
# 필수
from core.parallel import get_client, parallel_collect
from core.shared.io.output import OutputPath, open_in_explorer

# 리포트 출력 (Excel + HTML 동시 생성)
from core.shared.io.compat import generate_reports

# 선택 (출력 설정)
from core.shared.io.compat import OutputConfig, OutputFormat

# 선택 (Quiet 모드)
from core.parallel import is_quiet

# 선택 (타입 상수)
from core.shared.io.output import ReportType, ToolType

# 선택 (Excel 유틸리티)
from core.shared.io.excel import Workbook, ColumnDef, Styles

# 선택 (HTML 유틸리티)
from core.shared.io.html import AWSReport, ResourceItem, create_aws_report
```

---

## 서브타입이 있는 서비스 (ELB, RDS 등)

AWS 서비스 중 여러 하위 타입이 있는 경우:

### 파일명 프리픽스 패턴

```
plugins/elb/
├── __init__.py
├── common.py           # 공통 유틸리티
├── alb_unused.py       # ALB 미사용 (module: "alb_unused")
├── alb_security.py     # ALB 보안 (module: "alb_security")
├── nlb_unused.py       # NLB 미사용 (module: "nlb_unused")
└── clb_unused.py       # CLB 미사용 (module: "clb_unused")
```

### TOOLS 배열 예시

```python
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
    # module = 파일명 (프리픽스 포함), area = 타입
]
```

### 서브타입 도구 추가 시

1. 파일명: `{subtype}_{type}.py` (예: `alb_security.py`)
2. module: 파일명과 동일 (예: `"alb_security"`)
3. area: 타입명 (예: `"security"`)

### 적용 대상 서비스

| 서비스 | 서브타입 | 파일명 프리픽스 |
|--------|----------|-----------------|
| `elb` | ALB, NLB, GWLB, CLB | `alb_`, `nlb_`, `gwlb_`, `clb_` |
| `elasticache` | Redis, Memcached | `redis_`, `memcached_` |
| `mq` | RabbitMQ, ActiveMQ | `rabbitmq_`, `activemq_` |
| `fsx` | Windows, Lustre, ONTAP, OpenZFS | `windows_`, `lustre_`, `ontap_`, `openzfs_` |

---

## 검증 체크리스트

### 추가 전 확인
- [ ] 서비스 폴더 존재: `plugins/{service}/` 확인
- [ ] 타입 분류 완료 (ReportType/ToolType 중 선택)
- [ ] 기존 타입 파일 존재 여부 확인

### 추가 후 확인
- [ ] `plugins/{service}/__init__.py` - TOOLS 배열 업데이트
- [ ] 새 파일/함수에 `run(ctx)` 또는 분석 함수 존재
- [ ] 린트 통과: `ruff check plugins/{service}/{type}.py`
- [ ] 타입 체크: `mypy plugins/{service}/{type}.py`

### 테스트 (선택)
- [ ] 기존 테스트 파일 업데이트 또는 `/make-test` 실행
- [ ] `pytest tests/plugins/{service}/ -v` 통과

---

## 참조

### 코드 참조
- 기존 도구 확인: `plugins/{service}/` 폴더의 다른 `.py` 파일들
- 타입 정의: `shared/io/output/report_types.py`
- Excel + HTML 통합: `plugins/ec2/unused.py` (참고 구현)

### Skills 참조
- `.claude/skills/output-patterns/SKILL.md` - 리포트 출력 패턴
- `.claude/skills/parallel-execution-patterns/SKILL.md` - 병렬 처리 패턴
- `.claude/skills/error-handling-patterns/SKILL.md` - 에러 핸들링 패턴
- `.claude/skills/aws-boto3-patterns/SKILL.md` - AWS boto3 패턴

---

## 예시

### 예시 1: 새 타입 추가

**입력:**
```
/add-plugin-tool ec2에 보안 그룹 감사 도구 추가
```

**분석:**
- service: `ec2`
- tool_name: `보안 그룹 감사`
- type: `security` (보안 관련)

**결과:**
1. `plugins/ec2/__init__.py` 수정 - TOOLS에 항목 추가
2. `plugins/ec2/security.py` 생성 (새 파일)

### 예시 2: 기존 타입 확장

**입력:**
```
/add-plugin-tool ec2에 AMI 미사용 분석 추가
```

**분석:**
- service: `ec2`
- tool_name: `AMI 미사용 분석`
- type: `unused` (미사용 관련)
- 기존 `plugins/ec2/unused.py` 존재!

**결과:**
1. `plugins/ec2/unused.py` 수정 - `analyze_ami()` 함수 추가
2. `run()` 함수에 AMI 분석 통합
