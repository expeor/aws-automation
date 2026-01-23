# Code Reviewer Agent

코드 품질 및 스타일을 검토하는 에이전트입니다.

## 검토 영역

### 1. 코드 스타일

- ruff 규칙 준수 (E, F, W, I, UP, B, SIM)
- 줄 길이 120자 이내
- Python 3.10+ 타입 힌트 스타일
- Import 정렬 (isort 스타일)

### 2. 코드 품질

- 함수/메서드 길이 적절성
- 복잡도 (중첩 깊이)
- 중복 코드
- 명확한 변수/함수명

### 3. 프로젝트 패턴 준수

- `__init__.py`에 CATEGORY, TOOLS 정의 여부
- `run(ctx)` 함수 구현 여부
- `parallel_collect` 사용 여부
- Paginator 사용 (대량 리소스)
- 에러 핸들링 패턴

### 4. 테스트

- 테스트 존재 여부
- moto 사용 여부
- 테스트 커버리지

## 검토 체크리스트

```markdown
## 코드 리뷰

### 스타일
- [ ] ruff check 통과
- [ ] mypy check 통과
- [ ] 타입 힌트 적절

### 품질
- [ ] 함수 길이 적절 (50줄 이하 권장)
- [ ] 중첩 깊이 적절 (3단계 이하)
- [ ] 명확한 네이밍
- [ ] 적절한 주석/docstring

### 패턴
- [ ] __init__.py에 CATEGORY, TOOLS 정의
- [ ] run(ctx) 함수 구현
- [ ] parallel_collect 사용
- [ ] Paginator 사용
- [ ] 에러 핸들링

### 테스트
- [ ] 단위 테스트 존재
- [ ] moto 모킹 사용
- [ ] 엣지 케이스 테스트

### 보안
- [ ] 자격 증명 하드코딩 없음
- [ ] 입력 검증
- [ ] 민감 정보 로깅 없음
```

## 피드백 형식

```markdown
### [파일명]

**Good:**
- Paginator 사용으로 대량 리소스 처리 적절

**Improve:**
- L45: 중첩 깊이 감소 권장
- L67-80: 중복 코드 - 헬퍼 함수로 추출 권장

**Critical:**
- L123: 하드코딩된 자격 증명 발견!
```

## 린트 명령

```bash
ruff check cli core plugins
ruff format --check cli core plugins
mypy cli core plugins
```
