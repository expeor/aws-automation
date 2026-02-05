"""
aa_cli/aa/ui/console.py - Rich 콘솔 유틸리티

일관된 콘솔 출력을 위한 함수들
"""

import logging
import platform
import sys

from rich.columns import Columns as RichColumns
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule
from rich.table import Table
from rich.tree import Tree

from cli.i18n import t

# botocore 노이즈 로그 제한
logging.getLogger("botocore.httpchecksum").setLevel(logging.WARNING)
logging.getLogger("botocore.credentials").setLevel(logging.WARNING)
logging.getLogger("botocore.loaders").setLevel(logging.WARNING)
logging.getLogger("botocore.session").setLevel(logging.WARNING)


def get_console() -> Console:
    """Rich Console 인스턴스를 생성하고 반환합니다."""
    is_windows = platform.system().lower() == "windows"

    return Console(
        force_terminal=True,
        color_system="auto",
        highlight=True,
        record=True,
        soft_wrap=True,
        markup=True,
        emoji=not is_windows,
    )


# 전역 콘솔 인스턴스
console = get_console()


def clear_screen() -> None:
    """화면을 클리어합니다."""
    console.clear()


def get_progress() -> Progress:
    """Rich Progress 인스턴스를 생성하고 반환합니다."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    )


def get_logger(name: str = "rich") -> logging.Logger:
    """Rich 핸들러가 설정된 logger를 반환합니다.

    Args:
        name: logger 이름 (기본값: "rich")

    Returns:
        logging.Logger: 설정된 logger 인스턴스
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RichHandler(console=console, rich_tracebacks=True)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(handler)

    return logger


# 전역 logger 인스턴스
logger = get_logger()


# =============================================================================
# 표준 출력 스타일 (이모지 없이 Rich 스타일만 사용)
# =============================================================================

# 상태 심볼
SYMBOL_SUCCESS = "✓"  # 완료
SYMBOL_ERROR = "✗"  # 에러
SYMBOL_WARNING = "!"  # 경고
SYMBOL_INFO = "•"  # 정보
SYMBOL_PROGRESS = "•"  # 진행 중


def print_success(message: str) -> None:
    """성공 메시지 출력 (초록색 체크마크)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[green]{SYMBOL_SUCCESS} {message}[/green]")


def print_error(message: str) -> None:
    """에러 메시지 출력 (빨간색 X)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[red]{SYMBOL_ERROR} {message}[/red]")


def print_warning(message: str) -> None:
    """경고 메시지 출력 (노란색 경고)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[yellow]{SYMBOL_WARNING} {message}[/yellow]")


def print_info(message: str) -> None:
    """정보 메시지 출력 (파란색 정보)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[blue]{SYMBOL_INFO} {message}[/blue]")


def print_header(title: str) -> None:
    """섹션 헤더 출력

    Args:
        title: 헤더 제목
    """
    console.print()
    console.print(f"[bold underline cyan]{title}[/bold underline cyan]")
    console.print()


def print_step(step: int, total: int, message: str) -> None:
    """진행 단계 출력

    Args:
        step: 현재 단계
        total: 전체 단계 수
        message: 단계 설명
    """
    console.print(f"[dim]({step}/{total})[/dim] {message}")


def print_step_header(step: int, message: str) -> None:
    """Step 헤더 출력 (예: Step 1: 데이터 수집 중...)

    Args:
        step: Step 번호
        message: Step 설명
    """
    console.print(f"[bold cyan]Step {step}: {message}[/bold cyan]")


INDENT = "   "  # Step 내 부작업 들여쓰기 (3칸)


def print_sub_task(message: str) -> None:
    """하위 작업 진행 중 출력 (들여쓰기)

    Args:
        message: 작업 설명

    Example:
        print_step_header(1, "데이터 수집 중...")
        print_sub_task("S3에서 파일 검색 중...")
        print_sub_task_done("100개 파일 발견")
    """
    console.print(f"{INDENT}{message}")


def print_sub_task_done(message: str) -> None:
    """하위 작업 완료 출력 (들여쓰기 + 체크마크)

    Args:
        message: 완료 메시지
    """
    console.print(f"{INDENT}[green]{SYMBOL_SUCCESS} {message}[/green]")


def print_sub_info(message: str) -> None:
    """하위 작업 정보 출력 (들여쓰기 + 파란색)

    Args:
        message: 정보 메시지
    """
    console.print(f"{INDENT}[blue]{message}[/blue]")


def print_sub_warning(message: str) -> None:
    """하위 작업 경고 출력 (들여쓰기 + 노란색)

    Args:
        message: 경고 메시지
    """
    console.print(f"{INDENT}[yellow]{SYMBOL_WARNING} {message}[/yellow]")


def print_sub_error(message: str) -> None:
    """하위 작업 에러 출력 (들여쓰기 + 빨간색)

    Args:
        message: 에러 메시지
    """
    console.print(f"{INDENT}[red]{SYMBOL_ERROR} {message}[/red]")


def print_panel_header(title: str, subtitle: str | None = None) -> None:
    """제목과 부제목을 포함한 패널 헤더를 출력합니다.

    Args:
        title: 제목
        subtitle: 부제목 (선택)
    """
    if subtitle:
        console.print(
            Panel(
                f"[bold blue]{title}[/]\n[dim]{subtitle}[/]",
                border_style="blue",
                padding=(1, 2),
            )
        )
    else:
        console.print(
            Panel(
                f"[bold blue]{title}[/]",
                border_style="blue",
                padding=(1, 2),
            )
        )


def print_table(
    title: str,
    columns: list[str],
    rows: list[list],
) -> None:
    """테이블 형식으로 데이터를 출력합니다.

    Args:
        title: 테이블 제목
        columns: 컬럼 헤더 리스트
        rows: 행 데이터 리스트
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")

    for column in columns:
        table.add_column(column)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def print_legend(items: list[tuple]) -> None:
    """색상 범례를 출력합니다.

    Args:
        items: (색상, 설명) 튜플 리스트
               색상은 rich 색상명 (yellow, red, green, blue 등)

    Example:
        print_legend([
            ("yellow", "사용 중(in-use)"),
            ("red", "암호화 안됨"),
        ])
        # 출력: 색상 범례: 노란색 = 사용 중(in-use), 빨간색 = 암호화 안됨
    """
    color_names = {
        "yellow": t("common.color_yellow"),
        "red": t("common.color_red"),
        "green": t("common.color_green"),
        "blue": t("common.color_blue"),
        "cyan": t("common.color_cyan"),
        "magenta": t("common.color_magenta"),
        "orange": t("common.color_orange"),
        "gray": t("common.color_gray"),
        "dim": t("common.color_gray"),
    }

    legend_parts = []
    for color, description in items:
        color_name = color_names.get(color, color)
        legend_parts.append(f"[{color}]{color_name}[/{color}] = {description}")

    legend_text = ", ".join(legend_parts)
    console.print(f"[dim]{t('common.color_legend')} {legend_text}[/dim]")


# =============================================================================
# 섹션 박스 UI 컴포넌트
# =============================================================================

# 박스 테마 설정
BOX_WIDTH = 70  # 기본 박스 너비
BOX_STYLE = "#FF9900"  # AWS 오렌지 (배너와 통일)


def print_section_box(
    title: str,
    content_lines: list[str] | None = None,
    style: str = BOX_STYLE,
) -> None:
    """섹션 박스를 출력합니다.

    상단, 하단 테두리와 함께 내용을 출력합니다.

    Args:
        title: 박스 제목
        content_lines: 박스 내용 (각 줄별 리스트). None이면 시작만 출력
        style: 테두리 색상 (기본: cyan)

    Example:
        print_section_box("인증 방식 선택", [
            "  1. 🔐 SSO 세션",
            "     AWS IAM Identity Center",
        ])
    """
    console.print()
    console.print(f"[bold {style}]┌─ {title}[/bold {style}]")
    console.print(f"[bold {style}]│[/bold {style}]")

    if content_lines:
        for line in content_lines:
            console.print(f"[bold {style}]│[/bold {style}] {line}")
        console.print(f"[bold {style}]│[/bold {style}]")
        console.print(f"[bold {style}]└─[/bold {style}]")
        console.print()


def print_box_line(content: str = "", style: str = BOX_STYLE) -> None:
    """박스 내부 라인을 출력합니다.

    Args:
        content: 라인 내용 (빈 문자열이면 빈 라인)
        style: 테두리 색상
    """
    if content:
        console.print(f"[bold {style}]│[/bold {style}] {content}")
    else:
        console.print(f"[bold {style}]│[/bold {style}]")


def print_box_end(style: str = BOX_STYLE) -> None:
    """박스 하단을 출력합니다.

    Args:
        style: 테두리 색상
    """
    console.print(f"[bold {style}]└─[/bold {style}]")
    console.print()


def print_box_start(title: str, style: str = BOX_STYLE) -> None:
    """박스 상단만 출력합니다 (내용은 별도로 추가).

    Args:
        title: 박스 제목
        style: 테두리 색상
    """
    console.print()
    console.print(f"[bold {style}]┌─ {title}[/bold {style}]")
    console.print(f"[bold {style}]│[/bold {style}]")


# =============================================================================
# 도구 실행 UI 컴포넌트
# =============================================================================


def print_tool_start(tool_name: str, description: str = "") -> None:
    """도구 실행 시작 표시

    Args:
        tool_name: 도구 이름
        description: 도구 설명
    """
    console.print()
    console.print(f"[bold #FF9900]▶ {tool_name}[/]")
    if description:
        console.print(f"  [dim]{description}[/]")
    console.print(Rule(style="dim"))


def print_tool_complete(message: str | None = None, elapsed: float | None = None) -> None:
    """도구 실행 완료 표시

    Args:
        message: 완료 메시지
        elapsed: 소요 시간 (초)
    """
    if message is None:
        message = t("common.completed")
    console.print()
    console.print(Rule(style="dim"))
    if elapsed:
        console.print(f"[green]* {message}[/] [dim]({elapsed:.1f}s)[/]")
    else:
        console.print(f"[green]* {message}[/]")


# =============================================================================
# Rich 유틸리티 함수
# =============================================================================


def print_rule(title: str = "", style: str = "dim") -> None:
    """Rich Rule로 구분선 출력

    Args:
        title: 구분선 제목 (빈 문자열이면 제목 없는 구분선)
        style: 스타일 (기본: dim)
    """
    if title:
        console.print(Rule(title=title, style=style))
    else:
        console.print(Rule(style=style))


def print_result_tree(title: str, sections: list[dict]) -> None:
    """계층적 결과 트리 출력

    Args:
        title: 트리 루트 제목
        sections: 섹션 리스트. 각 섹션은:
            - label: 섹션 라벨
            - items: (label, value, style) 튜플 리스트

    Example:
        print_result_tree("분석 결과", [
            {"label": "EC2", "items": [("미사용", 5, "red"), ("저사용", 12, "yellow")]},
            {"label": "RDS", "items": [("미사용", 2, "red")]},
        ])
    """
    tree = Tree(f"[bold]{title}[/bold]")
    for section in sections:
        branch = tree.add(f"[cyan]{section['label']}[/cyan]")
        for item in section.get("items", []):
            label, value, style = item
            branch.add(f"[{style}]{label}: {value}[/{style}]")
    console.print(tree)


def print_error_tree(errors: list[tuple[str, list[str]]], title: str = "오류 요약") -> None:
    """에러를 카테고리별 계층 트리로 출력

    Args:
        errors: (category, [detail_items]) 튜플 리스트
        title: 트리 루트 제목

    Example:
        print_error_tree([
            ("AccessDenied", ["ap-northeast-2", "us-east-1"]),
            ("ThrottlingException", ["eu-west-1"]),
        ])
    """
    tree = Tree(f"[bold yellow]{title}[/bold yellow]")
    for category, items in errors:
        branch = tree.add(f"[red]{category}[/red] ({len(items)}건)")
        for item in items[:3]:
            branch.add(f"[dim]{item}[/dim]")
        if len(items) > 3:
            branch.add(f"[dim]... 외 {len(items) - 3}건[/dim]")
    console.print(tree)


def print_stat_columns(*panels: Panel) -> None:
    """Panel들을 동일 너비 컬럼으로 나란히 출력

    Args:
        *panels: Rich Panel 인스턴스들

    Example:
        from rich.panel import Panel
        print_stat_columns(
            Panel("10개", title="성공"),
            Panel("2개", title="실패"),
        )
    """
    console.print(RichColumns(list(panels), expand=True, equal=True))


def print_execution_summary(
    tool_name: str,
    profile: str = "",
    regions: list[str] | None = None,
    accounts: int = 0,
) -> None:
    """실행 요약 박스 출력

    Args:
        tool_name: 도구 이름
        profile: 프로파일 이름
        regions: 리전 목록
        accounts: 계정 수
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=12)
    table.add_column()
    table.add_row(t("runner.summary_tool") if t("runner.summary_tool") != "runner.summary_tool" else "도구", f"[bold]{tool_name}[/bold]")
    if profile:
        table.add_row("프로필", profile)
    if regions:
        table.add_row("리전", ", ".join(regions) if len(regions) <= 3 else f"{len(regions)}개 리전")
    if accounts > 0:
        table.add_row("계정", f"{accounts}개")
    console.print(Panel(table, title="실행 요약", border_style="#FF9900"))


def print_results_json(data: list[dict], pretty: bool = True) -> None:
    """JSON 형식으로 데이터 출력 (Rich syntax highlighting)

    Args:
        data: 출력할 데이터 (dict 리스트)
        pretty: 들여쓰기 여부 (기본: True)
    """
    import json

    json_str = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None, default=str)
    console.print_json(json_str)


# =============================================================================
# 키 입력 대기
# =============================================================================


def wait_for_any_key(prompt: str | None = None) -> None:
    """아무 키나 누르면 진행 (Enter 불필요)

    크로스 플랫폼 지원:
    - Windows: msvcrt.getwch() 사용
    - Unix/Mac: termios로 터미널 raw 모드 설정 후 단일 문자 읽기

    Args:
        prompt: 표시할 프롬프트 메시지

    Note:
        입력된 키 값은 사용되지 않고 즉시 버려집니다.
        보안상 입력 인젝션이나 버퍼 오버플로우 위험이 없습니다.
    """
    if prompt is None:
        prompt = f"[dim]{t('common.press_any_key_to_return')}[/dim]"
    console.print(prompt, end="")

    try:
        if sys.platform == "win32":
            # Windows: msvcrt 사용
            import msvcrt

            msvcrt.getwch()  # 단일 와이드 문자 읽기 (에코 없음)
        else:
            # Unix/Mac: termios 사용
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)  # 단일 문자 읽기
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        # fallback: 일반 input() 사용 (Enter 필요) - tty not available
        console.input("")
        return

    console.print()  # 줄바꿈
