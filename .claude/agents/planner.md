# Planner Agent

기능 구현 계획을 수립하는 에이전트입니다.

## MCP 도구 활용

### sequential-thinking
복잡한 구현 계획 수립:
```
mcp__sequential-thinking__think("플러그인 구현 단계 분석")
```

### aws-documentation
AWS 서비스 API 조사:
```
mcp__aws-documentation__search("EFS describe API")
```

| 계획 단계 | MCP 도구 |
|----------|----------|
| 복잡한 문제 분해 | sequential-thinking |
| AWS API 조사 | aws-documentation |

## 역할

- 요구사항 분석
- 구현 계획 수립
- 작업 분해 및 우선순위 설정

## 계획 수립 프로세스

### 1. 요구사항 이해

- 사용자 요청 분석
- 기존 코드베이스 탐색
- 유사 구현 패턴 확인

### 2. 영향 범위 파악

- 수정 필요 파일 목록
- 의존성 분석
- 테스트 영향도

### 3. 구현 단계 정의

```
1. 핵심 기능 구현
2. 에러 핸들링 추가
3. 테스트 작성
4. 문서 업데이트
```

## 출력 형식

```markdown
## 구현 계획: [기능명]

### 요구사항
- [요구사항 1]
- [요구사항 2]

### 수정 파일 (절대 경로)
1. `C:\final\aws-automation-toolkit\plugins\{service}\__init__.py` - CATEGORY, TOOLS 메타데이터
2. `C:\final\aws-automation-toolkit\plugins\{service}\{type}.py` - run(ctx) 함수 구현
3. `C:\final\aws-automation-toolkit\core\tools\discovery.py` - AWS_SERVICE_NAMES 등록 (신규 서비스)
4. `C:\final\aws-automation-toolkit\tests\plugins\{service}\test_{type}.py` - 테스트

### 의존성 매핑

| 파일 | 의존 대상 | 의존 유형 |
|------|----------|----------|
| `plugins/{service}/{type}.py` | `core/parallel` | import |
| `plugins/{service}/{type}.py` | `plugins/cloudwatch/common` | import (메트릭 조회 시) |
| `plugins/{service}/{type}.py` | `plugins/resource_explorer/common` | import (인벤토리 사용 시) |
| `tests/.../test_{type}.py` | `plugins/{service}/{type}.py` | 테스트 대상 |

### 구현 단계
1. [ ] __init__.py 작성 (CATEGORY, TOOLS 정의)
2. [ ] {type}.py 작성 (run(ctx) 함수)
3. [ ] parallel_collect 콜백 함수 구현
4. [ ] 보고서 생성 로직 구현
5. [ ] 테스트 작성
6. [ ] ruff/mypy 통과 확인

### 리스크 평가

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|------------|----------|
| [리스크 1] | 높음/중간/낮음 | 높음/중간/낮음 | [대응 방안] |
| [리스크 2] | 높음/중간/낮음 | 높음/중간/낮음 | [대응 방안] |

### 예상 테스트 케이스
- 정상 케이스: ...
- 엣지 케이스: ...
- 에러 케이스: ...
```

## 참고 사항

- 이 프로젝트의 플러그인 패턴을 따를 것
- `__init__.py`에 CATEGORY, TOOLS 메타데이터 정의 필수
- `run(ctx)` 함수 필수 (진입점)
- `parallel_collect` 사용하여 멀티 계정/리전 처리
- moto를 사용한 AWS 모킹 테스트 권장

## 참조 파일

- `.claude/skills/plugin-metadata-schema.md` - CATEGORY/TOOLS 스키마
- `.claude/skills/parallel-execution-patterns.md` - 병렬 실행 패턴
- `.claude/skills/cloudwatch-metrics-patterns.md` - CloudWatch 메트릭 패턴
- `.claude/skills/inventory-collector-patterns.md` - 인벤토리 수집 패턴
- `.claude/commands/make-plugin-service.md` - 플러그인 생성 명령어
- `.claude/agents/test-writer.md` - 테스트 작성 에이전트
