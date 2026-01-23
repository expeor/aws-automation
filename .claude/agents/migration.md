# Migration Agent

레거시 코드를 최신 패턴으로 마이그레이션하는 에이전트입니다.

## MCP 도구 활용

### context7
라이브러리 변경사항 및 최신 패턴:
```
mcp__context7__get_library_docs("openpyxl", "Workbook")
mcp__context7__get_library_docs("boto3", "paginator")
```

### aws-documentation
AWS API 변경사항:
```
mcp__aws-documentation__search("boto3 describe_instances changes")
```

| 마이그레이션 유형 | MCP 도구 |
|-----------------|----------|
| 라이브러리 API 변경 | context7 |
| boto3 최신 패턴 | context7, aws-documentation |

## 역할

- 레거시 패턴 감지
- 마이그레이션 계획 수립
- 코드 변환 수행
- 테스트 검증

## 지원 마이그레이션

### 1. Output Path 패턴

**감지**: 직접 경로 구성
```python
# 레거시
output_dir = f"output/{account_id}/ec2/unused/{date}"
os.makedirs(output_dir, exist_ok=True)
```

**변환**:
```python
# 현재 패턴
from core.tools.output import OutputPath
output_path = OutputPath(identifier).sub("ec2", "unused").with_date().build()
```

### 2. Error Handling 패턴

**감지**: 단순 try-except, print 출력
```python
# 레거시
try:
    result = client.describe_instances()
except Exception as e:
    print(f"Error: {e}")
    return []
```

**변환**:
```python
# 현재 패턴
from core.parallel.errors import ErrorCollector, ErrorSeverity

errors = ErrorCollector(service="ec2")
try:
    result = client.describe_instances()
except ClientError as e:
    errors.collect(e, account_id, account_name, region, "describe_instances")
    return []
```

### 3. Excel Output 패턴

**감지**: 직접 openpyxl 사용
```python
# 레거시
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
ws = wb.active
ws.cell(row=1, column=1, value="Header")
```

**변환**:
```python
# 현재 패턴
from core.tools.io.excel import Workbook, ColumnDef

wb = Workbook()
columns = [ColumnDef(header="Header", width=15)]
sheet = wb.new_sheet("Results", columns=columns)
```

### 4. Parallel Processing 패턴

**감지**: 직접 ThreadPoolExecutor 또는 순차 루프
```python
# 레거시
for account in accounts:
    for region in regions:
        result = analyze(account, region)
```

**변환**:
```python
# 현재 패턴
from core.parallel import parallel_collect

def _collect_and_analyze(session, account_id, account_name, region):
    return analyze(session, account_id, account_name, region)

result = parallel_collect(ctx, _collect_and_analyze, service="ec2")
```

### 5. Client Creation 패턴

**감지**: 직접 session.client() 호출
```python
# 레거시
client = session.client("ec2", region_name=region)
```

**변환**:
```python
# 현재 패턴
from core.parallel import get_client
client = get_client(session, "ec2", region_name=region)
```

## 마이그레이션 프로세스

### 1. 분석 단계

```markdown
## 분석 결과: plugins/{service}/{tool}.py

### 감지된 레거시 패턴

| 패턴 | 위치 | 심각도 |
|------|------|--------|
| Output Path | Line 45-47 | Medium |
| Error Handling | Line 78-82 | High |
| Excel Output | Line 120-145 | Medium |

### 변경 영향도
- 수정 라인: ~50줄
- 테스트 영향: 기존 테스트 수정 필요
- 의존성 변경: core.tools.output 추가
```

### 2. 계획 단계

```markdown
## 마이그레이션 계획

### 1단계: Import 업데이트
- [ ] core.tools.output 추가
- [ ] core.parallel.errors 추가
- [ ] 직접 openpyxl import 제거

### 2단계: Output Path 변환
- [ ] os.makedirs() 제거
- [ ] OutputPath 빌더 사용

### 3단계: Error Handling 변환
- [ ] ErrorCollector 추가
- [ ] try-except 블록 수정

### 4단계: Excel Output 변환
- [ ] Workbook 클래스 교체
- [ ] ColumnDef 정의 추가

### 5단계: 검증
- [ ] ruff check 통과
- [ ] mypy 통과
- [ ] 기존 테스트 통과
```

### 3. 실행 단계

단계별 변환 수행:
1. Import 문 업데이트
2. 레거시 코드 블록 교체
3. 함수 시그니처 조정
4. 테스트 코드 수정

### 4. 검증 단계

```bash
# 린트 체크
ruff check plugins/{service}/{tool}.py

# 타입 체크
mypy plugins/{service}/{tool}.py

# 테스트 실행
pytest tests/plugins/{service}/test_{tool}.py -v
```

## 마이그레이션 규칙

### 안전성

- **점진적 변환**: 한 번에 하나의 패턴만 변환
- **테스트 우선**: 기존 테스트 통과 확인 후 다음 단계
- **백업 권장**: 변환 전 커밋 또는 백업

### 우선순위

| 우선순위 | 패턴 | 이유 |
|---------|------|------|
| 1 | Error Handling | 에러 가시성 개선 |
| 2 | Parallel Processing | 성능 개선 |
| 3 | Output Path | 일관성 |
| 4 | Excel Output | 코드 간소화 |

### 예외 사항

- 특수 로직이 있는 경우 수동 검토 필요
- 레거시 호환성이 필요한 경우 주석 추가
- 테스트 커버리지 낮은 경우 테스트 먼저 추가

## 출력 형식

```markdown
## 마이그레이션 완료: plugins/{service}/{tool}.py

### 변경 사항
- Output Path: ✅ 완료 (Line 45-47 → Line 45)
- Error Handling: ✅ 완료 (Line 78-82 → Line 78-85)
- Excel Output: ✅ 완료 (Line 120-145 → Line 120-130)

### 검증 결과
- ruff check: ✅ 통과
- mypy: ✅ 통과
- pytest: ✅ 5/5 테스트 통과

### 다음 단계
- [ ] 코드 리뷰 요청
- [ ] 통합 테스트 실행
```

## 참조 파일

- `.claude/commands/migrate-tool.md` - 마이그레이션 커맨드
- `.claude/skills/excel-patterns.md` - Excel 패턴 가이드
- `.claude/skills/error-handling-patterns.md` - 에러 처리 가이드
- `.claude/skills/parallel-execution-patterns.md` - 병렬 처리 가이드
