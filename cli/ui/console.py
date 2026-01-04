"""
aa_cli/aa/ui/console.py - Rich 콘솔 유틸리티

일관된 콘솔 출력을 위한 함수들
"""

import logging
import platform
import sys

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
from rich.table import Table

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


def print_success(message: str) -> None:
    """성공 메시지 출력 (초록색 체크마크)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[green]✅ {message}[/green]")


def print_error(message: str) -> None:
    """에러 메시지 출력 (빨간색 X)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[red]❌ {message}[/red]")


def print_warning(message: str) -> None:
    """경고 메시지 출력 (노란색 경고)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def print_info(message: str) -> None:
    """정보 메시지 출력 (파란색 정보)

    Args:
        message: 출력할 메시지
    """
    console.print(f"[blue]ℹ️  {message}[/blue]")


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
        "yellow": "노란색",
        "red": "빨간색",
        "green": "초록색",
        "blue": "파란색",
        "cyan": "청록색",
        "magenta": "보라색",
        "orange": "주황색",
        "gray": "회색",
        "dim": "회색",
    }

    legend_parts = []
    for color, description in items:
        color_name = color_names.get(color, color)
        legend_parts.append(f"[{color}]{color_name}[/{color}] = {description}")

    legend_text = ", ".join(legend_parts)
    console.print(f"[dim]색상 범례: {legend_text}[/dim]")


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
    console.print("[dim]" + "─" * 50 + "[/]")


def print_tool_complete(message: str = "완료", elapsed: float | None = None) -> None:
    """도구 실행 완료 표시

    Args:
        message: 완료 메시지
        elapsed: 소요 시간 (초)
    """
    console.print()
    console.print("[dim]" + "─" * 50 + "[/]")
    if elapsed:
        console.print(f"[green]✓ {message}[/] [dim]({elapsed:.1f}s)[/]")
    else:
        console.print(f"[green]✓ {message}[/]")


# =============================================================================
# 키 입력 대기
# =============================================================================


def wait_for_any_key(prompt: str = "[dim]아무 키나 눌러 돌아가기...[/dim]") -> None:
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
        # fallback: 일반 input() 사용 (Enter 필요)
        console.input("")
        return

    console.print()  # 줄바꿈
