"""
reports/scheduled/menu.py - 정기 작업 메뉴 UI
"""

from rich.console import Console
from rich.table import Table

from cli.i18n import t
from cli.ui.console import clear_screen

from .registry import get_schedule_groups
from .types import PERMISSION_COLORS, ScheduledTask, ScheduleGroup


def show_scheduled_menu(console: Console, lang: str = "ko") -> tuple[str, ScheduledTask | None]:
    """정기 작업 메뉴 표시

    Args:
        console: Rich Console 인스턴스
        lang: 언어 설정 ("ko" 또는 "en")

    Returns:
        (action, selected_task) - action: "run", "back", "exit"
    """
    groups = get_schedule_groups(lang=lang)

    while True:
        clear_screen()
        console.print()

        # 주기별 그룹 테이블 (권한별 개수 표시)
        table = Table(
            title=f"[bold]{t('menu.scheduled_operations')}[/bold]",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column(t("menu.header_cycle"), width=16)
        table.add_column("[green]" + t("menu.task_check") + "[/green]", width=4, justify="right")
        table.add_column("[yellow]" + t("menu.task_apply") + "[/yellow]", width=4, justify="right")
        table.add_column("[red]" + t("menu.task_cleanup") + "[/red]", width=4, justify="right")

        for i, group in enumerate(groups, 1):
            table.add_row(
                str(i),
                f"[{group.color}]{group.icon} {group.display_name}[/{group.color}]",
                str(group.read_count) if group.read_count else "-",
                str(group.write_count) if group.write_count else "-",
                str(group.delete_count) if group.delete_count else "-",
            )

        console.print(table)
        console.print()
        console.print(
            f"[dim]{t('menu.permission_legend')}: "
            f"[green]●{t('menu.task_check')}(read)[/green] "
            f"[yellow]●{t('menu.task_apply')}(write)[/yellow] "
            f"[red]●{t('menu.task_cleanup')}(delete)[/red][/dim]"
        )
        console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

        choice = console.input("> ").strip()

        if choice == "0" or choice.lower() == "q":
            return ("back", None)

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(groups):
                result = _show_group_tasks(console, groups[idx - 1], lang)
                if result[0] == "run":
                    return result

    return ("back", None)


def _show_group_tasks(console: Console, group: ScheduleGroup, lang: str) -> tuple[str, ScheduledTask | None]:
    """그룹 내 작업 목록 (권한별 색상 표시)

    Args:
        console: Rich Console 인스턴스
        group: ScheduleGroup 인스턴스
        lang: 언어 설정

    Returns:
        (action, selected_task)
    """
    while True:
        clear_screen()
        console.print()

        table = Table(
            title=f"[bold][{group.color}]{group.icon} {group.display_name}[/{group.color}][/bold]",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("ID", width=8)
        table.add_column(t("menu.header_permission"), width=6)
        table.add_column(t("menu.header_name"), width=26)
        table.add_column(t("menu.header_description"), style="dim")

        for i, task in enumerate(group.tasks, 1):
            name = task.name if lang == "ko" else task.name_en
            desc = task.description if lang == "ko" else task.description_en
            perm_color = PERMISSION_COLORS.get(task.permission, "dim")
            table.add_row(
                str(i),
                task.id,
                f"[{perm_color}]{task.permission}[/{perm_color}]",
                name,
                desc[:45],
            )

        console.print(table)
        console.print()

        # delete 작업 경고
        if group.delete_count > 0:
            console.print(f"[red]{t('menu.delete_task_warning')}[/red]")

        console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

        choice = console.input("> ").strip()

        if choice == "0" or choice.lower() == "q":
            return ("back", None)

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(group.tasks):
                selected = group.tasks[idx - 1]

                # delete 작업 확인
                if selected.requires_confirm:
                    console.print()
                    confirm = (
                        console.input(f"[red]{t('menu.delete_confirm_prompt', name=selected.name)}: [/red]")
                        .strip()
                        .lower()
                    )
                    if confirm != "y":
                        continue

                return ("run", selected)

    return ("back", None)
