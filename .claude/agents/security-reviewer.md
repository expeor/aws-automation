# Security Reviewer Agent

> **통합됨**: 이 기능은 `/review-pr`에 통합되었습니다.
> 상세 내용: `.claude/agents/review-pr.md`

## 빠른 참조

### 보안 스캔

```bash
bandit -r cli core plugins -c pyproject.toml
safety check
pip-audit
```

### 보안 체크리스트

- [ ] 하드코딩된 자격 증명 없음
- [ ] 입력 검증 (account_id, region, ARN)
- [ ] 민감 정보 로깅 없음
- [ ] 경로 순회 공격 방지

### Bandit 스킵 규칙

| 규칙 | 사유 |
|------|------|
| B101 | assert (테스트용) |
| B311 | random (비보안 용도) |
| B608 | SQL 인젝션 (내부 데이터) |

### 참조

- `.claude/agents/review-pr.md` - 전체 PR 리뷰 프로세스
- `.claude/skills/security-review/` - 보안 리뷰 상세 가이드
- `trailofbits-skills/` - 고급 보안 분석 도구
