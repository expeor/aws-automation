# functions/analyzers/ vs functions/reports/ 경계 가이드

코드를 어디에 배치할지 결정하는 기준입니다.

## 결정 트리

```
새 도구 만들기
  ├── 단일 AWS 서비스? → functions/analyzers/{service}/
  │   예: EC2 미사용, RDS 유휴, Lambda 런타임
  │
  └── 여러 서비스 취합/오케스트레이션? → functions/reports/
      예: 미사용 리소스 종합, 리소스 인벤토리, IP 검색
```

## analyzers/ 디렉토리

**단일 서비스 분석 도구**. 각 서비스별 폴더에 위치.

```
functions/analyzers/
├── ec2/             # EC2 관련 도구들
│   ├── __init__.py  # CATEGORY + TOOLS 메타데이터
│   ├── unused.py    # 미사용 인스턴스
│   ├── ebs_audit.py # EBS 감사
│   └── ...
├── rds/
│   ├── __init__.py
│   └── unused.py    # RDS 유휴 분석
├── fn/              # Lambda
│   ├── __init__.py
│   ├── comprehensive.py
│   └── runtime_deprecated.py
└── vpc/
    ├── __init__.py
    ├── nat_audit.py
    └── nat_audit_analysis/  # 복잡한 도구의 하위 모듈
        ├── __init__.py
        ├── analyzer.py
        ├── collector.py
        └── reporter.py
```

### CATEGORY 등록

```python
# functions/analyzers/{service}/__init__.py
CATEGORY = {
    "name": "ec2",
    "display_name": "EC2",
    "description": "EC2 인스턴스 관리",
    "description_en": "EC2 Instance Management",
    "aliases": ["instance"],
}

TOOLS = [
    {
        "name": "미사용 인스턴스",
        "name_en": "Unused Instances",
        "description": "미사용 EC2 인스턴스 탐지",
        "description_en": "Detect unused EC2 instances",
        "permission": "read",
        "module": "unused",      # functions/analyzers/{service}/unused.py
        "area": "unused",
    },
]
```

### 도구 모듈 규약

```python
# functions/analyzers/{service}/{tool}.py
def run(ctx: ExecutionContext) -> None:
    """필수 진입점"""
    ...
```

## functions/reports/ 디렉토리

**여러 서비스를 취합하는 종합 리포트**.

```
functions/reports/
├── __init__.py              # CATEGORY + TOOLS (ref 필드 사용)
├── cost_dashboard/          # 미사용 리소스 종합
│   ├── orchestrator.py      # 여러 analyzer 도구 호출
│   ├── collectors.py        # 공통 수집 로직
│   └── report.py            # 종합 리포트 생성
├── inventory/               # 리소스 인벤토리
├── ip_search/               # IP 검색
└── log_analyzer/            # 로그 분석
```

### functions/reports/__init__.py의 ref 필드

reports는 `module` 대신 `ref` 필드를 사용:

```python
# functions/reports/__init__.py
TOOLS = [
    {
        "name": "미사용 리소스 종합",
        "name_en": "Unused Resources Dashboard",
        "permission": "read",
        "ref": "cost_dashboard/orchestrator",  # functions/reports/ 하위 경로
        "area": "cost",
    },
]
```

### 특수 플래그

```python
{
    "is_menu": True,           # 하위 메뉴 표시 (CategoryStep 특별 처리)
    "require_session": False,  # AWS 세션 불필요
    "single_region_only": True, # 단일 리전만 지원
}
```

## 오케스트레이터 패턴

`functions/reports/cost_dashboard/orchestrator.py` 참조:

```python
def run(ctx) -> None:
    """종합 리포트: 여러 서비스 분석 결과를 취합"""
    # 1. 개별 서비스별 수집
    nat_results = _collect_nat(ctx)
    ebs_results = _collect_ebs(ctx)
    eip_results = _collect_eip(ctx)

    # 2. 결과 취합
    combined = merge_results(nat_results, ebs_results, eip_results)

    # 3. 종합 리포트 생성
    generate_dashboard(ctx, combined)
```

## 하위 모듈 패턴 (analyzers)

복잡한 도구는 하위 디렉토리로 분리:

```
analyzers/vpc/
├── nat_audit.py                  # run() 진입점
└── nat_audit_analysis/           # 하위 모듈
    ├── __init__.py               # 공개 API export
    ├── collector.py              # NATCollector
    ├── analyzer.py               # NATAnalyzer
    └── reporter.py               # NATExcelReporter
```

```python
# nat_audit_analysis/__init__.py
from .analyzer import NATAnalyzer
from .collector import NATCollector
from .reporter import NATExcelReporter

__all__ = ["NATCollector", "NATAnalyzer", "NATExcelReporter"]
```

## 참조

- `functions/analyzers/rds/unused.py` - 간단한 단일 서비스 도구
- `functions/analyzers/fn/comprehensive.py` - 복잡한 단일 서비스 도구
- `functions/analyzers/vpc/nat_audit.py` - 하위 모듈 패턴
- `functions/reports/cost_dashboard/orchestrator.py` - 오케스트레이터 패턴
- `functions/reports/__init__.py` - ref 필드 및 특수 플래그 예시
