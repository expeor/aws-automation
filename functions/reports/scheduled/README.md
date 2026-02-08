# Scheduled Operations (정기 작업 관리)

거버넌스에 맞게 일간/월간/분기/반기/연간 **정기 작업**을 관리하고 실행하는 시스템입니다.

## 빠른 시작

```bash
# 대화형 메뉴에서 'd' 키로 접근
aa
> d  # 정기 작업 메뉴

# CLI로 직접 실행 (예정)
aa scheduled --cycle 3M
aa scheduled --id 3M-001
```

## 작업 유형

| 유형 | permission | 설명 | 색상 |
|------|-----------|------|------|
| 점검 | `read` | 현황 파악, 보고서 생성 | 🟢 녹색 |
| 적용 | `write` | 설정 변경, 태그 적용 | 🟡 노란색 |
| 정리 | `delete` | 리소스 삭제, 정리 | 🔴 빨간색 |

## 작업 주기

| 코드 | 주기 | 아이콘 | 예시 |
|------|------|--------|------|
| `D` | 일간 | 🕕 | Health 이벤트 확인 |
| `W` | 주간 | 📅 | 주간 리소스 점검 |
| `1M` | 월간 | 📅 | 미사용 리소스 정리 |
| `3M` | 분기 | 📊 | IAM 보안 감사 |
| `6M` | 반기 | 📋 | Rightsizing 분석 |
| `12M` | 연간 | 📆 | 종합 보안 감사 |

---

## YAML 설정 가이드

### 파일 위치

```
reports/scheduled/config/
├── default.yaml      # 기본 설정 (필수)
├── production.yaml   # 프로덕션 환경 설정
├── staging.yaml      # 스테이징 환경 설정
├── sample.yaml       # 샘플 설정 (참고용)
└── ...
```

### 기본 구조

```yaml
# config/{config_name}.yaml
config_name: "설정 이름"
config_name_en: "Config Name"

cycles:
  D:                              # 주기 코드 (D, W, 1M, 3M, 6M, 12M)
    display_name: "일간 작업"
    display_name_en: "Daily Operations"
    color: "red"                  # Rich 색상 (red, yellow, blue, green, magenta, cyan)
    icon: "🕕"                    # 이모지 아이콘
    tasks:
      - id: "D-001"               # 고유 ID (주기-번호)
        name: "작업 이름"
        name_en: "Task Name"
        description: "작업 설명"
        description_en: "Task description"
        tool_ref: "category/module"  # 실행할 도구 참조
        permission: "read"        # read, write, delete
        supports_regions: true    # 멀티 리전 지원 여부
        requires_confirm: false   # 실행 전 확인 필요 (delete에 권장)
        enabled: true             # 활성화 여부
```

### 필드 상세 설명

#### 주기 (cycle) 설정

| 필드 | 필수 | 설명 |
|------|------|------|
| `display_name` | ✅ | 한글 표시명 |
| `display_name_en` | ❌ | 영문 표시명 (없으면 한글 사용) |
| `color` | ❌ | Rich 색상 (기본: dim) |
| `icon` | ❌ | 이모지 아이콘 (기본: 📄) |
| `tasks` | ✅ | 작업 목록 |

#### 작업 (task) 설정

| 필드 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `id` | ✅ | string | 고유 식별자 (예: "3M-001") |
| `name` | ✅ | string | 한글 이름 |
| `name_en` | ❌ | string | 영문 이름 |
| `description` | ❌ | string | 한글 설명 |
| `description_en` | ❌ | string | 영문 설명 |
| `tool_ref` | ✅ | string | 도구 참조 경로 |
| `permission` | ❌ | string | 권한 타입 (기본: "read") |
| `supports_regions` | ❌ | bool | 멀티 리전 지원 (기본: true) |
| `requires_confirm` | ❌ | bool | 실행 전 확인 (기본: false) |
| `requires_input` | ❌ | dict | 사용자 입력 필드 정의 |
| `enabled` | ❌ | bool | 활성화 여부 (기본: true) |

#### tool_ref 경로 규칙

`tool_ref`는 `analyzers/` 또는 `reports/` 하위 모듈을 참조합니다:

```yaml
# analyzers/{category}/{module}.py → run(ctx) 함수 실행
tool_ref: "ec2/ebs_audit"           # analyzers/ec2/ebs_audit.py
tool_ref: "iam/iam_audit"           # analyzers/iam/iam_audit.py
tool_ref: "tag_editor/map_apply"    # analyzers/tag_editor/map_apply.py

# reports/{category}/{module}.py
tool_ref: "cost_dashboard/orchestrator"  # reports/cost_dashboard/orchestrator.py
```

---

## 다중 설정 사용하기

### 1. 설정 프로필 파일 생성

```yaml
# config/production.yaml
config_name: "프로덕션 환경"
config_name_en: "Production"

cycles:
  D:
    display_name: "일간 점검"
    display_name_en: "Daily Check"
    color: "red"
    icon: "🔔"
    tasks:
      - id: "D-001"
        name: "서비스 Health 점검"
        name_en: "Service Health Check"
        description: "AWS Health Dashboard 이벤트 확인"
        description_en: "Check AWS Health Dashboard events"
        tool_ref: "health/analysis"
        permission: "read"
        supports_regions: false

  1M:
    display_name: "월간 거버넌스"
    display_name_en: "Monthly Governance"
    color: "yellow"
    icon: "📋"
    tasks:
      - id: "1M-001"
        name: "비용 최적화 점검"
        name_en: "Cost Optimization Review"
        description: "미사용 리소스 및 예약 인스턴스 분석"
        description_en: "Analyze unused resources and reserved instances"
        tool_ref: "cost_dashboard/orchestrator"
        permission: "read"
        supports_regions: true

      - id: "1M-002"
        name: "보안 그룹 감사"
        name_en: "Security Group Audit"
        description: "0.0.0.0/0 오픈 포트 점검"
        description_en: "Check for 0.0.0.0/0 open ports"
        tool_ref: "vpc/sg_audit"
        permission: "read"
        supports_regions: true
```

### 2. 설정 선택 방법

#### 방법 1: 환경변수 (권장)

```bash
# 환경변수로 설정 지정
export AA_SCHEDULED_CONFIG=production

# 실행
aa
> d  # production.yaml 설정 사용
```

#### 방법 2: 메뉴에서 선택

```bash
aa
> d     # 정기 작업 메뉴
> c     # 설정 변경 (c 키)
> 2     # 원하는 설정 선택
```

#### 방법 3: CLI 옵션 (예정)

```bash
# CLI에서 직접 지정
aa scheduled --config production
aa scheduled --config production --cycle 3M
```

### 3. 설정 우선순위

1. CLI 옵션 (`--config`)
2. 환경변수 (`AA_SCHEDULED_CONFIG`)
3. 기본값 (`default.yaml`)

---

## 커스터마이즈 예시

### 작업 비활성화

기본 설정의 특정 작업을 비활성화:

```yaml
# config/minimal.yaml
config_name: "최소 설정"
config_name_en: "Minimal Config"

cycles:
  3M:
    display_name: "분기 작업"
    display_name_en: "Quarterly Operations"
    color: "blue"
    icon: "📊"
    tasks:
      - id: "3M-001"
        name: "필수 태그 누락"
        name_en: "Required Tag Missing"
        tool_ref: "tag_editor/map_audit"
        permission: "read"
        enabled: true  # 활성화

      - id: "3M-004"
        name: "오래된 스냅샷 정리"
        name_en: "Old Snapshot Cleanup"
        tool_ref: "ec2/snapshot_cleanup"
        permission: "delete"
        enabled: false  # ❌ 비활성화
```

### 사용자 입력이 필요한 작업

```yaml
tasks:
  - id: "3M-005"
    name: "커스텀 태그 적용"
    name_en: "Custom Tag Apply"
    description: "지정한 태그를 리소스에 일괄 적용"
    description_en: "Bulk apply specified tags to resources"
    tool_ref: "tag_editor/bulk_apply"
    permission: "write"
    requires_input:
      tag_key:
        type: "text"
        label: "태그 키"
        label_en: "Tag Key"
        required: true
      tag_value:
        type: "text"
        label: "태그 값"
        label_en: "Tag Value"
        required: true
      resource_type:
        type: "select"
        label: "리소스 유형"
        label_en: "Resource Type"
        options:
          - "ec2"
          - "rds"
          - "lambda"
```

### 삭제 작업 (확인 필수)

```yaml
tasks:
  - id: "6M-003"
    name: "오래된 로그 그룹 정리"
    name_en: "Old Log Group Cleanup"
    description: "180일 이상 미사용 CloudWatch 로그 그룹 삭제"
    description_en: "Delete CloudWatch log groups unused for 180+ days"
    tool_ref: "cloudwatch/log_cleanup"
    permission: "delete"
    supports_regions: true
    requires_confirm: true  # ⚠️ 실행 전 확인 프롬프트
```

---

## 프로그래밍 API

```python
from reports.scheduled import (
    get_schedule_groups,
    get_all_tasks,
    get_tasks_by_permission,
    load_config,
)

# 특정 설정 로드
config = load_config(company="production")
print(config["config_name"])  # "프로덕션 환경"

# 주기별 그룹 조회
groups = get_schedule_groups(company="production", lang="ko")
for group in groups:
    print(f"{group.icon} {group.display_name}")
    print(f"  점검: {group.read_count}개")
    print(f"  적용: {group.write_count}개")
    print(f"  정리: {group.delete_count}개")

# 모든 작업 조회
tasks = get_all_tasks(company="production")
for task in tasks:
    print(f"[{task.id}] {task.name} ({task.permission})")

# 권한별 필터링
delete_tasks = get_tasks_by_permission("delete", company="production")
for task in delete_tasks:
    print(f"⚠️ {task.name}: {task.description}")
```

---

## 모범 사례

### 1. ID 네이밍 규칙

```
{주기}-{순번}[-{접미사}]

예시:
D-001      # 일간 작업 1번
3M-002     # 분기 작업 2번
3M-P01     # 분기 작업 프로덕션 전용 1번
6M-S03     # 반기 작업 스테이징 전용 3번
```

### 2. 권한 분류 기준

| 권한 | 사용 시점 | 예시 |
|------|----------|------|
| `read` | AWS 리소스 조회만 필요 | 인벤토리, 감사, 분석 |
| `write` | 리소스 생성/수정 필요 | 태그 적용, 설정 변경 |
| `delete` | 리소스 삭제 필요 | 스냅샷 정리, AMI 삭제 |

### 3. delete 작업 가이드라인

- 항상 `requires_confirm: true` 설정
- description에 삭제 기준 명시 (예: "90일 이상 미사용")
- 가능하면 dry-run 옵션 제공
- 삭제 전 백업/스냅샷 생성 권장

### 4. 설정 프로필 관리

```
config/
├── default.yaml        # 공통 기본 설정 (수정 최소화)
├── production.yaml     # 프로덕션 환경
├── staging.yaml        # 스테이징 환경
├── dev.yaml            # 개발 환경
└── sample.yaml         # 참고용 샘플
```

---

## 문제 해결

### Q: 작업이 표시되지 않아요

1. YAML 파일 경로 확인: `reports/scheduled/config/{config}.yaml`
2. `enabled: false`가 설정되어 있는지 확인
3. 주기 코드가 올바른지 확인 (D, W, 1M, 3M, 6M, 12M)

### Q: tool_ref 오류가 발생해요

```
ERROR - run 함수 없음: {module_path}
```

1. `tool_ref` 경로가 올바른지 확인
2. 해당 모듈에 `run(ctx)` 함수가 있는지 확인
3. 모듈 import 오류가 있는지 확인

### Q: 설정이 적용되지 않아요

1. 환경변수 확인: `echo $AA_SCHEDULED_CONFIG`
2. YAML 파일명이 정확한지 확인 (확장자 `.yaml`)
3. YAML 문법 오류 확인: `python -c "import yaml; yaml.safe_load(open('config/my.yaml'))"`

---

## 관련 문서

- [CLAUDE.md](../../CLAUDE.md) - 프로젝트 개발 가이드
- [core/tools/discovery.py](../../core/tools/discovery.py) - 도구 발견 시스템
- [cli/ui/main_menu.py](../../cli/ui/main_menu.py) - 메뉴 UI 구현
