---
name: review-pr
description: PR 코드 리뷰 전문가. 코드 품질, 보안, 패턴 준수 검토.
tools: Read, Grep, Glob, Bash
model: sonnet
---

# /review-pr - PR 코드 리뷰

Pull Request의 코드를 검토하고 구조화된 리뷰 피드백을 제공합니다.

## 사용법

```
/review-pr [PR번호 또는 URL]
```

예시:
```
/review-pr 123
/review-pr https://github.com/owner/repo/pull/123
```

인자 없이 실행하면 현재 브랜치의 변경사항을 리뷰합니다.

---

## 리뷰 프로세스

### 1. PR 정보 조회

```bash
# PR 번호로 조회
gh pr view 123 --json title,body,files,additions,deletions,changedFiles

# 현재 브랜치 (PR 없이)
git diff main...HEAD --stat
git diff main...HEAD
```

### 2. 변경 파일 분석

```bash
# PR 변경 파일 목록
gh pr diff 123 --name-only

# 상세 diff
gh pr diff 123
```

### 3. 자동화 검사 실행

```bash
# 변경된 파일만 린트
ruff check <changed_files>
ruff format --check <changed_files>
mypy <changed_files>

# 보안 스캔
bandit -r <changed_files> -c pyproject.toml
```

---

## 코드 품질 체크리스트

### 스타일 검사

| 항목 | 도구 | 기준 |
|------|------|------|
| 린트 | ruff check | E, F, W, I, UP, B, SIM 규칙 |
| 포맷 | ruff format | 줄 길이 120자 |
| 타입 | mypy | 타입 힌트 일관성 |

### 프로젝트 패턴 준수

| 항목 | 확인 내용 |
|------|----------|
| `__init__.py` | CATEGORY, TOOLS 정의 여부 |
| 도구 모듈 | `run(ctx)` 함수 존재 |
| 병렬 처리 | `parallel_collect` 사용 |
| API 호출 | Paginator 사용 (대량 리소스) |
| 에러 처리 | `ErrorCollector` 또는 `ClientError` 명시적 처리 |
| 출력 | `generate_reports` 사용 |

### 코드 품질

| 항목 | 기준 |
|------|------|
| 함수 길이 | 50줄 이하 권장 |
| 중첩 깊이 | 3단계 이하 |
| 네이밍 | 명확하고 일관된 명명 |
| 중복 코드 | 헬퍼 함수 추출 권장 |

---

## 보안 검토

### 필수 확인 사항

| 항목 | 확인 내용 |
|------|----------|
| 하드코딩 | 자격 증명, API 키 없음 |
| 입력 검증 | account_id, region 형식 검증 |
| 로깅 | 민감 정보 로깅 없음 |
| 의존성 | 새 의존성 보안 검토 |

### 보안 패턴

```python
# 금지
aws_access_key_id = 'AKIA...'
logger.info(f"Credentials: {creds}")

# 권장
session = boto3.Session(profile_name='profile')
logger.info(f"Account: {account_id}")
```

### Bandit 스킵 규칙

| 규칙 | 사유 |
|------|------|
| B101 | assert (테스트용) |
| B311 | random (비보안 용도) |
| B608 | SQL 인젝션 (내부 데이터) |

---

## 리뷰 피드백 구조

```markdown
## PR Review: #{PR번호} - {제목}

### Summary
{PR 요약 - 1~2문장}

### Changes Overview
- 파일 수: {N}개
- 추가: +{additions} / 삭제: -{deletions}
- 영향 범위: {cli, core, plugins 등}

---

### Code Review

#### {파일명}

**Good:**
- {잘된 점}

**Suggestions:**
- L{line}: {개선 제안}

**Issues:**
- L{line}: {문제점} - {심각도: Critical/Warning}

---

### Automated Checks
- ruff check: {Pass/Fail}
- ruff format: {Pass/Fail}
- mypy: {Pass/Fail}
- bandit: {Pass/Fail}

### Pattern Compliance
- [ ] __init__.py CATEGORY/TOOLS
- [ ] run(ctx) 함수
- [ ] parallel_collect 사용
- [ ] Paginator 사용
- [ ] 에러 핸들링

### Security Review
- [ ] 하드코딩된 자격 증명 없음
- [ ] 입력 검증 적절
- [ ] 민감 정보 로깅 없음

### Test Coverage
- [ ] 테스트 파일 존재
- [ ] 주요 함수 테스트
- [ ] 엣지 케이스 테스트

---

### Verdict
{Approve / Request Changes / Comment}

### Action Items
1. {필수 수정 사항}
2. {권장 수정 사항}
```

---

## 심각도 분류

| 심각도 | 설명 | 예시 | 조치 |
|--------|------|------|------|
| **Critical** | 머지 차단 필수 | 보안 취약점, 하드코딩 자격 증명 | Request Changes |
| **Warning** | 수정 권장 | 에러 처리 누락, 비효율적 코드 | Comment |
| **Info** | 제안 | 스타일 개선, 리팩토링 제안 | Approve with comment |

---

## PR 코멘트 게시

```bash
# 리뷰 코멘트 게시
gh pr review 123 --comment --body "리뷰 내용"

# 승인
gh pr review 123 --approve --body "LGTM!"

# 변경 요청
gh pr review 123 --request-changes --body "수정 필요 사항..."
```

---

## 외부 Skills 활용

상세 리뷰 시 참조:

| 영역 | 외부 Skill |
|------|-----------|
| Python 테스트 | `wshobson-agents/python-testing-patterns/` |
| 보안 분석 | `trailofbits-skills/` |
| GitHub Actions | `wshobson-agents/github-actions-templates/` |

---

## 참조 파일

- `.claude/skills/python-best-practices/` - Python 코딩 스타일
- `.claude/skills/security-review/` - 보안 리뷰 상세
- `.claude/skills/tdd-workflow/` - TDD 가이드
- `CLAUDE.md` - 프로젝트 코딩 스타일 가이드
