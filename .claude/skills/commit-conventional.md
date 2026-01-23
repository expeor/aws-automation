# Conventional Commits

커밋 메시지 작성 가이드입니다.

## 형식

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Type

| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새로운 기능 | 새 도구 추가, 기능 구현 |
| `fix` | 버그 수정 | 오류 수정, 예외 처리 |
| `refactor` | 리팩토링 | 코드 구조 개선 (기능 변경 없음) |
| `docs` | 문서 | README, docstring 수정 |
| `test` | 테스트 | 테스트 추가/수정 |
| `chore` | 기타 | 빌드, 의존성 업데이트 |
| `style` | 스타일 | 포맷팅, 세미콜론 등 |
| `perf` | 성능 | 성능 개선 |
| `ci` | CI/CD | GitHub Actions 등 |

## Scope

| Scope | 설명 |
|-------|------|
| `cli` | CLI 관련 |
| `core` | Core 모듈 |
| `plugins` | 플러그인 |
| `tests` | 테스트 |
| `deps` | 의존성 |
| 서비스명 | 특정 서비스 (ec2, vpc, iam 등) |

## 예시

### 기능 추가
```
feat(plugins): add elasticache unused cluster detection
```

### 버그 수정
```
fix(core): handle SSO token expiration gracefully
```

### 리팩토링
```
refactor(cli): simplify menu navigation logic
```

### 문서
```
docs: update README with new CLI options
```

### 테스트
```
test(ec2): add moto tests for EBS audit
```

### 의존성
```
chore(deps): upgrade boto3 to 1.35.0
```

### Breaking Change
```
feat(cli)!: change run command arguments

BREAKING CHANGE: -p flag now requires profile name instead of index
```

## 한글/영문

영문 권장, 한글 허용:

```
# 영문 (권장)
feat(plugins): add RDS snapshot audit tool

# 한글 (허용)
feat(plugins): RDS 스냅샷 감사 도구 추가
```

## 커밋 단위

- 하나의 논리적 변경 = 하나의 커밋
- 너무 크지 않게 (리뷰 가능한 크기)
- 관련 없는 변경은 분리

### Good
```
feat(ec2): add EBS snapshot age analysis
test(ec2): add tests for snapshot analysis
docs: update plugin development guide
```

### Avoid
```
feat: add many features and fix bugs  # 너무 포괄적
```

## 버전 연동

Conventional Commits → Semantic Versioning 자동 매핑:

| Commit Type | 버전 변경 | 예시 (0.1.1 기준) |
|-------------|----------|------------------|
| `feat` | MINOR ↑ | → 0.2.0 |
| `fix` | PATCH ↑ | → 0.1.2 |
| `refactor` | PATCH ↑ | → 0.1.2 |
| `feat!` / `BREAKING CHANGE` | MAJOR ↑ | → 1.0.0 |
| `docs`, `test`, `chore` | 변경 없음 | - |

### 버전 업데이트 포함 커밋

```bash
# 1. 기능 구현 커밋
git commit -m "feat(plugins): add elasticache unused detection"

# 2. 버전 업데이트 커밋 (별도)
# version.txt: 0.1.1 → 0.2.0
# CHANGELOG.md 업데이트
git commit -m "chore: bump version to 0.2.0"
```

## 커밋 메시지 체크

PR 전 확인:
- [ ] type이 적절한가?
- [ ] scope가 명확한가?
- [ ] description이 변경 내용을 설명하는가?
- [ ] Breaking Change가 있으면 표시했는가?
- [ ] 버전 업데이트 필요 여부 확인 (feat/fix 시)
