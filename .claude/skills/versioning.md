# 버전 관리 가이드

version.txt와 CHANGELOG.md 자동 관리 가이드입니다.

## Semantic Versioning (SemVer)

```
MAJOR.MINOR.PATCH
```

| 버전 | 변경 시점 | 예시 |
|------|----------|------|
| MAJOR | Breaking changes, API 변경 | 0.x → 1.0.0 |
| MINOR | 새 기능 추가 (하위 호환) | 0.1.x → 0.2.0 |
| PATCH | 버그 수정, 리팩토링 | 0.1.1 → 0.1.2 |

## Conventional Commits → 버전 매핑

| Commit Type | 버전 영향 | 예시 |
|-------------|----------|------|
| `feat` | MINOR ↑ | 새 플러그인 추가 |
| `fix` | PATCH ↑ | 버그 수정 |
| `refactor` | PATCH ↑ | 코드 개선 |
| `docs` | - | 문서만 변경 |
| `test` | - | 테스트만 변경 |
| `chore` | - | 빌드/설정 변경 |
| `feat!` / `BREAKING CHANGE` | MAJOR ↑ | API 변경 |

## 버전 업데이트 절차

### 1. version.txt 수정

```bash
# 현재 버전 확인
cat version.txt  # 0.1.1

# 버전 업데이트
echo "0.1.2" > version.txt
```

### 2. CHANGELOG.md 업데이트

```markdown
## [0.1.2] - 2026-01-23

### Added
- 새로운 기능 설명

### Changed
- 변경된 기능 설명

### Fixed
- 수정된 버그 설명

### Removed
- 제거된 기능 설명
```

### 3. 커밋 & 태그

```bash
git add version.txt CHANGELOG.md
git commit -m "chore: bump version to 0.1.2"
git tag v0.1.2
git push origin main --tags
```

## CHANGELOG 섹션

| 섹션 | 용도 |
|------|------|
| Added | 새로운 기능 |
| Changed | 기존 기능 변경 |
| Deprecated | 곧 제거될 기능 |
| Removed | 제거된 기능 |
| Fixed | 버그 수정 |
| Security | 보안 취약점 수정 |

## 버전 업데이트 체크리스트

코드 변경 후:

- [ ] 변경 유형 확인 (feat/fix/refactor)
- [ ] 버전 번호 결정 (MAJOR/MINOR/PATCH)
- [ ] version.txt 업데이트
- [ ] CHANGELOG.md 업데이트
- [ ] 커밋 메시지에 버전 포함
- [ ] Git 태그 생성 (릴리스 시)

## 자동화 규칙

Claude Code가 코드를 수정할 때:

1. **feat 커밋 시**: MINOR 버전 증가 제안
2. **fix/refactor 커밋 시**: PATCH 버전 증가 제안
3. **Breaking Change 시**: MAJOR 버전 증가 필수

### 버전 증가 예시

```python
# 현재: 0.1.1

# feat 추가 → 0.2.0
# fix 수정 → 0.1.2
# feat! (breaking) → 1.0.0
```

## Pre-release 버전

개발 중인 버전:

```
0.2.0-alpha.1
0.2.0-beta.1
0.2.0-rc.1
```

## 참고

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
