# AWS Automation (aa)

AWS 운영 자동화 CLI 도구. 미사용 리소스 탐지, 보안 점검, IAM 감사 등 40개+ 도구 제공.

## 아키텍처

```
aws-automation/
├── cli/            # Click 기반 CLI, 대화형 메뉴
├── core/           # 인증, 병렬처리, 도구 관리, Excel 출력
├── plugins/        # AWS 서비스별 분석 도구 (40개+)
└── tests/          # pytest 테스트
```

### 주요 디렉토리

- **cli/**: 메인 앱 진입점 (`app.py`), 플로우 관리, 프롬프트
- **core/**: 인증 프로바이더, 병렬 처리, 도구 레지스트리, Excel 출력
- **plugins/**: 서비스별 분석 도구 (ec2, vpc, lambda, iam 등)

## 코딩 스타일

### Ruff 설정 (pyproject.toml)
```toml
[tool.ruff]
line-length = 120
target-version = "py310"
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # Line length handled by formatter
```

### Mypy 설정
```toml
[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
```

### 스타일 규칙

- 최대 줄 길이: 120자 (ruff format으로 관리)
- Import 정렬: isort 스타일 (ruff I 규칙)
- 한글 docstring 허용
- 타입 힌트: Python 3.10+ 스타일 (`list[str]` not `List[str]`)

## 플러그인 작성 패턴

### 기본 구조

플러그인은 `plugins/{service}/` 디렉토리에 위치하며, `__init__.py`와 도구 모듈로 구성:

```python
# plugins/{service}/__init__.py
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
        "module": "{type}",    # 파일명 (unused, security, cost 등)
        "area": "{type}",      # unused, security, cost, operation
    },
]
```

### 도구 모듈

```python
# plugins/{service}/{type}.py
from core.parallel import parallel_collect

def run(ctx) -> None:
    """도구 실행 함수 (필수)"""
    result = parallel_collect(ctx, _collect_and_analyze, service="{aws_service}")
    # ... 결과 처리 및 보고서 생성
```

### 병렬 처리

멀티 계정/리전 병렬 실행:
```python
from core.parallel import get_client, parallel_collect

def _collect_and_analyze(session, account_id: str, account_name: str, region: str):
    """병렬 실행 콜백 (단일 계정/리전)"""
    client = get_client(session, "service-name", region_name=region)
    # ... 분석 로직

def run(ctx) -> None:
    result = parallel_collect(ctx, _collect_and_analyze, service="service-name")
    data = result.get_data()
```

## AWS 관련 주의사항

### 인증

- SSO Session, SSO Profile, Static Credentials 지원
- `ctx.provider.get_session(region=region)` 사용 권장
- 하위 호환: `self.get_session(region)` 메서드 사용 가능

### API 호출

- Paginator 사용 필수 (대량 리소스)
- `botocore.exceptions` 에러 핸들링
- Rate limit 고려 (병렬 처리 시)

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

# 커버리지
pytest tests/ --cov=core --cov=cli --cov=plugins
```

### Mocking

- `moto` 라이브러리로 AWS 서비스 모킹
- `@mock_aws` 데코레이터 사용

## 린트/포맷

```bash
# 린트 체크
ruff check cli core plugins

# 자동 수정
ruff check --fix cli core plugins

# 포맷팅
ruff format cli core plugins

# 타입 체크
mypy cli core plugins

# 보안 스캔
bandit -r cli core plugins -c pyproject.toml
```

## 실행 명령

```bash
# 대화형 메뉴
aa

# 특정 서비스
aa ec2
aa vpc

# Headless 모드
aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

# IP 검색
aa ip 10.0.1.50

# 도구 목록
aa list-tools
```

## 디펜던시

- **boto3/botocore**: AWS SDK
- **click**: CLI 프레임워크
- **rich**: 터미널 UI
- **questionary**: 대화형 프롬프트
- **openpyxl**: Excel 출력
- **duckdb**: 대용량 로그 분석 (ALB 로그 등)

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
skips = ["B101", "B311", "B608"]
# B101: assert (테스트에서 사용)
# B311: random (보안 목적 아님)
# B608: DuckDB 쿼리 (내부 AWS 데이터, 사용자 입력 아님)
```
