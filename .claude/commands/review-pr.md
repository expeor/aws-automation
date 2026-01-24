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

## 실행 순서

### 1. PR 정보 조회

```bash
# PR 번호로 조회
gh pr view 123 --json title,body,files,additions,deletions,changedFiles

# 현재 브랜치 (PR 없이)
git diff main...HEAD --stat
git diff main...HEAD
```

### 2. 변경 파일 분석

PR에 포함된 파일 목록과 변경 내용 확인:

```bash
# PR 변경 파일 목록
gh pr diff 123 --name-only

# 상세 diff
gh pr diff 123
```

### 3. 코드 품질 체크리스트

#### 3.1 스타일 검사

```bash
# 변경된 파일만 린트
ruff check <changed_files>
ruff format --check <changed_files>
mypy <changed_files>
```

#### 3.2 프로젝트 패턴 준수

| 항목 | 확인 내용 |
|------|----------|
| `__init__.py` | CATEGORY, TOOLS 정의 여부 |
| 도구 모듈 | `run(ctx)` 함수 존재 |
| 병렬 처리 | `parallel_collect` 사용 |
| API 호출 | Paginator 사용 (대량 리소스) |
| 에러 처리 | `ClientError` 명시적 처리 |
| 출력 | `generate_reports` 사용 |

#### 3.3 보안 검토

| 항목 | 확인 내용 |
|------|----------|
| 하드코딩 | 자격 증명, API 키 없음 |
| 입력 검증 | account_id, region 형식 검증 |
| 로깅 | 민감 정보 로깅 없음 |
| 의존성 | 새 의존성 보안 검토 |

### 4. 리뷰 피드백 생성

#### 피드백 구조

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
- L{line}: {개선 제안}

**Issues:**
- L{line}: {문제점} - {심각도: Critical/Warning}

---

### Style Check
- ruff check: {Pass/Fail}
- ruff format: {Pass/Fail}
- mypy: {Pass/Fail}

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

## 심각도 분류

| 심각도 | 설명 | 예시 |
|--------|------|------|
| **Critical** | 머지 차단 필수 | 보안 취약점, 하드코딩 자격 증명 |
| **Warning** | 수정 권장 | 에러 처리 누락, 비효율적 코드 |
| **Info** | 제안 | 스타일 개선, 리팩토링 제안 |

## 예시 출력

```markdown
## PR Review: #45 - Add ElastiCache unused cluster detection

### Summary
ElastiCache 클러스터 미사용 탐지 플러그인 추가. CloudWatch 메트릭 기반 분석.

### Changes Overview
- 파일 수: 3개
- 추가: +285 / 삭제: -0
- 영향 범위: plugins/elasticache

---

### Code Review

#### plugins/elasticache/__init__.py

**Good:**
- CATEGORY, TOOLS 정의 완료
- 한글/영어 설명 모두 작성

#### plugins/elasticache/unused.py

**Good:**
- parallel_collect 사용
- Paginator 사용
- dataclass 활용

**Suggestions:**
- L45: `get_client()` 사용 권장 (Rate limiting 지원)
- L78-85: 반복되는 메트릭 조회 로직 → batch_get_metrics 활용 검토

**Issues:**
- L120: 빈 except 블록 - Warning

---

### Style Check
- ruff check: Pass
- ruff format: Pass
- mypy: Pass

### Pattern Compliance
- [x] __init__.py CATEGORY/TOOLS
- [x] run(ctx) 함수
- [x] parallel_collect 사용
- [x] Paginator 사용
- [ ] 에러 핸들링 - 개선 필요

### Security Review
- [x] 하드코딩된 자격 증명 없음
- [x] 입력 검증 적절
- [x] 민감 정보 로깅 없음

### Test Coverage
- [ ] 테스트 파일 없음 - 추가 필요

---

### Verdict
**Request Changes**

### Action Items
1. [필수] L120: 빈 except 블록에 ClientError 명시적 처리 추가
2. [필수] 테스트 파일 추가 (tests/plugins/elasticache/test_unused.py)
3. [권장] L45: session.client() → get_client() 변경
4. [권장] CloudWatch 메트릭 조회를 batch_get_metrics로 최적화
```

## PR 코멘트 게시

리뷰 완료 후 GitHub에 코멘트 게시 옵션:

```bash
# 리뷰 코멘트 게시
gh pr review 123 --comment --body "리뷰 내용"

# 승인
gh pr review 123 --approve --body "LGTM!"

# 변경 요청
gh pr review 123 --request-changes --body "수정 필요 사항..."
```

## 참조 파일

- `.claude/agents/code-reviewer.md` - 코드 리뷰 에이전트 상세
- `.claude/agents/security-reviewer.md` - 보안 리뷰 가이드
- `.claude/skills/python-best-practices.md` - Python 코딩 스타일
- `CLAUDE.md` - 프로젝트 코딩 스타일 가이드
