"""
cli/ui/banner.py - ASCII 아트 배너 및 컨텍스트 표시

화려한 ASCII 아트와 현재 설정 정보 표시
"""

from pathlib import Path

from rich.console import Console

from cli.i18n import t


def get_version() -> str:
    """버전 문자열 반환"""
    try:
        current = Path(__file__).resolve()
        candidate_dirs = [
            current.parent.parent.parent.parent,  # project root
        ]
        for base in candidate_dirs:
            version_file = base / "version.txt"
            if version_file.exists():
                with open(version_file, encoding="utf-8") as f:
                    return f.read().strip()
    except Exception:
        pass
    return "0.0.1"


# 컴팩트한 배너 (ASCII 호환)
COMPACT_LOGO = """
[bold #FF9900]  AA   AA [/]    [bold white]AWS Automation CLI[/] [dim]v{version}[/]
[bold #FF9900] A  A A  A[/]   {context}
[bold #CC7700] AAAA AAAA[/]
[bold #CC7700] A  A A  A[/]   [dim]{hint}[/]
[bold #995500] A  A A  A[/]
"""

# 풀 배너 (메인 메뉴용, ASCII 호환)
FULL_LOGO = """
[bold #FF9900]  AA   AA [/]
[bold #FF9900] A  A A  A[/]   [bold white]AWS Automation CLI[/]
[bold #CC7700] AAAA AAAA[/]   [dim]v{version}[/]
[bold #CC7700] A  A A  A[/]
[bold #995500] A  A A  A[/]
"""


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
    except Exception:
        pass
    return f"[dim]{t('common.profile_not_set')}[/]"


def print_banner(console: Console, compact: bool = False) -> None:
    """배너 출력

    Args:
        console: Rich Console 인스턴스
        compact: True면 간소화된 배너
    """
    version = get_version()
    context = get_current_context()
    hint = t("common.help_quit_hint")

    if compact:
        logo = COMPACT_LOGO.format(version=version, context=context, hint=hint)
    else:
        logo = FULL_LOGO.format(version=version)

    console.print()
    for line in logo.strip().split("\n"):
        console.print(line)
    console.print()


def print_simple_banner(console: Console) -> None:
    """간단한 배너 출력 (서브 메뉴용)"""
    version = get_version()
    context = get_current_context()
    console.print()
    console.print(f"[bold #FF9900]AA[/] [dim]v{version}[/] [dim]|[/] {context}")
    console.print()
