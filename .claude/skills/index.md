# Skills 인덱스

프로젝트 skill 파일 카탈로그입니다.

---

## 도메인별 분류

### AWS 패턴

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`aws-boto3-patterns.md`](./aws-boto3-patterns.md) | boto3 사용 패턴 | 클라이언트, 세션, 페이지네이션 |
| [`cloudwatch-metrics-patterns.md`](./cloudwatch-metrics-patterns.md) | CloudWatch 배치 메트릭 | MetricQuery, batch_get_metrics, 서비스별 빌더 |
| [`inventory-collector-patterns.md`](./inventory-collector-patterns.md) | 리소스 인벤토리 수집 | InventoryCollector, 50+ 리소스 타입 |
| [`plugin-metadata-schema.md`](./plugin-metadata-schema.md) | 플러그인 메타데이터 | CATEGORY, TOOLS, ReportType, ToolType |

### Python 개발

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`python-best-practices.md`](./python-best-practices.md) | Python 코딩 스타일 | ruff, mypy, 타입 힌트 |
| [`parallel-execution-patterns.md`](./parallel-execution-patterns.md) | 병렬 실행 | parallel_collect, Rate Limiter, Quotas |
| [`error-handling-patterns.md`](./error-handling-patterns.md) | 에러 처리 | ErrorCollector, try_or_default, ErrorSeverity |

### 출력 및 리포트

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`output-patterns.md`](./output-patterns.md) | 리포트 생성 | Excel, HTML, generate_reports |
| [`cli-output-style.md`](./cli-output-style.md) | 콘솔 출력 스타일 | 심볼, 색상, Step 패턴 |

### 개발 워크플로우

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`tdd-workflow.md`](./tdd-workflow.md) | TDD 가이드 | Red-Green-Refactor, 테스트 우선 |
| [`security-review.md`](./security-review.md) | 보안 리뷰 | OWASP, 취약점 검사 |
| [`commit-conventional.md`](./commit-conventional.md) | 커밋 컨벤션 | Conventional Commits, feat/fix/chore |
| [`versioning.md`](./versioning.md) | 버전 관리 | Semantic Versioning, CHANGELOG |

---

## 크로스 레퍼런스 매트릭스

| 작업 | 주요 Skill | 관련 Skills |
|------|-----------|-------------|
| 새 플러그인 생성 | `plugin-metadata-schema.md` | `parallel-execution-patterns.md`, `output-patterns.md` |
| CloudWatch 메트릭 조회 | `cloudwatch-metrics-patterns.md` | `aws-boto3-patterns.md`, `error-handling-patterns.md` |
| 인벤토리 기반 분석 | `inventory-collector-patterns.md` | `parallel-execution-patterns.md` |
| 테스트 작성 | `tdd-workflow.md` | `error-handling-patterns.md` |
| 리포트 생성 | `output-patterns.md` | `cli-output-style.md` |
| 에러 처리 구현 | `error-handling-patterns.md` | `parallel-execution-patterns.md` |
| 커밋 및 릴리스 | `commit-conventional.md` | `versioning.md` |

---

## 빠른 참조

### 플러그인 개발 체크리스트

1. **메타데이터** → `plugin-metadata-schema.md`
   - CATEGORY 스키마 확인
   - TOOLS 배열 정의
   - area (ReportType/ToolType) 선택

2. **수집 로직** → `parallel-execution-patterns.md`
   - `parallel_collect` 사용
   - 콜백 함수 정의
   - 에러 처리 추가

3. **CloudWatch 통합** (선택) → `cloudwatch-metrics-patterns.md`
   - 서비스별 쿼리 빌더 사용
   - `batch_get_metrics` 호출

4. **인벤토리 통합** (선택) → `inventory-collector-patterns.md`
   - `InventoryCollector` 사용
   - 다중 리소스 조합

5. **리포트 출력** → `output-patterns.md`
   - `generate_reports` 사용
   - Excel + HTML 동시 생성

6. **테스트** → `tdd-workflow.md`
   - moto 기반 AWS 모킹
   - 정상/엣지/에러 케이스

### 자주 사용하는 import

```python
# 병렬 처리
from core.parallel import parallel_collect, get_client, quiet_mode

# 에러 처리
from core.parallel.errors import ErrorCollector, ErrorSeverity, try_or_default

# CloudWatch 메트릭
from plugins.cloudwatch.common import (
    batch_get_metrics, MetricQuery, sanitize_metric_id,
    build_lambda_metric_queries, build_ec2_metric_queries,
)

# 인벤토리 수집
from plugins.resource_explorer.common import InventoryCollector

# 리포트 출력
from core.tools.io.compat import generate_reports
from core.tools.output import OutputPath
```

---

## 관련 Commands

| Command | 설명 | 관련 Skills |
|---------|------|-------------|
| `/make-plugin-service` | 새 플러그인 생성 | `plugin-metadata-schema.md`, `output-patterns.md` |
| `/add-plugin-tool` | 기존 서비스에 도구 추가 | `plugin-metadata-schema.md` |
| `/make-test` | 테스트 스캐폴딩 | `tdd-workflow.md` |
| `/lint` | 코드 품질 검사 | `python-best-practices.md` |
| `/coverage` | 테스트 커버리지 | `tdd-workflow.md` |
| `/release` | 릴리스 관리 | `versioning.md`, `commit-conventional.md` |

---

## 관련 Agents

| Agent | 설명 | 관련 Skills |
|-------|------|-------------|
| `planner.md` | 구현 계획 수립 | `plugin-metadata-schema.md`, `parallel-execution-patterns.md` |
| `test-writer.md` | 테스트 작성 | `tdd-workflow.md`, `cloudwatch-metrics-patterns.md` |
| `plugin-scaffolder.md` | 플러그인 스캐폴딩 | `plugin-metadata-schema.md`, `output-patterns.md` |
| `aws-expert.md` | AWS 전문가 | `aws-boto3-patterns.md`, `cloudwatch-metrics-patterns.md` |
