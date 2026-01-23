# internal/flow/steps/category.py
"""
카테고리/도구 선택 Step

discovery 기반으로 자동 발견된 카테고리/도구 표시.
menu.py 의존성 제거됨.
"""

from typing import Any

from rich.console import Console
from rich.table import Table

from cli.i18n import get_lang, t
from cli.ui.console import clear_screen, print_box_end, print_box_line, print_box_start
from core.tools.types import AREA_DISPLAY_BY_KEY as AREA_DISPLAY

from ..context import ExecutionContext, ToolInfo

console = Console()

# 권한별 색상 (ANSI)
PERMISSION_COLORS = {
    "read": "green",  # 안전 - 조회만
    "write": "yellow",  # 주의 - 변경
    "create": "yellow",
    "update": "yellow",
    "delete": "red",  # 위험 - 삭제
}


def _load_categories() -> list[dict[str, Any]]:
    """discovery 기반 카테고리 로드 (AWS 서비스 포함)"""
    try:
        from core.tools.discovery import discover_categories

        return discover_categories(include_aws_services=True)
    except ImportError as e:
        console.print(f"[red]! {t('flow.discovery_load_failed', error=str(e))}[/red]")
        return []


def _convert_to_tool_info(tool: dict, category_name: str) -> ToolInfo:
    """dict를 ToolInfo로 변환

    Note:
        플러그인 메타데이터에서는 `single_region_only`, `single_account_only` 사용
        ToolInfo에서는 `supports_single_region_only`, `supports_single_account_only` 사용
    """
    return ToolInfo(
        name=tool["name"],
        description=tool.get("description", ""),
        category=category_name,
        permission=tool.get("permission", "read"),
        # 플러그인 메타데이터 키와 ToolInfo 키 매핑
        supports_single_region_only=tool.get("single_region_only", False),
        supports_single_account_only=tool.get("single_account_only", False),
        is_global=tool.get("is_global", False),
    )


class CategoryStep:
    """카테고리/도구 선택 Step (discovery 기반)

    entry_point에 따라:
    - None: 전체 카테고리 메뉴 표시
    - "ebs": EBS 카테고리의 도구 목록 표시
    """

    def execute(
        self,
        ctx: ExecutionContext,
        entry_point: str | None = None,
    ) -> ExecutionContext:
        """카테고리/도구 선택 실행"""
        categories = _load_categories()

        if not categories:
            console.print(f"[red]! {t('flow.no_tools_registered')}[/red]")
            console.print(f"[yellow]* {t('flow.add_tools_hint')}[/yellow]")
            raise RuntimeError(t('flow.no_tools_registered'))

        if entry_point:
            # 특정 카테고리로 진입 (aa ebs 등)
            category = self._find_category(categories, entry_point)
            if not category:
                console.print(f"[red]! {t('flow.category_not_found', name=entry_point)}[/red]")
                raise ValueError(f"Unknown category: {entry_point}")

            # 도구 선택 (이전 메뉴 시 전체 메뉴로)
            while True:
                ctx.category = category["name"]
                # sub_services가 있고 이미 필터링되지 않은 경우 서브메뉴 표시
                display_category = self._apply_sub_service_menu(category)
                if display_category is None:
                    # 이전 메뉴 선택
                    category = self._select_category(categories)
                    continue
                tool = self._select_tool(display_category)
                if tool is not None:
                    break
                # 이전 메뉴 선택 시 전체 카테고리 메뉴로
                category = self._select_category(categories)
        else:
            # 전체 카테고리 메뉴 (이전 메뉴 루프)
            while True:
                category = self._select_category(categories)
                ctx.category = category["name"]
                # sub_services가 있으면 서브메뉴 표시
                display_category = self._apply_sub_service_menu(category)
                if display_category is None:
                    # 이전 메뉴 선택 시 카테고리 선택으로 돌아감
                    continue
                tool = self._select_tool(display_category)
                if tool is not None:
                    break
                # 이전 메뉴 선택 시 카테고리 선택으로 돌아감

        ctx.tool = _convert_to_tool_info(tool, category["name"])
        return ctx

    def _apply_sub_service_menu(self, category: dict) -> dict | None:
        """sub_services가 있으면 서브메뉴 표시, 없으면 원본 반환

        Returns:
            선택된 카테고리 (필터링됨), 또는 None (이전 메뉴)
        """
        sub_services = category.get("sub_services", [])

        # sub_services가 없거나 이미 필터링된 경우 (CLI에서 직접 aa alb 실행)
        if not sub_services or category.get("_sub_service_filter"):
            return category

        # 도구가 있는 sub_service만 필터링
        tools = category.get("tools", [])
        sub_svc_with_tools = []
        for sub_svc in sub_services:
            count = len([t for t in tools if t.get("sub_service") == sub_svc])
            if count > 0:
                sub_svc_with_tools.append((sub_svc, count))

        # sub_service에 도구가 하나도 없으면 서브메뉴 스킵
        if not sub_svc_with_tools:
            return category

        return self._select_sub_service(category, sub_svc_with_tools)

    def _find_category(self, categories: list[dict], name: str) -> dict | None:
        """이름, 별칭, 또는 하위 서비스명으로 카테고리 검색

        하위 서비스명으로 검색 시 해당 sub_service 도구만 필터링됨.
        예: "alb" → elb 카테고리 + sub_service=="alb"인 도구만
        """
        from core.tools.discovery import resolve_category

        return resolve_category(name)

    def _select_sub_service(self, category: dict, sub_svc_with_tools: list[tuple]) -> dict | None:
        """하위 서비스 선택 UI

        Args:
            category: 원본 카테고리
            sub_svc_with_tools: [(sub_service_name, tool_count), ...]

        Returns:
            선택된 카테고리 (필터링됨), 또는 None (이전 메뉴)
        """
        display_name = category.get("display_name", category["name"]).upper()
        tools = category.get("tools", [])

        # 공통 도구 수 (sub_service 미지정)
        common_count = len([tool for tool in tools if not tool.get("sub_service")])

        console.print()
        print_box_start(f"{display_name} {t('menu.sub_services')}")

        # 전체 옵션
        total_count = len(tools)
        print_box_line(f" [cyan]1[/cyan]  {t('menu.all_items')} ({t('menu.count_suffix', count=total_count)})")

        # 공통 도구가 있으면 표시
        if common_count > 0:
            print_box_line(f" [cyan]2[/cyan]  {t('menu.common_items')} ({t('menu.count_suffix', count=common_count)})")
            offset = 2
        else:
            offset = 1

        # 하위 서비스 옵션
        for i, (sub_svc, count) in enumerate(sub_svc_with_tools, offset + 1):
            print_box_line(f" [cyan]{i}[/cyan]  {sub_svc.upper()} ({t('menu.count_suffix', count=count)})")

        print_box_line()
        print_box_line(f" [dim]0[/dim] {t('menu.go_back')}")
        print_box_end()

        max_choice = offset + len(sub_svc_with_tools)

        while True:
            choice = console.input("> ").strip()
            if not choice:
                continue

            try:
                num = int(choice)
                if num == 0:
                    return None  # 이전 메뉴

                if num == 1:
                    # 전체 선택 → 원본 그대로
                    return category

                if common_count > 0 and num == 2:
                    # 공통만 선택 → sub_service 없는 도구만
                    filtered = category.copy()
                    filtered["tools"] = [t for t in tools if not t.get("sub_service")]
                    filtered["_sub_service_filter"] = "_common"
                    return filtered

                # 하위 서비스 선택
                sub_idx = num - offset - 1
                if 0 <= sub_idx < len(sub_svc_with_tools):
                    selected_sub_svc = sub_svc_with_tools[sub_idx][0]
                    filtered = category.copy()
                    filtered["tools"] = [t for t in tools if t.get("sub_service") == selected_sub_svc]
                    filtered["_sub_service_filter"] = selected_sub_svc
                    return filtered

                console.print(f"[dim]{t('menu.range_info', min=0, max=max_choice)}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('menu.enter_number')}[/dim]")

    def _select_category(self, categories: list[dict]) -> dict:
        """카테고리 선택 UI (페이지네이션, 3열 지원)"""
        PAGE_SIZE = 40  # 페이지당 40개

        # 카테고리 항목 준비
        menu_items = []
        for cat in categories:
            name = cat.get("display_name", cat["name"]).upper()
            if "정기 보고서" in cat.get("description", ""):
                name = "REPORT"
            tools_count = len(cat.get("tools", []))
            menu_items.append({"cat": cat, "name": name, "count": tools_count})

        total_count = len(menu_items)
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 1

        while True:
            # 화면 클리어
            clear_screen()

            # 현재 페이지 항목
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, total_count)
            page_items = menu_items[start_idx:end_idx]

            # 열 수 결정 (항목 수에 따라 1~3열)
            page_count = len(page_items)
            if page_count <= 14:
                num_cols = 1
            elif page_count <= 28:
                num_cols = 2
            else:
                num_cols = 3

            # 행 수 계산
            rows_per_col = (page_count + num_cols - 1) // num_cols

            # 테이블 생성
            console.print()
            title = f"[bold]{t('menu.aws_services')}[/bold] ({t('menu.count_suffix', count=total_count)})"
            if total_pages > 1:
                title += f" - {t('menu.page_info', current=current_page, total=total_pages)}"

            table = Table(
                title=title,
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )

            # 열 추가 (동적)
            for _ in range(num_cols):
                table.add_column("#", style="dim", width=4, justify="right")
                table.add_column(t("menu.header_category"), width=22)  # 14 → 22 (한글 11자)
                table.add_column(t("menu.header_tools"), width=5, justify="right")  # 4 → 5

            # 행별로 데이터 추가
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
            nav_parts.append(f"[dim]0[/dim] {t('menu.leave')}")
            console.print("  ".join(nav_parts))
            console.print(f"[dim]{t('menu.enter_number_or_keyword')}[/dim]")

            # 입력 루프
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

            try:
                num = int(choice)
                if num == 0:
                    raise KeyboardInterrupt()
                if 1 <= num <= total_count:
                    return dict(menu_items[num - 1]["cat"])
                console.print(f"[dim]{t('menu.range_info', min=1, max=total_count)}[/dim]")
            except ValueError:
                # 키워드 검색 (다른 페이지 항목도 검색 가능)
                matched = self._search_category_by_keyword(menu_items, choice)
                if matched:
                    return dict(matched["cat"])
                # 검색 결과 없으면 전체 검색으로 이동
                return self._quick_search_and_select(categories, choice)

    def _search_category_by_keyword(self, menu_items: list[dict], keyword: str) -> dict | None:
        """카테고리 이름으로 빠른 검색 (모든 페이지 대상)

        정확히 일치하거나 부분 일치하는 카테고리를 찾음.
        여러 개 일치 시 선택 UI 표시.
        """
        keyword_upper = keyword.upper()

        # 정확히 일치하는 경우
        exact_matches = [m for m in menu_items if m["name"] == keyword_upper]
        if len(exact_matches) == 1:
            return exact_matches[0]

        # 부분 일치
        partial_matches = [m for m in menu_items if keyword_upper in m["name"]]

        if not partial_matches:
            return None

        if len(partial_matches) == 1:
            return partial_matches[0]

        # 여러 개 일치 - 선택 UI
        console.print(f"\n[dim]'{keyword}' {t('common.search')}:[/dim]")
        for i, match in enumerate(partial_matches, 1):
            console.print(f"  {i}) {match['name']} ({t('menu.count_suffix', count=match['count'])})")
        console.print(f"  0) {t('menu.cancel')}")

        while True:
            choice = console.input("> ").strip()
            if not choice:
                continue
            try:
                num = int(choice)
                if num == 0:
                    return None
                if 1 <= num <= len(partial_matches):
                    return partial_matches[num - 1]
            except ValueError:
                pass
            console.print(f"[dim]{t('menu.range_info', min=0, max=len(partial_matches))}[/dim]")

    def _quick_search_and_select(self, categories: list[dict], keyword: str = "") -> dict:
        """빠른 검색으로 카테고리/도구 찾기"""
        from cli.ui.search import get_search_engine, init_search_engine

        if not keyword:
            keyword = console.input(f"{t('common.search')}: ").strip()

        if not keyword:
            return self._select_category(categories)

        # 검색 엔진 사용
        engine = get_search_engine()
        if not engine._built:
            engine = init_search_engine(categories)

        results = engine.search(keyword, limit=15)

        if not results:
            console.print(f"[dim]{t('menu.no_results', query=keyword)}[/dim]")
            return self._select_category(categories)

        # 테이블로 결과 표시
        console.print()
        table = Table(
            title=f"[bold]{t('common.search')}: {keyword}[/bold] ({t('menu.count_suffix', count=len(results))})",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column(t("menu.header_category"), width=16)  # 12 → 16
        table.add_column(t("menu.header_name"), width=26)      # 20 → 26
        table.add_column(t("menu.header_description"), style="dim")

        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.category_display.upper(), r.tool_name, r.description[:30])

        console.print(table)
        console.print()
        console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

        # 선택
        max_idx = len(results)
        while True:
            choice = console.input("> ").strip()
            if not choice:
                continue
            try:
                num = int(choice)
                if num == 0:
                    return self._select_category(categories)
                if 1 <= num <= max_idx:
                    selected = results[num - 1]
                    for cat in categories:
                        if cat["name"] == selected.category:
                            self._selected_tool_from_search = {
                                "category": cat,
                                "tool_module": selected.tool_module,
                                "tool_name": selected.tool_name,
                            }
                            return cat
                console.print(f"[dim]{t('menu.range_info', min=1, max=max_idx)}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('menu.enter_number')}[/dim]")

    def _select_tool(self, category: dict) -> dict | None:
        """도구 선택 UI (필터 지원)"""
        tools = category.get("tools", [])
        return self._display_tool_table_with_filter(category, tools)

    def _display_tool_table_with_filter(self, category: dict, tools: list[dict]) -> dict | None:
        """필터 지원 도구 선택 UI

        p: 권한 필터, a: 영역 필터, r: 필터 초기화

        Returns:
            선택된 도구 dict, 또는 None (이전 메뉴)
        """
        perm_filter: str | None = None
        area_filter: str | None = None

        while True:
            # 화면 클리어
            clear_screen()

            # 필터 적용
            filtered = self._apply_filters(tools, perm_filter, area_filter)

            # 영역별 그룹화 및 정렬
            grouped = self._group_tools_by_area(filtered)

            # 박스 시작
            display_name = category.get("display_name", category["name"]).upper()
            print_box_start(f"{display_name} ({t('menu.count_suffix', count=len(filtered))})")

            # 범례 출력
            self._print_filter_header(perm_filter, area_filter, len(filtered), len(tools), tools)
            print_box_line()

            # 영역별로 도구 출력
            tool_index = 1
            index_map = {}  # 번호 → 도구 매핑

            for area_key, area_tools in grouped.items():
                area_info = AREA_DISPLAY.get(area_key, {"label": area_key or t("menu.other"), "color": "dim"})
                area_label = area_info["label"]
                area_color = area_info["color"]

                # 영역 헤더
                print_box_line(f" [{area_color}]▸ {area_label}[/{area_color}] [dim]({len(area_tools)})[/dim]")

                # 도구 목록 (2열) - 직접 포맷팅
                sorted_tools = self._sort_tools(area_tools)
                half = (len(sorted_tools) + 1) // 2

                for i in range(half):
                    left = sorted_tools[i]
                    left_perm = left.get("permission", "read")
                    left_color = PERMISSION_COLORS.get(left_perm, "green")
                    left_name = left["name"][:26]
                    left_num = f"[{left_color}]{tool_index:>2}[/{left_color}]"
                    index_map[tool_index] = left
                    tool_index += 1

                    if i + half < len(sorted_tools):
                        right = sorted_tools[i + half]
                        right_perm = right.get("permission", "read")
                        right_color = PERMISSION_COLORS.get(right_perm, "green")
                        right_name = right["name"][:26]
                        right_num = f"[{right_color}]{tool_index:>2}[/{right_color}]"
                        index_map[tool_index] = right
                        tool_index += 1
                        # 2열 출력 (Rich Table 사용)
                        row_table = Table(show_header=False, box=None, padding=(0, 1), pad_edge=False)
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=26)  # 20 → 26
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=26)  # 20 → 26
                        row_table.add_row(left_num, left_name, right_num, right_name)
                        console.print("[bold #FF9900]│[/]   ", end="")
                        console.print(row_table)
                    else:
                        # 1열만 출력
                        row_table = Table(show_header=False, box=None, padding=(0, 1), pad_edge=False)
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=26)  # 20 → 26
                        row_table.add_row(left_num, left_name)
                        console.print("[bold #FF9900]│[/]   ", end="")
                        console.print(row_table)

            print_box_line()
            print_box_line(f" [dim]p[/dim] {t('menu.permission_filter')}  [dim]a[/dim] {t('menu.area_filter')}  [dim]r[/dim] {t('menu.reset')}  [dim]0[/dim] {t('menu.go_back')}")

            print_box_end()

            # 입력
            choice = console.input("> ").strip().lower()

            if not choice:
                continue

            # 필터 명령
            if choice == "p":
                perm_filter = self._select_permission_filter(perm_filter)
                continue
            elif choice == "a":
                area_filter = self._select_area_filter(area_filter, tools)
                continue
            elif choice == "r":
                perm_filter = None
                area_filter = None
                continue

            # 번호 선택
            try:
                idx = int(choice)
                if idx == 0:
                    return None
                if idx in index_map:
                    return index_map[idx]
                console.print(f"[dim]{t('menu.range_info', min=1, max=len(index_map))}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('menu.number_or_filter')}[/dim]")

    def _group_tools_by_area(self, tools: list[dict]) -> dict[str, list[dict]]:
        """영역별로 도구 그룹화 (순서 유지)"""
        from collections import OrderedDict

        # 영역 우선순위 (AWS Trusted Advisor 5대 영역)
        area_order = [
            "security",
            "cost",
            "fault_tolerance",
            "performance",
            "operational",
            "",
        ]

        grouped: dict[str, list[dict]] = OrderedDict()

        # 우선순위 순서대로 빈 리스트 초기화
        for area in area_order:
            grouped[area] = []

        # 도구 분류
        for tool in tools:
            area = tool.get("area", "")
            if area not in grouped:
                grouped[area] = []
            grouped[area].append(tool)

        # 빈 영역 제거
        return OrderedDict((k, v) for k, v in grouped.items() if v)

    def _apply_filters(self, tools: list[dict], perm_filter: str | None, area_filter: str | None) -> list[dict]:
        """필터 적용"""
        result = tools
        if perm_filter:
            result = [t for t in result if t.get("permission", "read") == perm_filter]
        if area_filter:
            result = [t for t in result if t.get("area", "") == area_filter]
        return result

    def _print_filter_header(
        self,
        perm_filter: str | None,
        area_filter: str | None,
        filtered_count: int,
        total_count: int,
        tools: list[dict] | None = None,
    ) -> None:
        """필터 헤더 출력"""
        # 필터 상태
        if perm_filter or area_filter:
            filters = []
            if perm_filter:
                perm_labels = {
                    "read": t("menu.permission_read"),
                    "write": t("menu.permission_write"),
                    "delete": t("menu.permission_delete"),
                }
                perm_label = perm_labels.get(perm_filter, perm_filter)
                filters.append(perm_label)
            if area_filter:
                area_label = AREA_DISPLAY.get(area_filter, {}).get("label", area_filter)
                filters.append(area_label)
            print_box_line(f" [dim]{t('menu.filter_status', filters=', '.join(filters), filtered=filtered_count, total=total_count)}[/dim]")

    def _select_permission_filter(self, current: str | None) -> str | None:
        """권한 필터 선택"""
        console.print(f"[dim]1){t('menu.permission_read')} 2){t('menu.permission_write')} 3){t('menu.permission_delete')} 0){t('menu.cancel')}[/dim]")
        choice = console.input("> ").strip()
        mapping = {"1": "read", "2": "write", "3": "delete"}
        return mapping.get(choice, current)

    def _select_area_filter(self, current: str | None, tools: list[dict] | None = None) -> str | None:
        """영역 필터 선택 (해당 카테고리에 있는 영역만 표시)"""
        # 사용 중인 영역만 필터링
        if tools:
            used_areas = set(tool.get("area", "") for tool in tools if tool.get("area"))
            areas = [(k, v) for k, v in AREA_DISPLAY.items() if k in used_areas]
        else:
            areas = list(AREA_DISPLAY.items())

        if not areas:
            console.print(f"[dim]{t('menu.no_filter_areas')}[/dim]")
            return current

        labels = " ".join([f"{i + 1}){info['label']}" for i, (_, info) in enumerate(areas)])
        console.print(f"[dim]{labels} 0){t('menu.cancel')}[/dim]")
        choice = console.input("> ").strip()
        try:
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(areas):
                return areas[idx - 1][0]
        except ValueError:
            pass
        return current

    def _sort_tools(self, tools: list[dict]) -> list[dict]:
        """권한순 → 이름순 정렬"""
        perm_order = {"read": 1, "write": 2, "delete": 3}
        return sorted(
            tools,
            key=lambda t: (
                perm_order.get(t.get("permission", "read"), 1),
                t.get("name", "").lower(),
            ),
        )
