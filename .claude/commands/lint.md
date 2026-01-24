# /lint - 코드 품질 검사

ruff, mypy, bandit을 실행하여 코드 품질을 종합 검사합니다.

## 사용법

```
/lint [path]
```

예시:
```
/lint                    # 전체 프로젝트 검사
/lint cli                # cli 디렉토리만 검사
/lint plugins/ec2        # 특정 플러그인 검사
```

## 실행 순서

### 1. 대상 경로 확인

`$ARGUMENTS`에서 경로 추출:
- 경로 미지정: `cli core plugins` (전체)
- 경로 지정: 해당 경로만 검사

### 2. Ruff Linter 실행

```bash
# 린트 검사 (자동 수정 포함)
ruff check --fix <path>
```

검사 항목 (`pyproject.toml` 설정):
- `E`: pycodestyle 에러
- `F`: pyflakes
- `W`: pycodestyle 경고
- `I`: isort (import 정렬)
- `UP`: pyupgrade (Python 버전 업그레이드)
- `B`: flake8-bugbear
- `SIM`: flake8-simplify

### 3. Ruff Formatter 실행

```bash
# 코드 포맷팅
ruff format <path>
```

포맷 설정:
- 줄 길이: 120자
- 따옴표: 쌍따옴표 (`"`)
- 들여쓰기: 스페이스

### 4. Mypy 타입 체크 실행

```bash
mypy <path>
```

타입 체크 설정 (`pyproject.toml`):
- Python 버전: 3.10
- 누락 import 무시: `ignore_missing_imports = true`
- 암시적 Optional 금지: `no_implicit_optional = true`

### 5. Bandit 보안 스캔 실행

```bash
bandit -r <path> -c pyproject.toml
```

보안 검사 설정:
- `tests` 디렉토리 제외
- 건너뛰는 규칙:
  - `B101`: assert (테스트용)
  - `B311`: random (보안 목적 아님)
  - `B608`: SQL 주입 (DuckDB 내부 쿼리)

### 6. 결과 요약

모든 검사 결과를 요약하여 출력:

```
/lint 실행 결과

[Ruff Lint]
  ✓ 에러 없음
  - 자동 수정: 3개

[Ruff Format]
  ✓ 포맷팅 완료

[Mypy]
  ✓ 타입 에러 없음

[Bandit]
  ✓ 보안 취약점 없음

전체 결과: ✓ 모든 검사 통과
```

에러 발생 시:

```
/lint 실행 결과

[Ruff Lint]
  ✗ 에러 2개 발견
  - plugins/ec2/unused.py:45: F401 imported but unused
  - plugins/ec2/unused.py:78: E501 line too long

[Mypy]
  ✗ 타입 에러 1개
  - core/parallel/executor.py:120: error: Incompatible types

[Bandit]
  ✓ 보안 취약점 없음

전체 결과: ✗ 실패 (Ruff: 2, Mypy: 1)
```

## 검사별 상세 옵션

### Ruff 검사만

```bash
ruff check cli core plugins
```

### Ruff 자동 수정 없이

```bash
ruff check --no-fix cli core plugins
```

### Mypy 상세 출력

```bash
mypy --show-error-codes --pretty cli core plugins
```

### Bandit 상세 출력

```bash
bandit -r cli core plugins -c pyproject.toml -v
```

## 참조 파일

- `pyproject.toml` - ruff, mypy, bandit 설정
- `.claude/skills/python-best-practices.md` - 코딩 스타일 가이드

## 주의사항

1. **가상환경 활성화**: 도구가 설치되어 있어야 함
2. **자동 수정**: ruff check --fix는 파일을 수정함
3. **Git 상태 확인**: 수정 전 uncommitted changes 확인 권장
4. **CI 연동**: GitHub Actions에서 동일 검사 실행
