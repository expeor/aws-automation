# AWS Automation (aa)

AWS 운영 자동화 CLI 도구. 미사용 리소스 탐지, 보안 점검, 비용 분석, IAM 감사 등 65개+ 도구 제공.

## Progressive Disclosure

> 상세 정보는 필요할 때만 로드하여 토큰 사용량을 줄입니다.

| 정보 | 위치 | 갱신 방법 |
|------|------|----------|
| 플러그인 목록 및 도구 | `.claude/project-index.md` | `/sync-index` |
| Core API 요약 | `.claude/project-index.md` | `/sync-index` |
| 최근 변경 파일 | `.claude/project-index.md` | `/sync-index` |
| 코딩 스타일 가이드 | 아래 참조 | - |
| 플러그인 작성 패턴 | 아래 참조 | - |

**프로젝트 탐색 시**: `.claude/project-index.md`를 먼저 확인하세요.

## 아키텍처

```
aws-automation/
├── core/               # CLI 인프라 전체 (통합)
│   ├── auth/           # 인증
│   ├── parallel/       # 병렬 처리
│   ├── tools/          # 도구 관리
│   ├── region/         # 리전
│   ├── cli/            # Click CLI, 플로우, UI, i18n
│   ├── shared/         # 공유 유틸리티 (AWS, I/O)
│   └── scripts/        # 개발 도구
├── functions/          # 기능 모듈
│   ├── analyzers/      # AWS 서비스별 분석 도구 (30개 카테고리)
│   └── reports/        # 종합 리포트 (cost_dashboard, inventory, ip_search, log_analyzer)
└── tests/              # pytest 테스트
```

### 주요 디렉토리

- **core/**: CLI 인프라 전체 (인증, 병렬 처리, 도구 관리, CLI, 공유 유틸리티)
  - **core/cli/**: 메인 앱 진입점 (`app.py`), 플로우 관리, 프롬프트, 국제화(i18n)
  - **core/shared/**: 공유 유틸리티 (AWS: metrics, pricing, inventory, ip_ranges / I/O: excel, html, csv)
- **functions/analyzers/**: 서비스별 분석 도구 (ec2, vpc, lambda, iam, cost 등)
- **functions/reports/**: 종합 리포트 (비용 대시보드, 인벤토리, IP 검색, 로그 분석)

### Core 모듈 구조

```
core/
├── auth/           # 인증 (SSO Session, SSO Profile, Static)
├── parallel/       # 병렬 실행 (Map-Reduce, Rate Limiting, Quotas)
│   ├── executor.py       # ParallelSessionExecutor, parallel_collect
│   ├── rate_limiter.py   # Token Bucket Rate Limiting
│   └── quotas.py         # Service Quotas 확인
├── tools/          # 도구 관리, 캐시, 히스토리
│   ├── discovery.py      # 플러그인/리포트 발견
│   ├── history/          # 사용 기록, 즐겨찾기
│   └── cache/            # 캐시 관리
├── region/         # 리전 데이터 및 가용성 확인
│   ├── data.py           # ALL_REGIONS, REGION_NAMES
│   └── availability.py   # 리전 가용성 확인
├── cli/            # Click 기반 CLI
│   ├── app.py            # 메인 엔트리포인트
│   ├── headless.py       # 비대화형 모드
│   ├── flow/             # 플로우 관리
│   ├── ui/               # 터미널 UI
│   └── i18n/             # 국제화
├── shared/         # 공유 유틸리티
│   ├── aws/              # AWS (metrics, pricing, inventory, ip_ranges, health)
│   └── io/               # I/O (excel, html, csv, output)
├── scripts/        # 개발 도구
│   └── generate_index.py # 프로젝트 인덱스 생성
└── filter.py       # 리전 필터링
```

### Reports 모듈 구조

종합 리포트는 `functions/reports/`에 위치:

```
functions/reports/
├── cost_dashboard/             # 미사용 리소스 종합 대시보드
├── inventory/                  # AWS 리소스 인벤토리
├── ip_search/                  # IP 검색 (Public/Private)
└── log_analyzer/               # ALB/NLB 로그 분석
```

## 코딩 스타일

### Ruff 설정 (pyproject.toml)
```toml
[tool.ruff]
line-length = 120
target-version = "py310"
exclude = [".git", "__pycache__", "build", "dist", ".eggs", "output", "temp"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Mypy 설정
```toml
[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
warn_redundant_casts = true
warn_unused_configs = true
no_implicit_optional = true
```

### 스타일 규칙

- 최대 줄 길이: 120자 (ruff format으로 관리)
- Import 정렬: isort 스타일 (ruff I 규칙)
- 한글 docstring 허용
- 타입 힌트: Python 3.10+ 스타일 (`list[str]` not `List[str]`)
- Python 지원 버전: 3.10, 3.11, 3.12, 3.13, 3.14

## 플러그인 작성 패턴

> **⚠️ 멀티 계정 지원 필수**: 모든 도구는 `parallel_collect` 패턴을 사용해야 합니다.
> `get_context_session()` 직접 호출은 SSO Session 멀티 계정 선택 시 오류 발생.

### 기본 구조

플러그인은 `functions/analyzers/{service}/` 디렉토리에 위치하며, `__init__.py`와 도구 모듈로 구성:

```python
# functions/analyzers/{service}/__init__.py
CATEGORY = {
    "name": "{service}",
    "display_name": "{Service}",
    "description": "서비스 설명 (한글)",
    "description_en": "Service description (English)",
    "aliases": [],  # 별칭 목록 (검색용)
}

TOOLS = [
    {
        "name": "도구 이름 (한글)",
        "name_en": "Tool Name (English)",
        "description": "도구 설명 (한글)",
        "description_en": "Tool description (English)",
        "permission": "read",  # read, write
        "module": "{module_name}",  # 파일명 (.py 제외)
        "area": "{area}",  # 아래 area 종류 참조
    },
]
```

### Area 종류

| Area | 설명 | 예시 |
|------|------|------|
| `unused` | 미사용/유휴 리소스 탐지 | EC2, EBS, Lambda |
| `cost` | 비용 분석/최적화 | Reserved Instance, Savings Plan |
| `inventory` | 리소스 인벤토리/현황 | Lambda 종합 분석, Backup 현황 |
| `security` | 보안 감사/점검 | IAM, CloudTrail, Security Group |
| `search` | 리소스 검색 | CloudFormation 스택, KMS 키 |
| `log` | 로그 분석 | ALB 액세스 로그 |
| `tag` | 태그 관리 | Tag Editor |
| `sync` | 리소스 동기화 | Route 53 레코드 |

### 도구 모듈 패턴

```python
# functions/analyzers/{service}/{module}.py
from core.parallel import parallel_collect, get_client

def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """병렬 실행 콜백 (단일 계정/리전)"""
    client = get_client(session, "service-name", region_name=region)
    # ... 분석 로직
    return results

def run(ctx) -> None:
    """도구 실행 함수 (필수)"""
    result = parallel_collect(ctx, _collect_and_analyze, service="{aws_service}")
    data = result.get_flat_data()

    # 에러 처리
    if result.error_count > 0:
        print(result.get_error_summary())

    # 보고서 생성
    from core.shared.io.compat import generate_reports
    generate_reports(ctx, data, columns=[...])
```

### 병렬 처리 (core.parallel)

```python
from core.parallel import (
    parallel_collect,       # 간편한 병렬 수집
    get_client,             # Rate limiting 적용 클라이언트
    safe_aws_call,          # 재시도 + Rate limiting 데코레이터
    quiet_mode,             # 로그 출력 억제
    ErrorCollector,         # 에러 수집/분류
    # Service Quotas 확인
    get_quota_checker,      # 쿼터 체커 싱글톤
    QuotaStatus,            # 쿼터 상태 (OK, WARNING, CRITICAL, EXCEEDED)
)

# 기본 사용
result = parallel_collect(ctx, callback_func, service="ec2", max_workers=20)

# Progress tracking
from core.cli.ui import parallel_progress
with parallel_progress("수집 중") as tracker:
    with quiet_mode():
        result = parallel_collect(ctx, callback_func, progress_tracker=tracker)

# 데코레이터
@safe_aws_call(service="ec2", operation="describe_instances")
def get_instances(session, region):
    ec2 = session.client("ec2", region_name=region)
    return ec2.describe_instances()["Reservations"]

# 쿼터 확인
checker = get_quota_checker(session, "ap-northeast-2")
quota = checker.get_quota("ec2", "Running On-Demand")
if quota and quota.usage_percent > 80:
    print(f"경고: {quota.quota_name} 사용률 {quota.usage_percent:.1f}%")
```

### 리전 가용성 확인 (core.region)

```python
from core.region import (
    get_available_regions,      # 사용 가능한 리전 조회
    filter_available_regions,   # 리전 필터링
    validate_regions,           # 리전 검증
    RegionAvailabilityChecker,  # 상세 제어
)

# 사용 가능한 리전 조회
available = get_available_regions(session)

# 요청 리전 검증
available, unavailable = validate_regions(session, ["ap-northeast-2", "me-south-1"])
for region, reason in unavailable:
    print(f"{region}: {reason}")  # me-south-1: 옵트인 필요
```

### 태그 정책 검증 (core.tools)

```python
from core.tools import (
    TagPolicyValidator,
    TagPolicy,
    TagRule,
    create_basic_policy,
    create_cost_allocation_policy,
)

# 정책 생성
policy = create_basic_policy(required_tags=["Environment", "Owner"])

# 검증
validator = TagPolicyValidator(policy)
result = validator.validate({"Environment": "prod"})
if not result.is_valid:
    print(result.get_summary())  # 누락된 필수 태그: Owner
```

### 파일 출력 (core.shared.io)

```python
# Excel 출력
from core.shared.io.excel import Workbook, ColumnDef

wb = Workbook()
columns = [
    ColumnDef("리소스", width=30),
    ColumnDef("상태", width=15, style="center"),
    ColumnDef("수량", width=10, style="number"),
]
sheet = wb.new_sheet("Results", columns)
for row in data:
    sheet.add_row([row["resource"], row["status"], row["count"]])
wb.save("output.xlsx")

# HTML 보고서 (ECharts 시각화)
from core.shared.io.html import AWSReport, create_aws_report

report = create_aws_report(
    title="EC2 미사용",
    service="EC2",
    tool_name="unused",
    ctx=ctx,
    resources=results,
)
report.save("output.html")

# 듀얼 출력 (Excel + HTML)
from core.shared.io.compat import generate_reports

generate_reports(ctx, data, columns=[...], charts=[...])
```

## AWS 관련 주의사항

### 인증

- SSO Session, SSO Profile, Static Credentials 지원
- `ctx.provider.get_session(region=region)` 사용 권장
- 멀티 계정: Organization 또는 Profile 그룹 지원

### API 호출

- Paginator 사용 필수 (대량 리소스)
- `botocore.exceptions` 에러 핸들링
- Rate limit: `get_client()` 사용 시 자동 Rate limiting 적용

### 보안

- AWS 자격 증명 하드코딩 금지
- 사용자 입력 검증 (account_id, region 형식)
- 민감 정보 로깅 금지

## 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 특정 모듈
pytest tests/core/ -v
pytest tests/functions/analyzers/ec2/ -v

# 커버리지
pytest tests/ --cov=core --cov=functions
```

### 테스트 구조
```
tests/
├── cli/            # CLI 테스트
├── core/           # Core 모듈 테스트
│   ├── auth/       # 인증 테스트
│   ├── parallel/   # 병렬 처리 테스트
│   └── tools/      # 도구 테스트
└── functions/
    ├── analyzers/  # 플러그인 테스트
    └── reports/    # 리포트 테스트
```

### Mocking

- `moto` 라이브러리로 AWS 서비스 모킹
- `@mock_aws` 데코레이터 사용

## 린트/포맷

```bash
# 린트 체크
ruff check core functions

# 자동 수정
ruff check --fix core functions

# 포맷팅
ruff format core functions

# 타입 체크
mypy core functions

# 보안 스캔
bandit -r core functions -c pyproject.toml
```

## 실행 명령

```bash
# 대화형 메뉴
aa

# 특정 서비스
aa ec2
aa vpc

# 비대화형 모드 (도구 직접 실행)
aa ec2/ebs_audit -p my-profile -r ap-northeast-2

# 다중 리전
aa ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

# 전체 리전
aa ec2/ebs_audit -p my-profile -r all

# 출력 형식 지정
aa ec2/ebs_audit -p my-profile -f json -o result.json

# IP 검색
aa ip 10.0.1.50

# 도구 목록
aa tools              # 기본
aa tools -c ec2       # 카테고리 필터
aa list-tools         # 별칭 (호환성)

# 프로파일 그룹 관리
aa group
```

### 비대화형 모드 옵션

| 옵션 | 설명 |
|------|------|
| `-p, --profile` | SSO Profile 또는 Access Key 프로파일 (필수) |
| `-r, --region` | 리전 또는 리전 패턴 (기본: ap-northeast-2) |
| `-f, --format` | 출력 형식: console, json, csv |
| `-o, --output` | 출력 파일 경로 |
| `-q, --quiet` | 최소 출력 모드 |

## Git 워크플로우

### Branch Protection Rules

- **master 브랜치 직접 push 금지**: GitHub branch protection rule로 master에 직접 push 불가
- 모든 변경은 PR(Pull Request)을 통해 진행
- 커밋 후 push 시 항상 feature 브랜치 사용

### 권장 워크플로우

1. Feature 브랜치 생성: `git checkout -b feature/기능명` 또는 `refactor/설명`
2. 변경사항 커밋
3. Feature 브랜치 push: `git push -u origin 브랜치명`
4. PR 생성: `gh pr create`
5. 리뷰 후 merge

### 브랜치 네이밍

| Prefix | 용도 | 예시 |
|--------|------|------|
| `feature/` | 새 기능 | `feature/elasticache-plugin` |
| `fix/` | 버그 수정 | `fix/sso-token-refresh` |
| `refactor/` | 리팩토링 | `refactor/parallel-executor` |
| `docs/` | 문서 | `docs/api-guide` |
| `chore/` | 설정/의존성 | `chore/update-deps` |

## Contributing

기여 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요:

- 개발 환경 설정
- 코드 스타일 (ruff, mypy)
- 커밋 컨벤션 (Conventional Commits)
- 브랜치 네이밍
- PR 프로세스

## 디펜던시

### Runtime
- **boto3/botocore**: AWS SDK
- **click**: CLI 프레임워크
- **rich**: 터미널 UI
- **questionary**: 대화형 프롬프트
- **openpyxl**: Excel 출력
- **duckdb**: 대용량 로그 분석 (ALB 로그 등)
- **msgpack**: 바이너리 직렬화 (캐시)
- **chardet**: 파일 인코딩 감지
- **requests**: HTTP 클라이언트
- **pytz**: 타임존 처리
- **filelock**: 파일 잠금
- **cryptography**: 암호화

### Development
- **pytest**: 테스트 프레임워크
- **moto**: AWS 모킹
- **ruff**: 린터/포매터
- **mypy**: 타입 체커
- **bandit**: 보안 스캐너

## 버전 관리

Semantic Versioning (MAJOR.MINOR.PATCH) 사용:

```bash
# 현재 버전 확인
cat version.txt

# 버전 파일
version.txt      # 현재 버전
CHANGELOG.md     # 변경 이력
```

### 버전 업데이트 규칙

| Commit Type | 버전 변경 |
|-------------|----------|
| `feat` | MINOR ↑ (0.1.1 → 0.2.0) |
| `fix`, `refactor` | PATCH ↑ (0.1.1 → 0.1.2) |
| `feat!`, `BREAKING CHANGE` | MAJOR ↑ (0.1.1 → 1.0.0) |

### 업데이트 절차

1. version.txt 수정
2. CHANGELOG.md 업데이트
3. `chore: bump version to x.x.x` 커밋

## Bandit 예외 규칙

```toml
[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101", "B311", "B608"]
# B101: assert (테스트에서 사용)
# B311: random (보안 목적 아님)
# B608: DuckDB 쿼리 (내부 AWS 데이터, 사용자 입력 아님)
```

## Coverage 설정

```toml
[tool.coverage.run]
source = ["core", "functions"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```
