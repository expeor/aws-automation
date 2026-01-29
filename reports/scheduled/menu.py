"""
reports/scheduled/menu.py - 정기 작업 메뉴 UI

기능:
- 주기별 작업 목록 표시 (collapsed/expanded)
- 실행 이력 조회 (h)
- 다음 실행 예정일 표시
- 검색/필터 (/, p)
- 일괄 선택 실행 (1,2,3 또는 1-5)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from cli.i18n import get_lang, t
from cli.ui.console import clear_screen

from .history import ScheduledRunHistory
from .registry import (
    get_schedule_groups,
    list_available_companies,
    load_config,
    resolve_company,
)
from .schedule import format_next_run_date, get_next_run_date
from .types import PERMISSION_COLORS, ScheduledTask, ScheduleGroup

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext


def run(ctx: ExecutionContext) -> None:
    """정기 작업 메뉴 실행 (도구 엔트리포인트)

    Args:
        ctx: 실행 컨텍스트 (사용되지 않음 - 메뉴 전용)
    """
    from cli.flow import create_flow_runner

    console = Console()
    lang = get_lang()

    action, tasks = show_scheduled_menu(console, lang)

    if action == "run" and tasks:
        # 단일 작업 또는 일괄 작업 실행
        runner = create_flow_runner()
        history = ScheduledRunHistory()
        current_company = resolve_company(None)

        for task in tasks:
            # tool_ref에서 category/module 분리하여 실행
            parts = task.tool_ref.split("/")
            if len(parts) >= 2:
                category = parts[0]
                module = "/".join(parts[1:])  # 서브모듈 지원

                start_time = time.time()
                try:
                    runner.run_tool_directly(category, module)
                    duration = time.time() - start_time
                    history.add(
                        task_id=task.id,
                        task_name=task.name,
                        company=current_company,
                        status="success",
                        duration_sec=duration,
                    )
                except Exception as e:
                    duration = time.time() - start_time
                    history.add(
                        task_id=task.id,
                        task_name=task.name,
                        company=current_company,
                        status="failed",
                        duration_sec=duration,
                        error_msg=str(e),
                    )


def show_scheduled_menu(
    console: Console, lang: str = "ko", company: str | None = None
) -> tuple[str, list[ScheduledTask]]:
    """정기 작업 메뉴 표시

    Args:
        console: Rich Console 인스턴스
        lang: 언어 설정 ("ko" 또는 "en")
        company: 회사명 (None이면 환경변수 → default)

    Returns:
        (action, selected_tasks) - action: "run", "back", "exit"
    """
    current_company = resolve_company(company)
    view_mode = "expanded"  # "collapsed" | "expanded"
    permission_filter: str | None = None  # None = 전체, "read"/"write"/"delete"

    while True:
        groups = get_schedule_groups(company=current_company, lang=lang)
        config = load_config(company=current_company)
        company_display = config.get("company_name" if lang == "ko" else "company_name_en", current_company)

        clear_screen()
        console.print()

        # 회사명 표시
        console.print(f"[dim]📁 {t('menu.current_config')}: [cyan]{company_display}[/cyan][/dim]")
        console.print()

        if view_mode == "collapsed":
            # Collapsed 뷰: 주기별 그룹 테이블 + 다음 실행일
            result = _render_collapsed_view(console, groups, lang)
        else:
            # Expanded 뷰: 모든 작업을 트리 형태로 표시
            result = _render_expanded_view(console, groups, lang, permission_filter)

        if result:
            return result

        # 도움말 표시
        _print_help_footer(console, permission_filter)

        choice = console.input("> ").strip()

        if choice == "0" or choice.lower() == "q":
            return ("back", [])

        if choice.lower() == "e":
            view_mode = "collapsed" if view_mode == "expanded" else "expanded"
            continue

        if choice.lower() == "c":
            new_config = _show_config_selector(console, current_company, lang)
            if new_config:
                current_company = new_config
            continue

        if choice.lower() == "h":
            _show_history_view(console, lang)
            continue

        if choice.lower() == "p":
            permission_filter = _toggle_permission_filter(console, permission_filter, lang)
            continue

        if choice == "/":
            search_result = _show_search_view(console, groups, lang)
            if search_result:
                return search_result
            continue

        # 일괄 선택 처리 (1,2,3 또는 1-5 또는 1 2 3)
        if view_mode == "collapsed":
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(groups):
                    result = _show_group_tasks(console, groups[idx - 1], lang)
                    if result[0] == "run":
                        return result
        else:
            # Expanded 모드: 다중 선택 지원
            task_map = _build_task_index_map(groups, permission_filter)
            indices = _parse_multi_selection(choice, len(task_map))

            if indices:
                selected_tasks = [task_map[idx] for idx in indices if idx in task_map]
                if selected_tasks:
                    # 실행 확인
                    result = _confirm_and_run_tasks(console, selected_tasks, lang)
                    if result:
                        return result

    return ("back", [])


def _parse_multi_selection(selection: str, max_count: int) -> list[int]:
    """선택 문자열 파싱 (1 2 3, 1,2,3, 1-3 지원)

    Args:
        selection: 사용자 입력 문자열
        max_count: 최대 유효 번호

    Returns:
        선택된 인덱스 목록 (1-based)
    """
    result = set()
    selection = selection.strip()

    parts = selection.replace(",", " ").split()

    for part in parts:
        if "-" in part and not part.startswith("-"):
            try:
                start_str, end_str = part.split("-", 1)
                start_int, end_int = int(start_str), int(end_str)
                for i in range(start_int, end_int + 1):
                    if 1 <= i <= max_count:
                        result.add(i)
            except ValueError:
                continue
        else:
            try:
                num = int(part)
                if 1 <= num <= max_count:
                    result.add(num)
            except ValueError:
                continue

    return sorted(result)


def _confirm_and_run_tasks(
    console: Console, tasks: list[ScheduledTask], lang: str
) -> tuple[str, list[ScheduledTask]] | None:
    """작업 실행 확인

    Args:
        console: Rich Console
        tasks: 선택된 작업 목록
        lang: 언어

    Returns:
        ("run", tasks) 또는 None (취소 시)
    """
    console.print()
    console.print(f"[bold]{t('menu.selected_tasks')} ({len(tasks)}{t('menu.count_suffix', count='')}):[/bold]")

    has_delete = False
    for task in tasks:
        name = task.name if lang == "ko" else task.name_en
        perm_color = PERMISSION_COLORS.get(task.permission, "dim")
        console.print(f"  - {name} ([{perm_color}]{task.permission}[/{perm_color}])")
        if task.permission == "delete":
            has_delete = True

    console.print()

    # delete 작업이 있으면 개별 확인
    if has_delete:
        console.print(f"[red]{t('menu.delete_task_warning')}[/red]")

        # delete 작업 개별 확인
        confirmed_tasks = []
        for task in tasks:
            if task.requires_confirm:
                name = task.name if lang == "ko" else task.name_en
                confirm = (
                    console.input(f"[red]{t('menu.delete_confirm_prompt', name=name)}: [/red]")
                    .strip()
                    .lower()
                )
                if confirm == "y":
                    confirmed_tasks.append(task)
            else:
                confirmed_tasks.append(task)

        if not confirmed_tasks:
            return None
        tasks = confirmed_tasks
    else:
        # 일반 확인
        confirm = console.input(f"{t('menu.confirm_batch_run')} (y/N): ").strip().lower()
        if confirm != "y":
            return None

    return ("run", tasks)


def _render_collapsed_view(
    console: Console, groups: list[ScheduleGroup], lang: str
) -> tuple[str, list[ScheduledTask]] | None:
    """Collapsed 뷰 렌더링 - 주기별 요약 테이블 + 다음 실행일

    Args:
        console: Rich Console 인스턴스
        groups: ScheduleGroup 목록
        lang: 언어 설정

    Returns:
        None (렌더링만 수행)
    """
    history = ScheduledRunHistory()

    table = Table(
        title=f"[bold]{t('menu.scheduled_operations')}[/bold]",
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 1),
        title_justify="left",
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column(t("menu.header_cycle"), width=24)
    table.add_column("[green]" + t("menu.task_check") + "[/green]", width=4, justify="right")
    table.add_column("[yellow]" + t("menu.task_apply") + "[/yellow]", width=4, justify="right")
    table.add_column("[red]" + t("menu.task_cleanup") + "[/red]", width=4, justify="right")

    for i, group in enumerate(groups, 1):
        # 다음 실행일 계산 (그룹 내 첫 번째 작업 기준)
        next_run_info = ""
        if group.tasks:
            first_task = group.tasks[0]
            last_run_record = history.get_last_run(first_task.id)
            last_run = None
            if last_run_record:
                import contextlib
                from datetime import datetime

                with contextlib.suppress(ValueError, TypeError):
                    last_run = datetime.fromisoformat(last_run_record.run_at)
            next_run = get_next_run_date(group.cycle, last_run)
            next_run_str = format_next_run_date(next_run, lang)
            next_label = t("menu.next_run") if lang == "ko" else "Next"
            next_run_info = f" [dim]({next_label}: {next_run_str})[/dim]"

        table.add_row(
            str(i),
            f"[{group.color}]{group.icon} {group.display_name}[/{group.color}]{next_run_info}",
            str(group.read_count) if group.read_count else "-",
            str(group.write_count) if group.write_count else "-",
            str(group.delete_count) if group.delete_count else "-",
        )

    console.print(table)
    console.print()
    return None


def _render_expanded_view(
    console: Console,
    groups: list[ScheduleGroup],
    lang: str,
    permission_filter: str | None = None,
) -> tuple[str, list[ScheduledTask]] | None:
    """Expanded 뷰 렌더링 - 모든 주기의 작업을 트리 형태로 표시

    Args:
        console: Rich Console 인스턴스
        groups: ScheduleGroup 목록
        lang: 언어 설정
        permission_filter: 권한 필터 (None이면 전체)

    Returns:
        None (렌더링만 수행)
    """
    title = f"[bold]{t('menu.scheduled_operations')}[/bold]"
    if permission_filter:
        filter_label = t(f"menu.permission_{permission_filter}")
        title += f" [dim]({t('menu.filter_permission')}: {filter_label})[/dim]"

    tree = Tree(title)

    # 이름 컬럼 폭 계산 (가장 긴 이름 기준)
    max_name_width = 0
    for group in groups:
        for task in group.tasks:
            if permission_filter and task.permission != permission_filter:
                continue
            name = task.name if lang == "ko" else task.name_en
            max_name_width = max(max_name_width, _display_width(name))
    name_width = min(max_name_width, 24)  # 최대 24자

    current_idx = 1
    for group in groups:
        # 필터 적용 시 해당 그룹에 표시할 작업이 있는지 확인
        filtered_tasks = [
            task for task in group.tasks if not permission_filter or task.permission == permission_filter
        ]
        if not filtered_tasks:
            continue

        branch = tree.add(f"[{group.color}]{group.icon} {group.display_name}[/{group.color}]")
        for task in filtered_tasks:
            perm_color = PERMISSION_COLORS.get(task.permission, "dim")
            name = task.name if lang == "ko" else task.name_en
            desc = task.description if lang == "ko" else task.description_en
            # 인덱스 패딩 (2자리)
            idx_str = f"[{current_idx}]".rjust(4)
            # 이름 패딩 (한글 폭 고려)
            name_padded = _pad_to_width(name, name_width)
            branch.add(
                f"[dim]{idx_str}[/dim] [{perm_color}]{task.permission:6}[/{perm_color}] {name_padded}  [dim]{desc[:40]}[/dim]"
            )
            current_idx += 1

    console.print(tree)
    console.print()
    return None


def _print_help_footer(console: Console, permission_filter: str | None) -> None:
    """도움말 푸터 출력"""
    # 권한 범례
    console.print(
        f"[dim]{t('menu.permission_legend')}: "
        f"[green]● {t('menu.task_check')}(read)[/green] "
        f"[yellow]● {t('menu.task_apply')}(write)[/yellow] "
        f"[red]● {t('menu.task_cleanup')}(delete)[/red][/dim]"
    )

    # 단축키
    console.print(
        f"[dim]e: {t('menu.toggle_expand')}  "
        f"/: {t('menu.search_tasks')}  "
        f"p: {t('menu.filter_permission')}  "
        f"h: {t('menu.run_history')}  "
        f"c: {t('menu.change_config')}[/dim]"
    )

    # 돌아가기
    console.print(f"[dim]0: {t('menu.go_back')}[/dim]")


def _display_width(text: str) -> int:
    """문자열의 터미널 표시 폭 계산 (East Asian Width 기준)"""
    import unicodedata

    width = 0
    for char in text:
        ea_width = unicodedata.east_asian_width(char)
        if ea_width in ("F", "W"):  # Fullwidth, Wide (한글, 한자 등)
            width += 2
        else:  # Na, H, N, A (영문, 기호, 화살표 등)
            width += 1
    return width


def _pad_to_width(text: str, target_width: int) -> str:
    """문자열을 목표 폭에 맞게 공백 패딩"""
    current_width = _display_width(text)
    if current_width >= target_width:
        return text
    return text + " " * (target_width - current_width)


def _build_task_index_map(
    groups: list[ScheduleGroup], permission_filter: str | None = None
) -> dict[int, ScheduledTask]:
    """전역 인덱스 → 작업 매핑 딕셔너리 생성

    Args:
        groups: ScheduleGroup 목록
        permission_filter: 권한 필터 (None이면 전체)

    Returns:
        인덱스 → ScheduledTask 매핑
    """
    task_map: dict[int, ScheduledTask] = {}
    current_idx = 1
    for group in groups:
        for task in group.tasks:
            if permission_filter and task.permission != permission_filter:
                continue
            task_map[current_idx] = task
            current_idx += 1
    return task_map


def _show_config_selector(console: Console, current: str, lang: str) -> str | None:
    """설정 프로필 선택 메뉴

    Args:
        console: Rich Console 인스턴스
        current: 현재 선택된 설정
        lang: 언어 설정

    Returns:
        선택된 설정명 또는 None (취소)
    """
    configs = list_available_companies()

    if len(configs) <= 1:
        console.print(f"\n[yellow]{t('menu.no_other_configs')}[/yellow]")
        console.input(f"[dim]{t('menu.press_any_key')}[/dim]")
        return None

    clear_screen()
    console.print()
    console.print(f"[bold]{t('menu.select_config')}[/bold]")
    console.print()

    for i, cfg in enumerate(configs, 1):
        config = load_config(company=cfg)
        display_name = config.get(
            "config_name" if lang == "ko" else "config_name_en",
            config.get("company_name" if lang == "ko" else "company_name_en", cfg),
        )
        marker = " [cyan]◀[/cyan]" if cfg == current else ""
        console.print(f"  [dim]{i}[/dim] {display_name} [dim]({cfg})[/dim]{marker}")

    console.print()
    console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

    choice = console.input("> ").strip()

    if choice == "0" or choice.lower() == "q":
        return None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(configs):
            return configs[idx - 1]

    return None


def _toggle_permission_filter(console: Console, current: str | None, lang: str) -> str | None:
    """권한 필터 토글

    Args:
        console: Rich Console
        current: 현재 필터 (None이면 전체)
        lang: 언어

    Returns:
        새 필터 값 또는 None (전체)
    """
    console.print()
    console.print(f"[bold]{t('menu.filter_permission')}[/bold]")
    console.print(f"  [dim]0[/dim] {t('menu.filter_all')}" + (" [cyan]◀[/cyan]" if current is None else ""))
    console.print("  [dim]1[/dim] [green]read[/green]" + (" [cyan]◀[/cyan]" if current == "read" else ""))
    console.print("  [dim]2[/dim] [yellow]write[/yellow]" + (" [cyan]◀[/cyan]" if current == "write" else ""))
    console.print("  [dim]3[/dim] [red]delete[/red]" + (" [cyan]◀[/cyan]" if current == "delete" else ""))

    choice = console.input("> ").strip()

    filter_map = {"0": None, "1": "read", "2": "write", "3": "delete"}
    return filter_map.get(choice, current)


def _show_history_view(console: Console, lang: str) -> None:
    """실행 이력 표시

    Args:
        console: Rich Console
        lang: 언어
    """
    history = ScheduledRunHistory()
    records = history.get_recent(limit=10)

    clear_screen()
    console.print()
    console.print(f"[bold]{t('menu.run_history')}[/bold]")
    console.print()

    if not records:
        console.print(f"[dim]{t('menu.no_history')}[/dim]")
    else:
        table = Table(
            title=f"{t('menu.recent_runs')} ({len(records)}{t('menu.count_suffix', count='')})",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column(t("menu.header_datetime"), width=12)
        table.add_column(t("menu.header_name"), width=24)
        table.add_column(t("menu.header_status"), width=6, justify="center")
        table.add_column(t("menu.header_duration"), width=8, justify="right")

        for i, record in enumerate(records, 1):
            status_icon = "✓" if record.status == "success" else "✗"
            status_color = "green" if record.status == "success" else "red"
            duration = record.get_duration_display()

            table.add_row(
                str(i),
                record.get_formatted_datetime(),
                record.task_name[:22],
                f"[{status_color}]{status_icon}[/{status_color}]",
                duration,
            )

        console.print(table)

    console.print()
    console.print(f"[dim]0: {t('menu.go_back')}[/dim]")
    console.input("> ")


def _show_search_view(
    console: Console, groups: list[ScheduleGroup], lang: str
) -> tuple[str, list[ScheduledTask]] | None:
    """검색 뷰 표시

    Args:
        console: Rich Console
        groups: ScheduleGroup 목록
        lang: 언어

    Returns:
        ("run", [task]) 또는 None
    """
    console.print()
    query = console.input(f"{t('menu.search_tasks')}: ").strip().lower()

    if not query:
        return None

    # 모든 작업에서 검색
    results: list[tuple[int, ScheduledTask]] = []
    idx = 1
    for group in groups:
        for task in group.tasks:
            name = task.name if lang == "ko" else task.name_en
            desc = task.description if lang == "ko" else task.description_en
            if query in name.lower() or query in desc.lower():
                results.append((idx, task))
            idx += 1

    if not results:
        console.print(f"[yellow]{t('menu.no_search_results')}[/yellow]")
        console.input(f"[dim]{t('menu.press_any_key')}[/dim]")
        return None

    # 검색 결과 표시
    clear_screen()
    console.print()
    console.print(f"[bold]{t('common.search')}: {query}[/bold] ({len(results)}{t('menu.count_suffix', count='')})")
    console.print()

    for i, (_orig_idx, task) in enumerate(results, 1):
        name = task.name if lang == "ko" else task.name_en
        perm_color = PERMISSION_COLORS.get(task.permission, "dim")
        console.print(f"  [dim]{i}[/dim] [{perm_color}]{task.permission:6}[/{perm_color}] {name}")

    console.print()
    console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

    choice = console.input("> ").strip()

    if choice == "0" or not choice:
        return None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(results):
            _, selected = results[idx - 1]
            # 확인 필요 시
            if selected.requires_confirm:
                name = selected.name if lang == "ko" else selected.name_en
                confirm = (
                    console.input(f"[red]{t('menu.delete_confirm_prompt', name=name)}: [/red]")
                    .strip()
                    .lower()
                )
                if confirm != "y":
                    return None
            return ("run", [selected])

    return None


def _show_group_tasks(console: Console, group: ScheduleGroup, lang: str) -> tuple[str, list[ScheduledTask]]:
    """그룹 내 작업 목록 (권한별 색상 표시)

    Args:
        console: Rich Console 인스턴스
        group: ScheduleGroup 인스턴스
        lang: 언어 설정

    Returns:
        (action, selected_tasks)
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

        console.print(f"[dim]{t('menu.selection_hint')}  0: {t('menu.go_back')}[/dim]")

        choice = console.input("> ").strip()

        if choice == "0" or choice.lower() == "q":
            return ("back", [])

        # 다중 선택 지원
        indices = _parse_multi_selection(choice, len(group.tasks))
        if indices:
            selected_tasks = [group.tasks[idx - 1] for idx in indices]
            result = _confirm_and_run_tasks(console, selected_tasks, lang)
            if result:
                return result

    return ("back", [])
