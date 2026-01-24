# Code Reviewer Agent

> **통합됨**: 이 기능은 `/review-pr`에 통합되었습니다.
> 상세 내용: `.claude/agents/review-pr.md`

## 빠른 참조

### 코드 품질 검사

```bash
ruff check cli core plugins
ruff format --check cli core plugins
mypy cli core plugins
```

### 프로젝트 패턴 체크리스트

- [ ] `__init__.py`에 CATEGORY, TOOLS 정의
- [ ] `run(ctx)` 함수 구현
- [ ] `parallel_collect` 사용
- [ ] Paginator 사용 (대량 리소스)
- [ ] `ErrorCollector` 에러 핸들링

### 참조

- `.claude/agents/review-pr.md` - 전체 PR 리뷰 프로세스
- `.claude/skills/python-best-practices/` - Python 스타일 가이드
