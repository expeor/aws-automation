# Excel 출력 패턴

프로젝트의 표준 Excel 보고서 생성 패턴입니다.

## 권장 패턴: core/tools/io/excel

```python
from core.tools.io.excel import Workbook, ColumnDef, Styles
```

## 기본 사용법

### 1. Workbook 생성

```python
from core.tools.io.excel import Workbook, ColumnDef

# 한국어 (기본)
wb = Workbook()

# 영어
wb = Workbook(lang="en")
```

### 2. 컬럼 정의

```python
columns = [
    ColumnDef(header="계정", header_en="Account", width=15, style="data"),
    ColumnDef(header="리전", header_en="Region", width=12, style="center"),
    ColumnDef(header="리소스 ID", header_en="Resource ID", width=25, style="data"),
    ColumnDef(header="크기(GB)", header_en="Size(GB)", width=10, style="number"),
    ColumnDef(header="비용", header_en="Cost", width=12, style="currency"),
    ColumnDef(header="상태", header_en="Status", width=10, style="center"),
]
```

### 스타일 타입

| style | 설명 | 정렬 |
|-------|------|------|
| `data` | 일반 텍스트 (기본) | 왼쪽, 줄바꿈 |
| `center` | 중앙 정렬 | 중앙, 줄바꿈 |
| `wrap` | 줄바꿈 텍스트 | 왼쪽, 줄바꿈 |
| `number` | 정수 (1,234) | 오른쪽 |
| `currency` | 통화 ($1,234.56) | 오른쪽 |
| `percent` | 백분율 (12.34%) | 오른쪽 |
| `text` | 강제 텍스트 (@) | 왼쪽 |

### 3. 시트 생성 및 데이터 추가

```python
# 시트 생성
sheet = wb.new_sheet("분석 결과", columns=columns)

# 데이터 행 추가
for item in results:
    sheet.add_row([
        item.account_name,
        item.region,
        item.resource_id,
        item.size_gb,
        item.cost,
        item.status,
    ])

# 조건부 스타일 적용
for item in results:
    style = None
    if item.status == "unused":
        style = Styles.danger()  # 빨간 배경
    elif item.status == "warning":
        style = Styles.warning()  # 노란 배경

    sheet.add_row([...], style=style)

# 요약 행
sheet.add_summary_row(["합계", "", "", total_size, total_cost, ""])
```

### 4. 저장

```python
# 전체 경로 지정
wb.save("/path/to/report.xlsx")

# 규칙 기반 파일명
wb.save_as(
    output_dir="/path/to/output",
    prefix="EBS_Unused",
    region="ap-northeast-2",  # 선택
    suffix="audit",           # 선택
)
# 결과: EBS_Unused_ap-northeast-2_20260123_audit.xlsx
```

## Summary 시트 (분석 요약)

```python
# Summary 시트 생성 (맨 앞에 위치)
summary = wb.new_summary_sheet()  # 또는 new_summary_sheet("분석 요약")

# 제목
summary.add_title("EBS 볼륨 분석 보고서")

# 섹션 + 항목
summary.add_section("분석 정보")
summary.add_item("분석 일시", "2026-01-23 15:30:00")
summary.add_item("계정 수", "5개")
summary.add_item("리전 수", "3개")

summary.add_section("분석 결과")
summary.add_item("총 볼륨", 150)
summary.add_item("미사용 볼륨", 23, highlight="danger")  # 빨간 강조
summary.add_item("월간 예상 비용", "$1,234.56", highlight="warning")  # 노란 강조

# 순위 리스트
summary.add_section("상위 항목")
summary.add_list_section("Top 5 계정별 미사용", [
    ("production-account", 12),
    ("dev-account", 8),
    ("staging-account", 3),
])

# 빈 행 추가
summary.add_blank_row()
```

### highlight 옵션

| highlight | 색상 | 용도 |
|-----------|------|------|
| `danger` | 빨강 | 주의 필요, 삭제 대상 |
| `warning` | 노랑 | 검토 필요 |
| `success` | 초록 | 정상, 완료 |
| `info` | 파랑 | 정보성 |

## Styles 프리셋

```python
from core.tools.io.excel import Styles

# 행 스타일
Styles.danger()   # 빨간 배경 + 흰 글씨
Styles.warning()  # 노란 배경
Styles.success()  # 초록 배경
Styles.summary()  # 연노랑 배경 + 볼드 (합계용)
```

## 전체 예시

```python
from core.tools.io.excel import Workbook, ColumnDef, Styles
from core.tools.output import OutputPath

def generate_report(results: list[AnalysisResult], ctx) -> str:
    wb = Workbook()

    # Summary 시트
    summary = wb.new_summary_sheet()
    summary.add_title("미사용 리소스 분석")
    summary.add_section("요약")
    summary.add_item("총 리소스", len(results))
    summary.add_item("미사용", sum(1 for r in results if r.unused), highlight="danger")

    # Detail 시트
    columns = [
        ColumnDef(header="계정", width=15),
        ColumnDef(header="리전", width=12, style="center"),
        ColumnDef(header="ID", width=25),
        ColumnDef(header="상태", width=10, style="center"),
        ColumnDef(header="비용", width=12, style="currency"),
    ]
    sheet = wb.new_sheet("상세", columns=columns)

    for r in results:
        style = Styles.danger() if r.unused else None
        sheet.add_row([r.account, r.region, r.id, r.status, r.cost], style=style)

    # 저장
    output_path = OutputPath(ctx.identifier).sub("service", "audit").with_date().build()
    return str(wb.save_as(output_path, "report"))
```

## 레거시 패턴 (사용 지양)

```python
# ❌ 직접 openpyxl 사용
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
ws = wb.active
ws.cell(row=1, column=1, value="Header")
ws.cell(row=1, column=1).fill = PatternFill(...)  # 수동 스타일

# ✅ core/tools/io/excel 사용
from core.tools.io.excel import Workbook, ColumnDef
wb = Workbook()
sheet = wb.new_sheet("Results", columns=[...])  # 자동 스타일
```

## 자동 적용 기능

`Workbook` 클래스 사용 시 자동 적용:
- 헤더 스타일 (파란 배경, 흰 글씨, 볼드)
- 자동 필터
- 첫 행 고정 (freeze_panes)
- 줌 85%
- 테두리
- 컬럼 너비

## 참조

- `core/tools/io/excel/workbook.py` - Workbook, Sheet, ColumnDef
- `core/tools/io/excel/styles.py` - 스타일 정의
