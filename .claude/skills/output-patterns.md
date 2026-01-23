# 리포트 출력 패턴

프로젝트의 표준 리포트 생성 패턴입니다. Excel과 HTML을 동시에 생성합니다.

## 출력 설정 (OutputConfig)

```python
from core.tools.io import OutputConfig, OutputFormat

# 기본값: Excel + HTML 모두 출력
config = OutputConfig()

# 형식 확인
if config.should_output_excel():
    # Excel 출력
if config.should_output_html():
    # HTML 출력

# 문자열에서 생성
config = OutputConfig.from_string("both")  # excel, html, both, console
```

### OutputFormat 플래그

| 형식 | 설명 |
|------|------|
| `EXCEL` | Excel 파일 출력 |
| `HTML` | HTML 리포트 출력 |
| `CONSOLE` | 콘솔 출력만 |
| `ALL` | Excel + HTML (기본값) |

---

## 권장 패턴: generate_reports()

**새 플러그인 작성 시 권장하는 통합 출력 API**

```python
from core.tools.io.compat import generate_reports

def run(ctx) -> None:
    results = parallel_collect(ctx, _collect_and_analyze, service="ec2")

    # HTML용 flat 데이터 준비
    flat_data = [
        {
            "account_id": r.account_id,
            "account_name": r.account_name,
            "region": r.region,
            "resource_id": r.resource_id,
            "resource_name": r.name,
            "status": r.status,
            "reason": r.recommendation,
            "cost": r.monthly_cost,
        }
        for r in results
    ]

    # Excel + HTML 동시 생성
    report_paths = generate_reports(
        ctx,
        data=flat_data,
        excel_generator=lambda d: _save_excel(results, d),
        html_config={
            "title": "EC2 미사용 인스턴스 분석",
            "service": "EC2",
            "tool_name": "unused",
            "total": total_count,
            "found": unused_count,
            "savings": total_savings,
        },
        output_dir=output_path,
    )

    # 결과 출력
    if report_paths.get("excel"):
        console.print(f"Excel: {report_paths['excel']}")
    if report_paths.get("html"):
        console.print(f"HTML: {report_paths['html']}")
```

---

## Excel 출력 패턴

### 기본 사용법

```python
from core.tools.io.excel import Workbook, ColumnDef, Styles

# Workbook 생성
wb = Workbook()  # 한국어 (기본)
wb = Workbook(lang="en")  # 영어

# 컬럼 정의
columns = [
    ColumnDef(header="계정", header_en="Account", width=15, style="data"),
    ColumnDef(header="리전", header_en="Region", width=12, style="center"),
    ColumnDef(header="크기(GB)", header_en="Size(GB)", width=10, style="number"),
    ColumnDef(header="비용", header_en="Cost", width=12, style="currency"),
]

# 시트 생성 및 데이터 추가
sheet = wb.new_sheet("분석 결과", columns=columns)

for item in results:
    style = Styles.danger() if item.unused else None
    sheet.add_row([item.account, item.region, item.size, item.cost], style=style)

# 요약 행
sheet.add_summary_row(["합계", "", total_size, total_cost])

# 저장
wb.save_as(output_dir, prefix="EC2_Unused", region="ap-northeast-2")
```

### 스타일 타입

| style | 설명 | 정렬 |
|-------|------|------|
| `data` | 일반 텍스트 (기본) | 왼쪽, 줄바꿈 |
| `center` | 중앙 정렬 | 중앙, 줄바꿈 |
| `number` | 정수 (1,234) | 오른쪽 |
| `currency` | 통화 ($1,234.56) | 오른쪽 |
| `percent` | 백분율 (12.34%) | 오른쪽 |

### Styles 프리셋

```python
Styles.danger()   # 빨간 배경 + 흰 글씨
Styles.warning()  # 노란 배경
Styles.success()  # 초록 배경
Styles.summary()  # 연노랑 배경 + 볼드 (합계용)
```

### Summary 시트

```python
summary = wb.new_summary_sheet()
summary.add_title("EBS 볼륨 분석 보고서")
summary.add_section("분석 정보")
summary.add_item("분석 일시", "2026-01-23 15:30:00")
summary.add_item("계정 수", "5개")
summary.add_section("분석 결과")
summary.add_item("미사용 볼륨", 23, highlight="danger")
summary.add_item("월간 예상 비용", "$1,234.56", highlight="warning")
```

---

## HTML 출력 패턴

### AWSReport (권장)

```python
from core.tools.io.html import AWSReport, ResourceItem

# 리포트 생성
report = AWSReport(
    title="EC2 미사용 리소스 분석",
    service="EC2",
    tool_name="unused",
    ctx=ctx,
)

# 요약 정보
report.set_summary(
    total=150,
    found=23,
    savings=1234.56,
)

# 리소스 추가
for item in results:
    report.add_resource(ResourceItem(
        account_id=item["account_id"],
        account_name=item["account_name"],
        region=item["region"],
        resource_id=item["instance_id"],
        resource_name=item.get("name", ""),
        status="unused",
        reason=item["reason"],
        cost=item.get("monthly_cost", 0),
    ))

# 저장 (브라우저 자동 열림)
report.save(output_path)
```

### 간편 API

```python
from core.tools.io.html import create_aws_report

report = create_aws_report(
    title="EC2 미사용",
    service="EC2",
    tool_name="unused",
    ctx=ctx,
    resources=results,  # list[dict]
    total=100,
    found=10,
    savings=500.0,
)
report.save("output.html")
```

### 자동 생성 기능

AWSReport 사용 시 자동 생성:
- 요약 카드 (전체, 발견, 비율, 절감액)
- 계정별 분포 차트 (Pie)
- 리전별 분포 차트 (Bar)
- 상태별 분포 차트 (있는 경우)
- 리소스 상세 테이블 (검색, 정렬, 페이지네이션)

---

## CLI --format 옵션

```bash
# 기본값: Excel + HTML 둘 다
aa run ec2/unused -p my-profile -r ap-northeast-2

# Excel만
aa run ec2/unused -p my-profile -r ap-northeast-2 --format excel

# HTML만
aa run ec2/unused -p my-profile -r ap-northeast-2 --format html

# 콘솔만 (파일 생성 X)
aa run ec2/unused -p my-profile -r ap-northeast-2 --format console
```

---

## 전체 예시 (새 플러그인)

```python
from core.tools.io.compat import generate_reports
from core.tools.io.excel import Workbook, ColumnDef, Styles
from core.tools.output import OutputPath

def _save_excel(results: list, output_dir: str) -> str:
    """Excel 보고서 생성"""
    wb = Workbook()

    columns = [
        ColumnDef(header="Account", width=20),
        ColumnDef(header="Region", width=15),
        ColumnDef(header="Resource ID", width=25),
        ColumnDef(header="Status", width=12, style="center"),
        ColumnDef(header="Cost", width=12, style="currency"),
    ]
    sheet = wb.new_sheet("Results", columns)

    for r in results:
        style = Styles.danger() if r.unused else None
        sheet.add_row([r.account, r.region, r.id, r.status, r.cost], style=style)

    return str(wb.save_as(output_dir, "Service_Type"))


def run(ctx) -> None:
    """도구 실행"""
    results = parallel_collect(ctx, _collect_and_analyze, service="service")

    # Flat 데이터 (HTML용)
    flat_data = [
        {
            "account_id": r.account_id,
            "account_name": r.account_name,
            "region": r.region,
            "resource_id": r.id,
            "status": r.status,
            "reason": r.reason,
            "cost": r.cost,
        }
        for r in results
    ]

    # 출력 경로
    identifier = ctx.accounts[0].id if ctx.accounts else ctx.profile_name or "default"
    output_path = OutputPath(identifier).sub("service", "type").with_date().build()

    # Excel + HTML 동시 생성
    report_paths = generate_reports(
        ctx,
        data=flat_data,
        excel_generator=lambda d: _save_excel(results, d),
        html_config={
            "title": "서비스 분석",
            "service": "Service",
            "tool_name": "type",
            "total": len(results),
            "found": sum(1 for r in results if r.unused),
            "savings": sum(r.cost for r in results if r.unused),
        },
        output_dir=output_path,
    )

    console.print("\n[bold green]완료![/bold green]")
    for fmt, path in report_paths.items():
        console.print(f"  {fmt.upper()}: {path}")
```

---

## 대용량 데이터 처리 패턴

50개 이상의 계정이나 100개 이상의 리소스 종류가 있을 때 사용합니다.

### Best Practices

| 데이터 규모 | 권장 패턴 |
|------------|----------|
| ~6개 카테고리 | Pie 차트 그대로 |
| 7-15개 카테고리 | Top 5 + "기타" 그룹화 (자동) |
| 16개+ 카테고리 | Treemap 또는 Bar (horizontal) |
| 계층 데이터 (계정→리전→서비스) | Treemap with drill-down |

### Top N + "기타" 그룹화

```python
from core.tools.io.html import group_top_n, aggregate_by_group

# 50개 계정 → Top 10 + "기타 (40개)"
accounts = [("account-1", 150), ("account-2", 120), ...]  # 50개
grouped = group_top_n(accounts, top_n=10)
# → [("account-1", 150), ..., ("기타 (40개)", 350)]

# dict 리스트에서 집계
data = [{"account": "A", "region": "ap-northeast-2"}, ...]
by_account = aggregate_by_group(data, "account")  # 카운트
by_region = aggregate_by_group(data, "region", "cost", "sum")  # 합계
```

### 계층적 Treemap (대규모 환경 권장)

```python
from core.tools.io.html import build_treemap_hierarchy, HTMLReport

# 원본 데이터 (수천 개 가능)
items = [
    {"account": "prod-1", "region": "ap-northeast-2", "service": "EC2", "count": 45},
    {"account": "prod-1", "region": "ap-northeast-2", "service": "RDS", "count": 12},
    {"account": "prod-1", "region": "us-east-1", "service": "EC2", "count": 23},
    {"account": "dev-1", "region": "ap-northeast-2", "service": "Lambda", "count": 89},
    # ... 수백/수천 개
]

# 계층 구조로 변환 (계정 → 리전 → 서비스)
treemap_data = build_treemap_hierarchy(
    items,
    group_keys=["account", "region", "service"],
    value_key="count"
)

# Treemap 차트 (각 레벨 Top 10, 최대 깊이 3)
report = HTMLReport("리소스 분포")
report.add_treemap_chart("계정별 리소스 분포", treemap_data, top_n_per_level=10)
report.save("output.html")
```

### 차트별 자동 대용량 처리

```python
report = HTMLReport("대용량 테스트")

# Pie: 6개 초과 시 자동으로 Top 5 + 기타
report.add_pie_chart("계정별 분포", accounts_50)  # 자동 그룹화

# Pie: 명시적 Top N 지정
report.add_pie_chart("서비스별 분포", services_100, top_n=8)

# Bar: 8개 이상 시 자동 horizontal
report.add_bar_chart("리전별 비용", regions_15, [...])  # 자동 가로 바

# Bar: 명시적 Top N
report.add_bar_chart("Top 10 계정", accounts_50, [...], top_n=10)

# Line: 30개 이상 시 자동 스크롤
report.add_line_chart("일별 추이", days_90, [...])  # dataZoom 자동 활성화
```

### 시계열 차트 (CloudWatch 스타일)

로그 분석, 메트릭 추이 등 시간 기반 데이터에 최적화된 차트입니다.

```python
from core.tools.io.html import HTMLReport

report = HTMLReport("로그 분석")

# 단일 시리즈
report.add_time_series_chart(
    "요청 트렌드",
    timestamps=timestamps,  # list[datetime]
    values=[100, 150, 200, ...],
)

# 다중 시리즈
report.add_time_series_chart(
    "상태코드별 트렌드",
    timestamps=timestamps,
    values={
        "2xx": [80, 120, 150, ...],
        "4xx": [10, 15, 20, ...],
        "5xx": [2, 3, 1, ...],
    },
    aggregation="sum",  # sum, avg, max, min, count
    area=True,
)
```

**자동 해상도 (CloudWatch 스타일):**

시간 범위에 따라 적절한 집계 단위를 자동 결정합니다.

| 시간 범위 | 버킷 크기 | 표시 형식 |
|----------|----------|----------|
| ≤3시간 | 5분 | HH:MM |
| ≤24시간 | 15분 | HH:MM |
| ≤7일 | 1시간 | MM/DD HH:MM |
| ≤30일 | 4시간 | MM/DD HH:MM |
| >30일 | 1일 | MM/DD |

```python
# 명시적 버킷 크기 지정
report.add_time_series_chart(
    "분당 요청",
    timestamps=timestamps,
    values=values,
    bucket_minutes=1,  # 1분 단위 강제
)
```

**ALB 로그 분석 예시:**

```python
# 타임스탬프와 에러 플래그 수집
all_timestamps: list[datetime] = []
is_error_list: list[int] = []

for key in ["ELB 2xx Count", "ELB 3xx Count", "ELB 4xx Count", "ELB 5xx Count"]:
    log_data = analysis_results.get(key, {})
    if isinstance(log_data, dict):
        timestamps = log_data.get("timestamps", [])
        is_error = 1 if ("4xx" in key or "5xx" in key) else 0
        for ts in timestamps:
            if ts and hasattr(ts, "timestamp"):
                all_timestamps.append(ts)
                is_error_list.append(is_error)

if all_timestamps:
    report.add_time_series_chart(
        "시간대별 요청 트렌드",
        timestamps=all_timestamps,
        values={
            "전체 요청": [1] * len(all_timestamps),
            "에러 (4xx+5xx)": is_error_list,
        },
        aggregation="sum",
        area=True,
    )
```

### 동적 차트 크기 (ChartSize)

데이터 복잡도에 따라 차트 크기가 자동으로 조절됩니다.

```python
from core.tools.io.html import ChartSize

# ChartSize enum
ChartSize.SMALL   # 350px, 1열 (50%)
ChartSize.MEDIUM  # 400px, 1열 (50%)
ChartSize.LARGE   # 500px, 전체 너비 (100%)
ChartSize.XLARGE  # 600px, 전체 너비 (100%)
```

**자동 크기 결정 기준:**

| 복잡도 (카테고리 × 시리즈) | 크기 | 높이 | 그리드 |
|--------------------------|------|------|--------|
| ≤6 | SMALL | 350px | 1열 (50%) |
| 7-15 | MEDIUM | 400px | 1열 (50%) |
| 16-30 | LARGE | 500px | 전체 너비 |
| 31+ | XLARGE | 600px | 전체 너비 |

**특수 케이스:**

- **가로 Bar 차트**: `max(기본높이, 카테고리수 × 35px)`
- **Treemap**: 노드 20개 이하 LARGE(450px), 초과 XLARGE(600px)
- **Line 차트**: 50개+ 카테고리 시 LARGE 이상

### 성능 최적화

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `ANIMATION_THRESHOLD` | 100 | 이 개수 초과 시 애니메이션 비활성화 |
| `DEFAULT_TOP_N` | 10 | group_top_n 기본값 |
| `MAX_CHART_CATEGORIES` | 15 | 차트 권장 최대 카테고리 |

```python
# ECharts 옵션에 자동 적용됨
option = {
    "animationThreshold": 100,  # 대용량 시 애니메이션 OFF
    ...
}
```

---

## 참조

- `core/tools/io/config.py` - OutputConfig, OutputFormat
- `core/tools/io/compat.py` - generate_reports, generate_dual_report
- `core/tools/io/excel/workbook.py` - Workbook, Sheet, ColumnDef
- `core/tools/io/html/aws_report.py` - AWSReport, ResourceItem
- `core/tools/io/html/report.py` - HTMLReport, ChartSize, group_top_n, aggregate_by_group, build_treemap_hierarchy

### HTMLReport 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `add_summary()` | 요약 카드 (라벨, 값, 색상) |
| `add_pie_chart()` | 파이/도넛/로즈 차트 |
| `add_bar_chart()` | 바 차트 (자동 horizontal) |
| `add_line_chart()` | 라인 차트 (자동 스크롤) |
| `add_time_series_chart()` | 시계열 차트 (CloudWatch 스타일 적응형 해상도) |
| `add_gauge_chart()` | 게이지 차트 |
| `add_radar_chart()` | 레이더 차트 |
| `add_treemap_chart()` | 트리맵 (계층 데이터) |
| `add_heatmap_chart()` | 히트맵 |
| `add_scatter_chart()` | 산점도 |
| `add_table()` | 테이블 (검색, 정렬, 페이지네이션) |
