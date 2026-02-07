---
name: review
description: 2단계 리뷰 (스펙 준수 → 코드 품질). 커밋/PR 전 자동 리뷰 수행.
---

# /review - 2-Stage Pre-Commit Review

커밋 또는 PR 생성 전에 2단계 자동 리뷰를 수행합니다.
obra/superpowers의 2-stage review 패턴을 이 프로젝트에 맞게 적응했습니다.

## 사용법

```
/review              # 현재 변경사항 리뷰
/review --staged     # 스테이지된 변경사항만 리뷰
/review --spec SPEC  # 특정 요구사항 파일 기준 리뷰
```

## 리뷰 프로세스

### Stage 1: 스펙 준수 리뷰 (Spec Compliance)

**목적:** 구현이 요구사항을 충족하는지 확인

#### 실행 순서

1. 변경사항 수집

```bash
# 변경된 파일 목록
git diff --name-only HEAD

# 스테이지된 변경
git diff --cached --stat

# 상세 diff
git diff HEAD
```

2. 요구사항 대비 점검

변경사항이 속한 영역에 따라 다른 체크리스트 적용:

**플러그인 (analyzers/) 변경 시:**

| 체크 항목 | 확인 방법 |
|-----------|----------|
| `__init__.py`에 CATEGORY, TOOLS 정의 | Grep으로 확인 |
| `run(ctx)` 진입점 함수 존재 | Grep으로 확인 |
| `parallel_collect` 사용 | Grep으로 확인 (멀티 계정 필수) |
| 보고서 생성 로직 포함 | `generate_reports` 또는 `HTMLReport` 사용 확인 |
| 에러 처리 존재 | `ErrorCollector`, `ClientError`, `try/except` 확인 |

**Core (core/) 변경 시:**

| 체크 항목 | 확인 방법 |
|-----------|----------|
| 하위 호환성 유지 | 기존 import 경로가 작동하는지 확인 |
| 테스트 존재 | `tests/core/` 미러 구조에 테스트 파일 확인 |
| TYPE_CHECKING 가드 사용 | 순환 참조 방지 확인 |

**CLI (cli/) 변경 시:**

| 체크 항목 | 확인 방법 |
|-----------|----------|
| i18n 키 추가 | 새 문자열에 대한 번역 키 확인 |
| 기존 명령어 호환 | --help 출력 확인 |

3. 스펙 준수 판정

```
✅ 스펙 준수: 모든 요구사항 충족
❌ 스펙 미준수: [미충족 항목 나열]
```

**Stage 1이 ❌면 Stage 2로 진행하지 않음.** 먼저 스펙 이슈를 수정.

---

### Stage 2: 코드 품질 리뷰 (Code Quality)

**목적:** 구현 품질이 프로젝트 기준을 충족하는지 확인

#### 자동 도구 실행

```bash
# 린트
ruff check <changed_files>

# 포맷
ruff format --check <changed_files>

# 타입 체크
mypy <changed_files> --ignore-missing-imports

# 보안 스캔
bandit -r <changed_files> -c pyproject.toml

# 테스트 실행 (관련 테스트만)
pytest <related_test_files> -v --tb=short
```

#### 수동 코드 리뷰

| 항목 | 기준 |
|------|------|
| 함수 길이 | 50줄 이하 권장 |
| 중첩 깊이 | 3단계 이하 |
| 중복 코드 | 같은 로직 2회 이상 반복 시 헬퍼 추출 권장 |
| 네이밍 | 기존 패턴과 일관성 |
| Import | `from __future__ import annotations` 포함 |
| 보안 | 하드코딩된 자격 증명, 민감 정보 로깅 없음 |

#### 품질 판정

```
✅ 품질 통과: 모든 검사 통과
⚠️ 경고: [개선 권장 사항] (커밋 가능하나 개선 권장)
❌ 품질 미달: [수정 필수 사항]
```

---

## 출력 형식

```markdown
## Review: [변경 요약]

### Stage 1: 스펙 준수 [✅/❌]

**변경 파일:** N개
**영향 범위:** {analyzers, core, cli, shared, tests}

| 체크 항목 | 상태 | 비고 |
|-----------|------|------|
| parallel_collect 사용 | ✅ | |
| CATEGORY/TOOLS 정의 | ✅ | |
| run(ctx) 함수 | ✅ | |
| 보고서 생성 | ❌ | generate_reports 누락 |

### Stage 2: 코드 품질 [✅/⚠️/❌]

**자동 검사:**
- ruff check: ✅ Pass (0 issues)
- ruff format: ✅ Pass
- mypy: ⚠️ 2 warnings
- bandit: ✅ Pass
- pytest: ✅ 15/15 pass

**수동 리뷰:**
- [파일명:행번호] [Suggestion] 설명
- [파일명:행번호] [Issue] 설명

### 종합 판정: [✅ Approve / ⚠️ Approve with Comments / ❌ Request Changes]

### 조치 사항
1. [필수] ...
2. [권장] ...
```

---

## /commit 연계

`/review`를 먼저 실행하고 통과하면 `/commit` 실행을 권장:

```
1. /review          # 리뷰 수행
2. (이슈 수정)      # 발견된 이슈 수정
3. /review          # 재리뷰 (선택)
4. /commit          # 커밋 실행
```

---

## 참조

- `.claude/skills/obra-superpowers/skills/subagent-driven-development/SKILL.md` - 2-stage review 원본
- `.claude/skills/obra-superpowers/skills/verification-before-completion/SKILL.md` - 검증 원칙
- `.claude/agents/review-pr.md` - PR 레벨 리뷰 (GitHub 연동)
- `.claude/skills/commit/SKILL.md` - 커밋 자동화
