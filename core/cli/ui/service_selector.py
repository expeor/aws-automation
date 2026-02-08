"""
cli/ui/service_selector.py - 서비스 선택 UI

페이지네이션, 동적 열, 키워드 검색을 지원하는 서비스 선택 메뉴
"""

from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.table import Table

from core.cli.i18n import t
from core.cli.ui.console import clear_screen


def select_service(
    console: Console,
    services: list[dict[str, Any]],
    *,
    title: str | None = None,
    page_size: int = 40,
    show_description: bool = False,
    sort_alphabetically: bool = True,
    on_select: Callable[[dict[str, Any]], Any] | None = None,
    allow_back: bool = True,
) -> dict[str, Any] | None:
    """서비스 선택 UI (페이지네이션, 동적 열, 키워드 검색 지원)

    Args:
        console: Rich Console
        services: 서비스(카테고리) 딕셔너리 리스트
        title: 테이블 제목 (기본: "서비스별")
        page_size: 페이지당 항목 수 (기본: 40)
        show_description: 설명 표시 여부 (기본: False, True면 단일 열)
        sort_alphabetically: 알파벳순 정렬 (기본: True)
        on_select: 선택 시 콜백 (None이면 선택된 서비스 반환)
        allow_back: 뒤로가기(0) 허용 여부 (기본: True)

    Returns:
        선택된 서비스 딕셔너리, 또는 None (뒤로가기/취소)
    """
    if not services:
        console.print(f"[yellow]{t('menu.no_services_available')}[/]")
        return None

    # 메뉴 항목 준비
    menu_items = []
    for svc in services:
        name = svc.get("display_name", svc.get("name", "")).upper()
        tools_count = len(svc.get("tools", []))
        desc = svc.get("description", "")[:45] if show_description else ""
        menu_items.append({"svc": svc, "name": name, "count": tools_count, "desc": desc})

    # 알파벳순 정렬
    if sort_alphabetically:
        menu_items.sort(key=lambda x: x["name"].lower())

    total_count = len(menu_items)
    total_pages = (total_count + page_size - 1) // page_size
    current_page = 1

    display_title = title or t("menu.by_service")

    while True:
        clear_screen()

        # 현재 페이지 항목
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_count)
        page_items = menu_items[start_idx:end_idx]
        page_count = len(page_items)

        # 열 수 결정 (설명 표시 시 단일 열, 아니면 동적)
        if show_description or page_count <= 14:
            num_cols = 1
        elif page_count <= 28:
            num_cols = 2
        else:
            num_cols = 3

        rows_per_col = (page_count + num_cols - 1) // num_cols

        # 테이블 생성
        console.print()
        table_title = f"[bold]{display_title}[/bold] ({t('menu.count_suffix', count=total_count)})"
        if total_pages > 1:
            table_title += f" - {t('menu.page_info', current=current_page, total=total_pages)}"

        table = Table(
            title=table_title,
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )

        # 열 추가
        if show_description:
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column(t("menu.header_service"), width=20)
            table.add_column(t("menu.header_tools"), width=5, justify="right")
            table.add_column(t("menu.header_description"), style="dim")
        else:
            for _ in range(num_cols):
                table.add_column("#", style="dim", width=4, justify="right")
                table.add_column(t("menu.header_service"), width=22)
                table.add_column(t("menu.header_tools"), width=5, justify="right")

        # 행 데이터 추가
        if show_description:
            for i, item in enumerate(page_items):
                global_idx = start_idx + i + 1
                table.add_row(str(global_idx), item["name"], str(item["count"]), item["desc"])
        else:
            for row in range(rows_per_col):
                row_data = []
                for col in range(num_cols):
                    item_idx = col * rows_per_col + row
                    if item_idx < page_count:
                        global_idx = start_idx + item_idx + 1
                        item = page_items[item_idx]
                        row_data.extend([str(global_idx), item["name"], str(item["count"])])
                    else:
                        row_data.extend(["", "", ""])
                table.add_row(*row_data)

        console.print(table)
        console.print()

        # 네비게이션 안내
        nav_parts = []
        if total_pages > 1:
            if current_page > 1:
                nav_parts.append(f"[dim]p[/dim] {t('menu.previous')}")
            if current_page < total_pages:
                nav_parts.append(f"[dim]n[/dim] {t('menu.next')}")
        if allow_back:
            nav_parts.append(f"[dim]0[/dim] {t('menu.go_back')}")
        console.print("  ".join(nav_parts))
        console.print(f"[dim]{t('menu.enter_number_or_keyword')}[/dim]")

        # 입력 처리
        choice = console.input("> ").strip()
        if not choice:
            continue

        choice_lower = choice.lower()

        # 페이지 이동
        if choice_lower == "n" and current_page < total_pages:
            current_page += 1
            continue
        elif choice_lower == "p" and current_page > 1:
            current_page -= 1
            continue
        elif choice_lower == "q" or choice == "0":
            if allow_back:
                return None
            continue

        # 숫자 입력
        try:
            num = int(choice)
            if 1 <= num <= total_count:
                selected: dict[str, Any] = menu_items[num - 1]["svc"]
                if on_select:
                    result = on_select(selected)
                    if result is False:
                        continue  # 콜백이 False 반환 시 메뉴 유지
                return selected
            console.print(f"[dim]{t('menu.range_info', min=1, max=total_count)}[/dim]")
        except ValueError:
            # 키워드 검색
            matched = _search_by_keyword(menu_items, choice)
            if matched:
                matched_svc: dict[str, Any] = matched["svc"]
                if on_select:
                    result = on_select(matched_svc)
                    if result is False:
                        continue
                return matched_svc
            console.print(f"[dim]{t('menu.no_match')}[/dim]")


def _search_by_keyword(menu_items: list[dict], keyword: str) -> dict | None:
    """키워드로 서비스 검색 (전체 페이지 대상)"""
    keyword_lower = keyword.lower()

    # 정확히 일치
    for item in menu_items:
        if item["name"].lower() == keyword_lower:
            return item

    # 시작 일치
    for item in menu_items:
        if item["name"].lower().startswith(keyword_lower):
            return item

    # 포함
    for item in menu_items:
        if keyword_lower in item["name"].lower():
            return item

    return None
