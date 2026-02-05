"""
cli/ui/banner.py - ASCII 아트 배너 및 컨텍스트 표시

화려한 ASCII 아트와 현재 설정 정보 표시
"""

import logging
from pathlib import Path

from rich.console import Console

from cli.i18n import t

logger = logging.getLogger(__name__)


def get_tool_count() -> int:
    """전체 도구 수 반환"""
    try:
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True)
        return sum(len(cat.get("tools", [])) for cat in categories)
    except Exception:
        return 65  # fallback


def get_version() -> str:
    """버전 문자열 반환"""
    try:
        current = Path(__file__).resolve()
        candidate_dirs = [
            current.parent.parent.parent,  # cli/ui/banner.py → project root
        ]
        for base in candidate_dirs:
            version_file = base / "version.txt"
            if version_file.exists():
                with open(version_file, encoding="utf-8") as f:
                    return f.read().strip()
    except Exception as e:
        logger.debug("Failed to read version file: %s", e)
    return "0.0.1"


# 컴팩트한 배너 (ASCII 호환)
# (style, ascii_art, suffix) 형식
COMPACT_LOGO_LINES: list[tuple[str, str, str]] = [
    ("#FF9900", "    /\\  /\\", "    [bold white]AWS Automation CLI[/] [dim]v{version}[/]"),
    ("#FF9900", "   /  \\/  \\", "   {context}"),
    ("#CC7700", "  / /\\  /\\ \\", ""),
    ("#995500", " /_/  \\/  \\_\\", "  [dim]{hint}[/]"),
]

# 풀 배너 (메인 메뉴용, ASCII 호환)
# (style, ascii_art, suffix) 형식
FULL_LOGO_LINES: list[tuple[str, str, str]] = [
    ("#FF9900", "    /\\      /\\", ""),
    ("#FF9900", "   /  \\    /  \\", "     [bold white]AWS Automation CLI[/]  [dim]v{version}[/]"),
    ("#CC7700", "  / /\\ \\  / /\\ \\", "    [dim cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"),
    ("#CC7700", " / ____ \\/ ____ \\", "   [cyan]⚡ {tool_count}+ Tools Ready[/]"),
    ("#995500", "/_/    \\_\\/    \\_\\", ""),
]


def get_current_context() -> str:
    """현재 AWS 컨텍스트 정보 반환"""
    try:
        from core.auth import get_current_context_info

        info = get_current_context_info()
        if info:
            mode = info.get("mode", "")
            profile = info.get("profile", "")
            if mode == "multi":
                return f"[cyan]Multi-Account[/] [dim]|[/] [white]{profile}[/]"
            elif mode == "single":
                return f"[green]Single[/] [dim]|[/] [white]{profile}[/]"
            elif profile:
                return f"[white]{profile}[/]"
    except Exception as e:
        logger.debug("Failed to get current context: %s", e)
    return f"[dim]{t('common.profile_not_set')}[/]"


def _render_logo_lines(console: Console, lines: list[tuple[str, str, str]], format_vars: dict[str, str]) -> None:
    """로고 라인 렌더링 (백슬래시 이스케이프 처리)"""
    from rich.text import Text

    for color, ascii_art, suffix in lines:
        text = Text()
        text.append(ascii_art, style=f"bold {color}")
        if suffix:
            formatted_suffix = suffix.format(**format_vars)
            # Rich 마크업이 포함된 suffix는 console.print로 출력
            console.print(text, formatted_suffix, end="")
            console.print()
        else:
            console.print(text)


def print_banner(console: Console, compact: bool = False) -> None:
    """배너 출력

    Args:
        console: Rich Console 인스턴스
        compact: True면 간소화된 배너
    """
    console.print()
    if compact:
        format_vars = {
            "version": get_version(),
            "context": get_current_context(),
            "hint": t("common.help_quit_hint"),
        }
        _render_logo_lines(console, COMPACT_LOGO_LINES, format_vars)
    else:
        format_vars = {"tool_count": str(get_tool_count()), "version": get_version()}
        _render_logo_lines(console, FULL_LOGO_LINES, format_vars)
    console.print()


def print_simple_banner(console: Console) -> None:
    """간단한 배너 출력 (서브 메뉴용)"""
    version = get_version()
    context = get_current_context()
    console.print()
    console.print(f"[bold #FF9900]AA[/] [dim]v{version}[/] [dim]|[/] {context}")
    console.print()
