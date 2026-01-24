# /coverage - 테스트 커버리지 분석

pytest-cov를 사용하여 테스트 커버리지를 측정하고 리포트를 생성합니다.

## 사용법

```
/coverage [path] [options]
```

예시:
```
/coverage                      # 전체 커버리지 측정
/coverage tests/core           # 특정 테스트만 실행
/coverage --html               # HTML 리포트 생성
/coverage --min 80             # 최소 80% 커버리지 요구
```

## 실행 순서

### 1. 테스트 실행 및 커버리지 측정

```bash
pytest tests/ --cov=core --cov=cli --cov=plugins --cov-report=term-missing
```

커버리지 대상 (`pyproject.toml` 설정):
- `cli/`
- `core/`
- `plugins/`

제외 항목:
- `*/tests/*`
- `*/__pycache__/*`

### 2. 결과 출력

#### 터미널 요약

```
/coverage 실행 결과

테스트 결과: 45 passed, 2 skipped in 12.34s

커버리지 요약
─────────────────────────────────────────────────
Name                              Stmts   Miss  Cover
──────────────────────────────────────────────────────
cli/app.py                          120     15    88%
cli/flow.py                          85     10    88%
core/parallel/executor.py           150     25    83%
core/parallel/rate_limiter.py        60      5    92%
core/tools/io/excel/workbook.py     200     30    85%
plugins/ec2/unused.py               100     12    88%
──────────────────────────────────────────────────────
TOTAL                              1500    200    87%
```

#### 미커버 라인 하이라이트

```
core/parallel/executor.py:45-52, 78-85, 120-125
  - 45-52: except 블록 (에러 처리)
  - 78-85: 타임아웃 처리
  - 120-125: 재시도 로직
```

### 3. HTML 리포트 생성 (선택)

`--html` 옵션 사용 시:

```bash
pytest tests/ --cov=core --cov=cli --cov=plugins --cov-report=html
```

리포트 위치: `htmlcov/index.html`

```
HTML 리포트 생성 완료
  위치: htmlcov/index.html
  브라우저에서 열기: open htmlcov/index.html
```

### 4. 최소 커버리지 확인 (선택)

`--min` 옵션 사용 시:

```bash
pytest tests/ --cov=core --cov=cli --cov=plugins --cov-fail-under=80
```

```
# 통과
✓ 커버리지 87% (최소 요구: 80%)

# 실패
✗ 커버리지 75% (최소 요구: 80%)
  - 5% 추가 필요
```

## 모듈별 상세 분석

### 특정 모듈 분석

```bash
pytest tests/core/parallel/ --cov=core/parallel --cov-report=term-missing -v
```

### 누락된 라인 확인

```bash
pytest tests/ --cov=core --cov-report=term-missing | grep -E "^\S+\.py"
```

## 커버리지 개선 가이드

### 미커버 코드 유형

| 유형 | 예시 | 권장 조치 |
|------|------|----------|
| except 블록 | `except ClientError` | 에러 케이스 테스트 추가 |
| 조건부 분기 | `if config.debug` | 다양한 설정으로 테스트 |
| 타임아웃 | `except TimeoutError` | 모킹으로 타임아웃 시뮬레이션 |
| 플랫폼 특정 | `if platform == 'win32'` | 해당 플랫폼에서 테스트 |

### 제외 설정 (pragma: no cover)

커버리지에서 제외할 코드:

```python
if TYPE_CHECKING:  # 타입 체크용 (pragma: no cover)
    from typing import Any

if __name__ == "__main__":  # 직접 실행용 (pragma: no cover)
    main()
```

## pyproject.toml 설정

```toml
[tool.coverage.run]
source = ["cli", "core", "plugins"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

## 출력 예시

```
/coverage 실행 결과

테스트 실행 중...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45/45 passed

커버리지 요약
─────────────────────────────────────────────────
모듈                    커버리지    상태
─────────────────────────────────────────────────
cli/                       88%       ✓
core/                      85%       ✓
  core/parallel/           92%       ✓
  core/tools/              78%       !
plugins/                   82%       ✓
─────────────────────────────────────────────────
TOTAL                      85%       ✓

미커버 주요 영역:
  - core/tools/io/excel/workbook.py:145-160 (에러 처리)
  - plugins/ec2/unused.py:89-95 (조건부 분기)

HTML 리포트: htmlcov/index.html
```

## 참조 파일

- `pyproject.toml` - coverage 설정
- `tests/conftest.py` - 공통 fixture
- `.claude/skills/tdd-workflow.md` - TDD 가이드
- `.claude/commands/make-test.md` - 테스트 스캐폴딩

## 주의사항

1. **테스트 의존성**: pytest-cov 패키지 필요
2. **병렬 실행**: `-n auto` 옵션과 함께 사용 시 coverage 설정 필요
3. **캐시**: `.coverage` 파일과 `htmlcov/` 디렉토리는 `.gitignore`에 추가
4. **CI 연동**: GitHub Actions에서 커버리지 배지 생성 가능
