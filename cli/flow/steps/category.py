# internal/flow/steps/category.py
"""
카테고리/도구 선택 Step

discovery 기반으로 자동 발견된 카테고리/도구 표시.
menu.py 의존성 제거됨.
"""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from cli.ui.console import print_box_end, print_box_line, print_box_start

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

# 영역별 색상 (AWS Trusted Advisor 5대 영역)
AREA_DISPLAY = {
    "security": {"label": "보안", "color": "red"},
    "cost": {"label": "비용", "color": "yellow"},
    "fault_tolerance": {"label": "내결함성", "color": "blue"},
    "performance": {"label": "성능", "color": "magenta"},
    "operational": {"label": "운영", "color": "cyan"},
}


def _print_section_header(title: str) -> None:
    """섹션 헤더 출력"""
    console.print()
    console.print(f"[bold underline cyan]{title}[/bold underline cyan]")
    console.print()


def _load_categories() -> List[Dict[str, Any]]:
    """discovery 기반 카테고리 로드 (AWS 서비스 포함)"""
    try:
        from core.tools.discovery import discover_categories

        return discover_categories(include_aws_services=True)
    except ImportError as e:
        console.print(f"[red]! discovery 모듈 로드 실패: {e}[/red]")
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
        entry_point: Optional[str] = None,
    ) -> ExecutionContext:
        """카테고리/도구 선택 실행"""
        categories = _load_categories()

        if not categories:
            console.print("[red]! 등록된 도구가 없습니다.[/red]")
            console.print(
                "[yellow]* internal/tools/ 하위에 "
                "CATEGORY, TOOLS가 정의된 폴더를 추가하세요.[/yellow]"
            )
            raise RuntimeError("도구 없음")

        if entry_point:
            # 특정 카테고리로 진입 (aa ebs 등)
            category = self._find_category(categories, entry_point)
            if not category:
                console.print(f"[red]! '{entry_point}' 카테고리를 찾을 수 없습니다.[/red]")
                raise ValueError(f"Unknown category: {entry_point}")

            # 도구 선택 (이전 메뉴 시 전체 메뉴로)
            while True:
                ctx.category = category["name"]
                tool = self._select_tool(category)
                if tool is not None:
                    break
                # 이전 메뉴 선택 시 전체 카테고리 메뉴로
                category = self._select_category(categories)
        else:
            # 전체 카테고리 메뉴 (이전 메뉴 루프)
            while True:
                category = self._select_category(categories)
                ctx.category = category["name"]
                tool = self._select_tool(category)
                if tool is not None:
                    break
                # 이전 메뉴 선택 시 카테고리 선택으로 돌아감

        ctx.tool = _convert_to_tool_info(tool, category["name"])
        return ctx

    def _find_category(self, categories: List[Dict], name: str) -> Optional[Dict]:
        """이름으로 카테고리 검색"""
        for cat in categories:
            if cat["name"] == name:
                return cat
        return None

    def _select_category(self, categories: List[Dict]) -> Dict:
        """카테고리 선택 UI (페이지네이션, 3열 지원)"""
        PAGE_SIZE = 40  # 페이지당 40개
        MAX_COLS = 3  # 최대 3열

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
            title = f"[bold]카테고리 선택[/bold] ({total_count}개)"
            if total_pages > 1:
                title += f" - 페이지 {current_page}/{total_pages}"

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
                table.add_column("카테고리", width=14)
                table.add_column("도구", width=4, justify="right")

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
                    nav_parts.append("[dim]p[/dim] 이전")
                if current_page < total_pages:
                    nav_parts.append("[dim]n[/dim] 다음")
            nav_parts.append("[dim]0[/dim] 나가기")
            console.print("  ".join(nav_parts))
            console.print("[dim]번호 입력 또는 키워드 검색[/dim]")

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
                    return menu_items[num - 1]["cat"]
                console.print(f"[dim]1-{total_count} 범위[/dim]")
            except ValueError:
                # 키워드 검색 (다른 페이지 항목도 검색 가능)
                matched = self._search_category_by_keyword(menu_items, choice)
                if matched:
                    return matched["cat"]
                # 검색 결과 없으면 전체 검색으로 이동
                return self._quick_search_and_select(categories, choice)

    def _search_category_by_keyword(
        self, menu_items: List[Dict], keyword: str
    ) -> Optional[Dict]:
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
        console.print(f"\n[dim]'{keyword}' 검색 결과:[/dim]")
        for i, match in enumerate(partial_matches, 1):
            console.print(f"  {i}) {match['name']} ({match['count']}개)")
        console.print("  0) 취소")

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
            console.print(f"[dim]0-{len(partial_matches)} 범위[/dim]")

    def _quick_search_and_select(
        self, categories: List[Dict], keyword: str = ""
    ) -> Dict:
        """빠른 검색으로 카테고리/도구 찾기"""
        from cli.ui.search import get_search_engine, init_search_engine

        if not keyword:
            keyword = console.input("검색: ").strip()

        if not keyword:
            return self._select_category(categories)

        # 검색 엔진 사용
        engine = get_search_engine()
        if not engine._built:
            engine = init_search_engine(categories)

        results = engine.search(keyword, limit=15)

        if not results:
            console.print(f"[dim]'{keyword}' 결과 없음[/dim]")
            return self._select_category(categories)

        # 테이블로 결과 표시
        console.print()
        table = Table(
            title=f"[bold]검색: {keyword}[/bold] ({len(results)}건)",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("카테고리", width=12)
        table.add_column("도구", width=20)
        table.add_column("설명", style="dim")

        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.category_display.upper(), r.tool_name, r.description[:30])

        console.print(table)
        console.print()
        console.print("[dim]0: 돌아가기[/dim]")

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
                console.print(f"[dim]1-{max_idx} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _select_tool(self, category: Dict) -> Optional[Dict]:
        """도구 선택 UI (필터 지원)"""
        tools = category.get("tools", [])
        return self._display_tool_table_with_filter(category, tools)

    def _display_tool_table_with_filter(
        self, category: Dict, tools: List[Dict]
    ) -> Optional[Dict]:
        """필터 지원 도구 선택 UI

        p: 권한 필터, a: 영역 필터, r: 필터 초기화

        Returns:
            선택된 도구 dict, 또는 None (이전 메뉴)
        """
        perm_filter: Optional[str] = None
        area_filter: Optional[str] = None

        while True:
            # 필터 적용
            filtered = self._apply_filters(tools, perm_filter, area_filter)

            # 영역별 그룹화 및 정렬
            grouped = self._group_tools_by_area(filtered)

            # 박스 시작
            display_name = category.get("display_name", category["name"]).upper()
            print_box_start(f"{display_name} ({len(filtered)}개)")

            # 범례 출력
            self._print_filter_header(
                perm_filter, area_filter, len(filtered), len(tools), tools
            )
            print_box_line()

            # 영역별로 도구 출력
            tool_index = 1
            index_map = {}  # 번호 → 도구 매핑

            for area_key, area_tools in grouped.items():
                area_info = AREA_DISPLAY.get(
                    area_key, {"label": area_key or "기타", "color": "dim"}
                )
                area_label = area_info["label"]
                area_color = area_info["color"]

                # 영역 헤더
                print_box_line(
                    f" [{area_color}]▸ {area_label}[/{area_color}] [dim]({len(area_tools)})[/dim]"
                )

                # 도구 목록 (2열) - 직접 포맷팅
                sorted_tools = self._sort_tools(area_tools)
                half = (len(sorted_tools) + 1) // 2

                for i in range(half):
                    left = sorted_tools[i]
                    left_perm = left.get("permission", "read")
                    left_color = PERMISSION_COLORS.get(left_perm, "green")
                    left_name = left["name"][:20]
                    left_num = f"[{left_color}]{tool_index:>2}[/{left_color}]"
                    index_map[tool_index] = left
                    tool_index += 1

                    if i + half < len(sorted_tools):
                        right = sorted_tools[i + half]
                        right_perm = right.get("permission", "read")
                        right_color = PERMISSION_COLORS.get(right_perm, "green")
                        right_name = right["name"][:20]
                        right_num = f"[{right_color}]{tool_index:>2}[/{right_color}]"
                        index_map[tool_index] = right
                        tool_index += 1
                        # 2열 출력 (Rich Table 사용)
                        row_table = Table(
                            show_header=False, box=None, padding=(0, 1), pad_edge=False
                        )
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=20)
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=20)
                        row_table.add_row(left_num, left_name, right_num, right_name)
                        console.print(f"[bold #FF9900]│[/]   ", end="")
                        console.print(row_table)
                    else:
                        # 1열만 출력
                        row_table = Table(
                            show_header=False, box=None, padding=(0, 1), pad_edge=False
                        )
                        row_table.add_column(width=3, justify="right")
                        row_table.add_column(width=20)
                        row_table.add_row(left_num, left_name)
                        console.print(f"[bold #FF9900]│[/]   ", end="")
                        console.print(row_table)

            print_box_line()
            print_box_line(
                " [dim]p[/dim] 권한필터  [dim]a[/dim] 영역필터  [dim]r[/dim] 초기화  [dim]0[/dim] 돌아가기"
            )

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
                console.print(f"[dim]1-{len(index_map)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 또는 p/a/r[/dim]")

    def _group_tools_by_area(self, tools: List[Dict]) -> Dict[str, List[Dict]]:
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

        grouped: Dict[str, List[Dict]] = OrderedDict()

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

    def _apply_filters(
        self, tools: List[Dict], perm_filter: Optional[str], area_filter: Optional[str]
    ) -> List[Dict]:
        """필터 적용"""
        result = tools
        if perm_filter:
            result = [t for t in result if t.get("permission", "read") == perm_filter]
        if area_filter:
            result = [t for t in result if t.get("area", "") == area_filter]
        return result

    def _print_filter_header(
        self,
        perm_filter: Optional[str],
        area_filter: Optional[str],
        filtered_count: int,
        total_count: int,
        tools: List[Dict] = None,
    ) -> None:
        """필터 헤더 출력"""
        # 권한 범례 (간결)
        perm_legend = "[green]■[/green]읽기 [yellow]■[/yellow]쓰기 [red]■[/red]삭제"
        print_box_line(f" {perm_legend}")

        # 영역 범례 (사용 중인 영역만)
        if tools:
            used_areas = set(t.get("area", "") for t in tools if t.get("area"))
            if used_areas:
                area_parts = []
                for area_key in used_areas:
                    info = AREA_DISPLAY.get(
                        area_key, {"label": area_key, "color": "dim"}
                    )
                    area_parts.append(
                        f"[{info['color']}]■[/{info['color']}]{info['label']}"
                    )
                print_box_line(f" {' '.join(area_parts)}")

        # 필터 상태
        if perm_filter or area_filter:
            filters = []
            if perm_filter:
                perm_label = {"read": "읽기", "write": "쓰기", "delete": "삭제"}.get(
                    perm_filter, perm_filter
                )
                filters.append(perm_label)
            if area_filter:
                area_label = AREA_DISPLAY.get(area_filter, {}).get("label", area_filter)
                filters.append(area_label)
            print_box_line(
                f" [dim]필터: {', '.join(filters)} ({filtered_count}/{total_count})[/dim]"
            )

    def _select_permission_filter(self, current: Optional[str]) -> Optional[str]:
        """권한 필터 선택"""
        console.print("[dim]1)읽기 2)쓰기 3)삭제 0)취소[/dim]")
        choice = console.input("> ").strip()
        if choice == "1":
            return "read"
        elif choice == "2":
            return "write"
        elif choice == "3":
            return "delete"
        return current

    def _select_area_filter(
        self, current: Optional[str], tools: List[Dict] = None
    ) -> Optional[str]:
        """영역 필터 선택 (해당 카테고리에 있는 영역만 표시)"""
        # 사용 중인 영역만 필터링
        if tools:
            used_areas = set(t.get("area", "") for t in tools if t.get("area"))
            areas = [(k, v) for k, v in AREA_DISPLAY.items() if k in used_areas]
        else:
            areas = list(AREA_DISPLAY.items())

        if not areas:
            console.print("[dim]필터 가능한 영역이 없습니다.[/dim]")
            return current

        labels = " ".join(
            [f"{i+1}){info['label']}" for i, (_, info) in enumerate(areas)]
        )
        console.print(f"[dim]{labels} 0)취소[/dim]")
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

    def _sort_tools(self, tools: List[Dict]) -> List[Dict]:
        """권한순 → 이름순 정렬"""
        perm_order = {"read": 1, "write": 2, "delete": 3}
        return sorted(
            tools,
            key=lambda t: (
                perm_order.get(t.get("permission", "read"), 1),
                t.get("name", "").lower(),
            ),
        )
