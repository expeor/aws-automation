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

### 텍스트 품질 (humanizer)

| Skill | 설명 | 용도 |
|-------|------|------|
| `humanizer` | AI 생성 영문 텍스트 패턴 감지/수정 (24개 패턴) | README, CHANGELOG, description_en |

### UI/UX 디자인 (ui-ux-pro-max)

| Skill | 설명 | 용도 |
|-------|------|------|
| `ui-ux-pro-max` | 50개 스타일, 21개 팔레트, 차트 가이드라인 | HTML 리포트 시각 품질 개선 |

### 스킬 관리 (find-skills)

| Skill | 설명 | 용도 |
|-------|------|------|
| `find-skills` | 스킬 검색/설치/업데이트 (`npx skills`) | 스킬 인프라 관리 |

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
| [`error-handling-patterns`](./error-handling-patterns/) | 에러 처리 | ErrorCollector, @safe_aws_call, try_or_default |

### 출력 및 리포트

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`output-patterns`](./output-patterns/) | 리포트 생성 | Excel, HTML, generate_dual_report |
| [`cli-output-style.md`](./cli-output-style.md) | 콘솔 출력 스타일 | 심볼, 색상, Step 패턴 |

### 아키텍처 가이드

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`analyzers-vs-reports.md`](./analyzers-vs-reports.md) | analyzers/ vs reports/ 경계 | 단일 서비스 vs 종합 오케스트레이션 |
| [`debugging-troubleshooting.md`](./debugging-troubleshooting.md) | 디버깅/트러블슈팅 | moto, conftest, 병렬 실행 디버깅 |

### 텍스트 품질

| Skill | 설명 | 주요 내용 |
|-------|------|----------|
| [`korean-humanizer`](./korean-humanizer/) | 한국어 AI 작문 패턴 제거 | 12개 한국어 패턴, 도구 설명/CHANGELOG/docstring |

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
| 새 플러그인 생성 | `plugin-metadata-schema.md`, `analyzers-vs-reports.md` | - |
| CloudWatch 메트릭 | `cloudwatch-metrics-patterns.md` | - |
| 테스트 작성 | `tdd-workflow`, `debugging-troubleshooting.md` | `python-testing-patterns`, `test-driven-development` |
| 보안 검토 | `security-review` | `property-based-testing`, `codeql` |
| 리포트 생성 | `output-patterns` | `xlsx`, `ui-ux-pro-max` |
| HTML 리포트 디자인 | `output-patterns` | `ui-ux-pro-max` |
| GitHub Actions | - | `github-actions-templates` |
| 에러 처리 | `error-handling-patterns` | - |
| 디버깅 | `debugging-troubleshooting.md` | `systematic-debugging` |
| 영문 텍스트 품질 | - | `humanizer` |
| 한국어 텍스트 품질 | `korean-humanizer` | - |
| 스킬 검색/설치 | - | `find-skills` |

---

## 빠른 참조

### 플러그인 개발 체크리스트

1. **위치 결정** → `analyzers-vs-reports.md` (단일 서비스: analyzers/, 종합: reports/)
2. **메타데이터** → `plugin-metadata-schema.md`
3. **수집 로직** → `parallel-execution-patterns`
4. **CloudWatch** → `cloudwatch-metrics-patterns.md`
5. **인벤토리** → `inventory-collector-patterns.md`
6. **에러 처리** → `error-handling-patterns` (@safe_aws_call, ErrorCollector)
7. **리포트** → `output-patterns` (generate_dual_report + create_output_path)
8. **테스트** → `tdd-workflow` + `debugging-troubleshooting.md`

### 자주 사용하는 import

```python
# 병렬 처리
from core.parallel import parallel_collect, get_client, quiet_mode

# 에러 처리
from core.parallel.errors import ErrorCollector, ErrorSeverity, try_or_default
from core.parallel.decorators import safe_aws_call, RetryConfig

# CloudWatch 메트릭
from shared.aws.metrics import batch_get_metrics, MetricQuery

# 인벤토리 수집
from shared.aws.inventory import InventoryCollector

# 리포트 출력
from shared.io.compat import generate_dual_report
from shared.io.output.helpers import create_output_path
from shared.io.output import print_report_complete, open_in_explorer
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
| `/review` | 2단계 리뷰 (스펙 + 품질) | `commit`, `security-review` |
| `/sync-index` | 인덱스 갱신 | - |

---

## 관련 Agents

| Agent | 설명 | 관련 Skills |
|-------|------|-------------|
| `review-pr.md` | PR 리뷰 (통합) | 전체 |
| `planner.md` | 구현 계획 수립 | `plugin-metadata-schema.md` |
| `aws-expert.md` | AWS 전문가 | `aws-boto3-patterns` |
