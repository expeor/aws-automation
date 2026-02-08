# CLI 출력 스타일 가이드

콘솔 출력 시 사용하는 표준 스타일입니다.

## 표준 심볼 (이모지 사용 금지)

```python
from core.cli.ui import (
    SYMBOL_SUCCESS,   # ✓ - 완료
    SYMBOL_ERROR,     # ✗ - 에러
    SYMBOL_WARNING,   # ! - 경고
    SYMBOL_INFO,      # • - 정보
    SYMBOL_PROGRESS,  # • - 진행 중
)
```

---

## 표준 출력 함수

```python
from core.cli.ui import (
    print_success,      # [green]✓ 메시지[/green]
    print_error,        # [red]✗ 메시지[/red]
    print_warning,      # [yellow]! 메시지[/yellow]
    print_info,         # [blue]• 메시지[/blue]
    print_step_header,  # [bold cyan]Step N: 메시지[/bold cyan]
    print_sub_task,     # 메시지 (들여쓰기 없음)
    print_sub_task_done,# [green]✓ 메시지[/green]
)
```

---

## Step 출력 패턴

```python
from core.cli.ui import console, print_step_header

# Step 헤더
print_step_header(1, "데이터 수집 중...")
# 출력: [bold cyan]Step 1: 데이터 수집 중...[/bold cyan]

# 부작업 진행
console.print("S3에서 파일 검색 중...")

# 부작업 완료
console.print("[green]✓ 50개 파일 발견[/green]")
```

---

## 출력 예시

```
Step 1: 데이터 수집 중...
S3에서 파일 검색 중...
✓ 50개 파일 발견
Step 2: 분석 중...
로그 파싱 중...
✓ 1,000개 로그 분석 완료
Step 3: 보고서 생성 중...
Excel 보고서 생성 완료    ━━━━━━━━━━━━━━━━━━━━━━━    10/10    0:00:01
HTML 보고서 생성 중...
✓ HTML 보고서 생성 완료

✓ 보고서 생성 완료!
   EXCEL: output/report.xlsx
   HTML: output/report.html
```

---

## 금지 사항

- **이모지 사용 금지**: `📊`, `🔍`, `⏰`, `🚀`, `🧹`, `📋` 등
- **이모지 체크마크 금지**: `✅`, `❌` → `✓`, `✗` 사용
- **이모지 경고 금지**: `⚠️` → `!` 사용

---

## 테이블 상태 표시

```python
# 활성화 상태
status = "[green]✓[/green]" if enabled else "[red]✗[/red]"

# 알 수 없는 상태
status = "[dim]?[/dim]"
```

---

## 섹션 헤더

```python
# 이모지 없이 텍스트만
console.print("\n[bold cyan]ALB 로그 분석 설정[/bold cyan]")
console.print("\n[bold cyan]분석 시간 범위 설정[/bold cyan]")
```

---

## 경고/에러 메시지

```python
# 경고
console.print("[yellow]! 파일을 찾을 수 없습니다.[/yellow]")

# 에러
console.print("[red]✗ 연결 실패: timeout[/red]")

# 성공
console.print("[green]✓ 분석 완료[/green]")
```

---

## Progress 표시 (Rich)

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,
) as progress:
    task = progress.add_task("수집 중...", total=None)
    # 작업 수행
```

---

## 숫자 포맷팅

```python
# 큰 숫자 (천 단위 쉼표)
console.print(f"총 {total:,}개")  # 총 1,234개

# 백분율
console.print(f"사용률: {percent:.1f}%")  # 사용률: 87.5%

# 통화
console.print(f"절감액: ${savings:,.2f}")  # 절감액: $1,234.56

# 바이트
def format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

console.print(f"크기: {format_bytes(size)}")  # 크기: 1.5 GB
```

---

## 테이블 출력

```python
from rich.table import Table

table = Table(title="분석 결과", show_header=True)
table.add_column("계정", style="cyan")
table.add_column("리전", style="white")
table.add_column("미사용", style="red", justify="right")
table.add_column("절감액", style="green", justify="right")

for row in results:
    table.add_row(
        row["account"],
        row["region"],
        str(row["unused_count"]),
        f"${row['savings']:,.2f}"
    )

console.print(table)
```

---

## 참조

- `cli/ui/__init__.py` - 표준 출력 함수
- `cli/ui/symbols.py` - 표준 심볼 정의
- `.claude/skills/output-patterns.md` - 리포트 출력 패턴 (Excel, HTML)
