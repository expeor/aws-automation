# Skills 인덱스

프로젝트 skill 파일 카탈로그입니다.

---

## 외부 Skills

### Python 개발 (wshobson-agents)

| Skill | 설명 | 용도 |
|-------|------|------|
| `python-testing-patterns` | pytest 테스트 패턴, 픽스처, 모킹 | 고급 테스트 작성 |
| `python-performance-optimization` | 프로파일링, 최적화 기법 | 성능 개선 |
| `async-python-patterns` | asyncio, 비동기 패턴 | 비동기 코드 |
| `python-packaging` | pyproject.toml, 배포 | 패키지 관리 |
| `uv-package-manager` | uv 패키지 매니저 | 빠른 의존성 관리 |

### CI/CD & Git (wshobson-agents)

| Skill | 설명 | 용도 |
|-------|------|------|
| `github-actions-templates` | GitHub Actions 워크플로우 | CI/CD 구성 |
| `git-advanced-workflows` | Git 고급 워크플로우 | 브랜치 전략 |
| `secrets-management` | 시크릿 관리 | 보안 설정 |

### TDD & 테스트 (obra-superpowers)

| Skill | 설명 | 용도 |
|-------|------|------|
| `test-driven-development` | TDD 철학, Red-Green-Refactor | TDD 원칙 |
| `verification-before-completion` | 완료 전 검증 | 품질 보증 |
| `systematic-debugging` | 체계적 디버깅 | 문제 해결 |
| `using-git-worktrees` | Git worktrees 활용 | 병렬 작업 |

### 보안 분석 (trailofbits-skills)

| Skill | 설명 | 용도 |
|-------|------|------|
| `property-based-testing` | 속성 기반 테스트 (Hypothesis) | 고급 테스트 |
| `audit-context-building` | 보안 감사 컨텍스트 구축 | 보안 분석 |
| `codeql` | CodeQL 정적 분석 | 취약점 탐지 |
| `coverage-analysis` | 커버리지 분석 | 테스트 품질 |

### 문서 & 리포트 (anthropics-skills)

| Skill | 설명 | 용도 |
|-------|------|------|
| `xlsx` | Excel 파일 생성/편집/분석 | 리포트 출력 |
| `pdf` | PDF 문서 처리 | 문서 생성 |
| `pptx` | PowerPoint 생성 | 프레젠테이션 |
| `docx` | Word 문서 처리 | 문서 생성 |

---

## 프로젝트 Skills

### AWS 패턴

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`aws-boto3-patterns`](./aws-boto3-patterns/) | boto3 사용 패턴 | 클라이언트, 세션, 페이지네이션 |
| [`cloudwatch-metrics-patterns.md`](./cloudwatch-metrics-patterns.md) | CloudWatch 배치 메트릭 | MetricQuery, batch_get_metrics |
| [`inventory-collector-patterns.md`](./inventory-collector-patterns.md) | 리소스 인벤토리 수집 | InventoryCollector, 50+ 리소스 타입 |
| [`plugin-metadata-schema.md`](./plugin-metadata-schema.md) | 플러그인 메타데이터 | CATEGORY, TOOLS, ReportType |

### Python 개발

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`python-best-practices`](./python-best-practices/) | Python 코딩 스타일 | ruff, mypy, 타입 힌트 |
| [`parallel-execution-patterns`](./parallel-execution-patterns/) | 병렬 실행 | parallel_collect, Rate Limiter |
| [`error-handling-patterns`](./error-handling-patterns/) | 에러 처리 | ErrorCollector, try_or_default |

### 출력 및 리포트

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`output-patterns`](./output-patterns/) | 리포트 생성 | Excel, HTML, generate_reports |
| [`cli-output-style.md`](./cli-output-style.md) | 콘솔 출력 스타일 | 심볼, 색상, Step 패턴 |

### 개발 워크플로우

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`tdd-workflow`](./tdd-workflow/) | TDD 가이드 | Red-Green-Refactor, moto |
| [`security-review`](./security-review/) | 보안 리뷰 | OWASP, 취약점 검사 |
| [`commit`](./commit/) | 커밋 자동화 | Conventional Commits |
| [`release`](./release/) | 릴리스 관리 | Semantic Versioning, CHANGELOG |
| [`migrate-tool`](./migrate-tool/) | 도구 마이그레이션 | 레거시 도구 업데이트 |

---

## 크로스 레퍼런스 매트릭스

| 작업 | 프로젝트 Skill | 외부 Skill |
|------|---------------|-----------|
| 새 플러그인 생성 | `plugin-metadata-schema.md` | - |
| CloudWatch 메트릭 | `cloudwatch-metrics-patterns.md` | - |
| 테스트 작성 | `tdd-workflow` | `python-testing-patterns`, `test-driven-development` |
| 보안 검토 | `security-review` | `property-based-testing`, `codeql` |
| 리포트 생성 | `output-patterns` | `xlsx` |
| GitHub Actions | - | `github-actions-templates` |
| 에러 처리 | `error-handling-patterns` | - |

---

## 빠른 참조

### 플러그인 개발 체크리스트

1. **메타데이터** → `plugin-metadata-schema.md`
2. **수집 로직** → `parallel-execution-patterns`
3. **CloudWatch** → `cloudwatch-metrics-patterns.md`
4. **인벤토리** → `inventory-collector-patterns.md`
5. **리포트** → `output-patterns`
6. **테스트** → `tdd-workflow` + `python-testing-patterns`

### 자주 사용하는 import

```python
# 병렬 처리
from core.parallel import parallel_collect, get_client, quiet_mode

# 에러 처리
from core.parallel.errors import ErrorCollector, ErrorSeverity, try_or_default

# CloudWatch 메트릭
from plugins.cloudwatch.common import batch_get_metrics, MetricQuery

# 인벤토리 수집
from plugins.resource_explorer.common import InventoryCollector

# 리포트 출력
from core.tools.io.compat import generate_reports
```

---

## 관련 Commands

| Command | 설명 | 관련 Skills |
|---------|------|-------------|
| `/make-plugin-service` | 새 플러그인 생성 | `plugin-metadata-schema.md` |
| `/add-plugin-tool` | 도구 추가 | `plugin-metadata-schema.md` |
| `/make-test` | 테스트 스캐폴딩 | `tdd-workflow` |
| `/lint` | 코드 품질 검사 | `python-best-practices` |
| `/coverage` | 테스트 커버리지 | `tdd-workflow` |
| `/sync-index` | 인덱스 갱신 | - |

---

## 관련 Agents

| Agent | 설명 | 관련 Skills |
|-------|------|-------------|
| `review-pr.md` | PR 리뷰 (통합) | 전체 |
| `planner.md` | 구현 계획 수립 | `plugin-metadata-schema.md` |
| `aws-expert.md` | AWS 전문가 | `aws-boto3-patterns` |
