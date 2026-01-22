"""
cli/ui/main_menu.py - 메인 메뉴 UI (V2)

100+ 서비스 확장 대응:
- 검색 우선 (Search-First)
- 즐겨찾기 (최대 5개 표시)
- 통합 입력 (번호/키워드)
"""

from typing import TYPE_CHECKING, Any

from rich.console import Console

from cli.i18n import get_lang, get_text, t
from cli.ui.banner import print_banner

if TYPE_CHECKING:
    from cli.ui.search import ToolSearchEngine
    from core.auth.config.loader import AWSProfile
    from core.tools.history import FavoritesManager, RecentHistory
    from core.tools.types import AreaInfo
from cli.ui.console import clear_screen, console as default_console
from cli.ui.console import (
    wait_for_any_key,
)
from core.tools.types import AREA_COMMANDS, AREA_KEYWORDS, AREA_REGISTRY

# 권한별 색상
PERMISSION_COLORS = {
    "read": "green",
    "write": "yellow",
    "delete": "red",
}

# 단축키 매핑
SHORTCUTS = {
    "h": "help",
    "?": "help",
    "a": "all_tools",
    "s": "browse",  # 서비스별 (EC2, ELB, VPC...)
    "c": "aws_category",  # AWS 카테고리 (Compute, Storage...)
    "t": "trusted_advisor",  # Trusted Advisor 영역 (보안, 비용, 성능...)
    "f": "favorites",
    "g": "profile_groups",
    "p": "profiles",
    "0": "exit",
    "q": "exit",
    "quit": "exit",
    "exit": "exit",
}


class MainMenu:
    """메인 메뉴 클래스 (V2 - 확장성 대응)"""

    def __init__(self, console: Console | None = None, lang: str = "ko"):
        """초기화

        Args:
            console: Rich Console 인스턴스 (기본: 전역 console 사용)
            lang: 언어 설정 ("ko" 또는 "en", 기본값: "ko")
        """
        self.console = console or default_console
        self.lang = lang
        self._categories: list[dict] = []
        self._search_engine: ToolSearchEngine | None = None
        self._recent_history: RecentHistory | None = None
        self._favorites: FavoritesManager | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """지연 초기화 (첫 호출 시)"""
        if self._initialized:
            return

        # 카테고리 로드
        from core.tools.discovery import discover_categories

        self._categories = discover_categories(include_aws_services=True)

        # 검색 엔진 초기화
        from cli.ui.search import init_search_engine

        self._search_engine = init_search_engine(self._categories)

        # 이력/즐겨찾기 로드
        from core.tools.history import FavoritesManager, RecentHistory

        self._recent_history = RecentHistory()
        self._favorites = FavoritesManager()

        self._initialized = True

    def show(self) -> tuple[str, Any]:
        """메인 메뉴 표시 및 선택 받기

        Returns:
            (action, data) 튜플
            - action: 액션 이름 (예: "browse", "search", "favorite_select", "exit")
            - data: 추가 데이터 (카테고리명, 검색어, 인덱스 등)
        """
        self._ensure_initialized()

        # 화면 클리어 후 배너 출력
        clear_screen()
        print_banner(self.console)

        # 즐겨찾기 섹션 (최대 5개)
        fav_items = self._print_favorites_section()

        # 네비게이션 섹션 (서비스 탐색 가이드)
        self._print_navigation_section()

        # 하단 안내
        self._print_footer()

        # 통합 입력
        return self._get_unified_input(fav_items)

    def _print_favorites_section(self) -> list[Any]:
        """즐겨찾기 섹션 출력 (최대 5개)

        Returns:
            favorite items 리스트
        """
        assert self._favorites is not None
        all_favs = self._favorites.get_all()
        fav_items = all_favs[:5]

        if not fav_items:
            return []

        count_info = f" ({len(fav_items)}/{len(all_favs)})" if len(all_favs) > 5 else ""
        self.console.print(f"[bold]{t('menu.favorites')}{count_info}[/bold]")

        for i, item in enumerate(fav_items, 1):
            self.console.print(f"  {i}. {item.tool_name} [dim]{item.category}[/dim]")

        return fav_items

    def _print_navigation_section(self) -> None:
        """네비게이션 섹션 출력"""
        from rich.table import Table

        self.console.print()
        self.console.print(f"[bold]{t('menu.tool_navigation')}[/bold]")

        # Rich Table로 정렬
        cmd_table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            pad_edge=False,
        )
        cmd_table.add_column(width=3)
        cmd_table.add_column(width=16)
        cmd_table.add_column(width=3)
        cmd_table.add_column(width=16)
        cmd_table.add_column(width=3)
        cmd_table.add_column(width=16)

        cmd_table.add_row(
            "[dim]a[/dim]",
            t('menu.all_tools'),
            "[dim]s[/dim]",
            t('menu.aws_services'),
            "[dim]c[/dim]",
            t('menu.aws_category'),
        )
        cmd_table.add_row(
            "[dim]t[/dim]",
            t('menu.check_types'),
            "",
            "",
            "",
            "",
        )
        self.console.print(cmd_table)

        self.console.print()
        self.console.print(f"[bold]{t('menu.settings')}[/bold]")
        cmd_table2 = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            pad_edge=False,
        )
        cmd_table2.add_column(width=3)
        cmd_table2.add_column(width=16)
        cmd_table2.add_column(width=3)
        cmd_table2.add_column(width=16)
        cmd_table2.add_column(width=3)
        cmd_table2.add_column(width=16)
        cmd_table2.add_row(
            "[dim]f[/dim]",
            t('menu.favorites'),
            "[dim]p[/dim]",
            t('menu.profiles'),
            "[dim]g[/dim]",
            t('menu.profile_groups'),
        )
        cmd_table2.add_row(
            "[dim]q[/dim]",
            t('common.exit'),
            "",
            "",
            "",
            "",
        )
        self.console.print(cmd_table2)

        self.console.print()
        self.console.print(f"[dim]{t('menu.search_keyword_hint')}[/dim]")

    def _print_footer(self) -> None:
        """하단 안내 출력"""
        pass  # 네비게이션 섹션에 통합됨

    def _get_unified_input(
        self,
        fav_items: list,
    ) -> tuple[str, Any]:
        """통합 입력 처리

        - 숫자: 즐겨찾기 선택
        - 단축키: 빠른 작업/기타 액션
        - 그 외: 검색 쿼리

        Returns:
            (action, data) 튜플
        """
        self.console.print()
        user_input = self.console.input("> ").strip()

        if not user_input:
            return ("show_menu", None)

        user_lower = user_input.lower()

        # 1. 단축키 체크 (a, b, w, f, h, q 등)
        if user_lower in SHORTCUTS:
            return (SHORTCUTS[user_lower], None)

        # 2. 숫자 입력: 즐겨찾기 선택
        if user_input.isdigit():
            idx = int(user_input)
            fav_count = len(fav_items)

            # 즐겨찾기 범위
            if 1 <= idx <= fav_count:
                item = fav_items[idx - 1]
                return ("favorite_select", item)

            # 범위 초과
            if fav_count > 0:
                self.console.print(f"[red]! {t('menu.enter_range_number', max=fav_count)}[/red]")
            else:
                self.console.print(f"[red]! {t('menu.no_favorites')}[/red]")
            return ("show_menu", None)

        # 4. 그 외: 검색
        return ("search", user_input)

    def run_action(self, action: str, data: Any = None) -> bool:
        """액션 실행

        Args:
            action: 액션 이름
            data: 추가 데이터

        Returns:
            True: 메뉴 계속, False: 종료
        """
        self._ensure_initialized()

        if action == "exit":
            self.console.print(f"[dim]{t('common.exit')}[/dim]")
            return False

        if action == "show_menu":
            return True

        if action == "help":
            self._show_help()
            return True

        if action == "all_tools":
            self._list_all_tools()
            return True

        if action == "browse":
            # 서비스별 탐색 (FlowRunner로 위임)
            from cli.flow import create_flow_runner

            runner = create_flow_runner()
            runner.run()
            return True

        if action == "aws_category":
            # AWS 카테고리별 탐색
            self._show_aws_category_view()
            return True

        if action == "trusted_advisor":
            # Trusted Advisor 영역별 탐색
            self._show_trusted_advisor_view()
            return True

        if action == "favorite_select":
            # 즐겨찾기 도구 직접 실행
            self._run_tool_directly(data.category, data.tool_module)
            return True

        if action == "search":
            # 검색 결과 표시 및 선택
            self._handle_search(data)
            return True

        if action == "favorites":
            self._manage_favorites()
            return True

        if action == "settings":
            self._show_settings()
            return True

        if action == "profiles":
            self._show_profiles()
            return True

        if action == "profile_groups":
            self._manage_profile_groups()
            return True

        return True

    def _run_tool_directly(self, category: str, tool_module: str) -> None:
        """도구 직접 실행 (프로파일/리전 선택 후)"""
        from cli.flow import create_flow_runner

        runner = create_flow_runner()
        runner.run_tool_directly(category, tool_module)

        # 도구 실행 완료 후 메뉴 복귀 전 대기
        self.console.print()
        wait_for_any_key(f"[dim]{t('common.press_any_key_to_return')}[/dim]")

    def _handle_search(self, query: str) -> None:
        """검색 처리"""
        if not self._search_engine:
            self.console.print(f"[red]{t('menu.search_engine_not_initialized')}[/]")
            return

        query_lower = query.lower()

        # /command 스타일 필터 처리
        if query_lower in AREA_COMMANDS:
            self._handle_area_search(query, AREA_COMMANDS[query_lower])
            return

        # Area 키워드 매칭 처리
        if query in AREA_KEYWORDS:
            self._handle_area_search(query, AREA_KEYWORDS[query])
            return

        results = self._search_engine.search(query, limit=15)

        if not results:
            self.console.print()
            self.console.print(f"[yellow]{t('menu.no_results', query=query)}[/]")
            self.console.print(f"[dim]{t('menu.search_no_results_hint')}[/]")
            wait_for_any_key()
            return

        # 화면 클리어 후 검색 결과 표시
        clear_screen()
        from rich.table import Table

        self.console.print()
        table = Table(
            title=f"[bold]{t('common.search')}: {query}[/bold] ({t('menu.search_results_count', count=len(results))})",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column(t("menu.header_category"), width=16)
        table.add_column(t("menu.header_name"), width=26)
        table.add_column(t("menu.header_description"), style="dim")

        for i, r in enumerate(results, 1):
            table.add_row(
                str(i),
                r.category_display.upper(),
                r.tool_name,
                r.description[:50] if r.description else "",  # 35 → 50
            )

        self.console.print(table)
        self.console.print()
        self.console.print(f"[dim]0: {t('common.back')}[/dim]")

        # 선택
        while True:
            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(results):
                    selected = results[idx - 1]
                    self._run_tool_directly(selected.category, selected.tool_module)
                    return

            self.console.print(f"[red]{t('menu.enter_range_number', max=len(results))}[/]")

    def _handle_area_search(self, query: str, area: str) -> None:
        """영역(area) 기반 검색 처리"""
        from rich.table import Table

        # 모든 도구를 flat list로
        all_tools = []
        for cat in self._categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)
            for tool in cat.get("tools", []):
                all_tools.append(
                    {
                        "category": cat_name,
                        "category_display": cat_display,
                        "tool_module": tool.get("module", ""),
                        **tool,
                    }
                )

        # area 필터링
        results = [(i, t) for i, t in enumerate(all_tools, 1) if t.get("area") == area]

        if not results:
            self.console.print()
            self.console.print(f"[yellow]{t('menu.no_results', query=query)}[/]")
            wait_for_any_key()
            return

        # 결과 표시
        self.console.print()
        table = Table(
            title=f"[bold]{query}[/bold] ({t('menu.search_results_count', count=len(results))})",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column(t("menu.header_category"), width=16)  # 12 → 16
        table.add_column(t("menu.header_tools"), width=28)      # 25 → 28
        table.add_column(t("menu.header_description"), style="dim")

        for i, (_, tool) in enumerate(results, 1):
            table.add_row(
                str(i),
                tool.get("category_display", tool.get("category", "")).upper(),
                tool.get("name", ""),
                (tool.get("description", "") or "")[:55],  # 40 → 55
            )

        self.console.print(table)
        self.console.print()
        self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

        # 선택
        while True:
            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(results):
                    _, selected = results[idx - 1]
                    self._run_tool_directly(selected["category"], selected["tool_module"])
                    return

            self.console.print(f"[red]{t('menu.range_info', min=0, max=len(results))}[/]")

    def _list_all_tools(self) -> None:
        """전체 도구 목록 표시 및 선택 (페이지네이션 적용)"""
        from rich.table import Table

        PAGE_SIZE = 20

        # 모든 도구를 flat list로 만들어 번호 부여
        all_tools = []
        for cat in self._categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)
            cat_desc = cat.get("description", cat_name)
            tools = cat.get("tools", [])
            for tool in tools:
                all_tools.append(
                    {
                        "category": cat_name,
                        "category_display": cat_display,
                        "category_desc": cat_desc,
                        **tool,
                    }
                )

        total_count = len(all_tools)
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 1

        while True:
            # 화면 클리어
            clear_screen()

            # 현재 페이지의 도구들
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, total_count)
            page_tools = all_tools[start_idx:end_idx]

            self.console.print()
            table = Table(
                title=f"[bold]{t('menu.all_tools')}[/bold] ({t('menu.count_suffix', count=total_count)}) - {t('menu.page_info', current=current_page, total=total_pages)}",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column(t("menu.header_category"), width=18)  # 14 → 18
            table.add_column(t("menu.header_tools"), width=28)      # 22 → 28
            table.add_column(t("menu.header_description"), style="dim")

            for idx, tool in enumerate(page_tools, start_idx + 1):
                table.add_row(
                    str(idx),
                    tool.get("category_display", tool["category"]).upper(),
                    tool.get("name", ""),
                    tool.get("description", "")[:55],  # 40 → 55
                )

            self.console.print(table)
            self.console.print()

            # 네비게이션 안내
            nav_parts = []
            if current_page > 1:
                nav_parts.append(f"[dim]p[/dim] {t('menu.previous')}")
            if current_page < total_pages:
                nav_parts.append(f"[dim]n[/dim] {t('menu.next')}")
            nav_parts.append(f"[dim]0[/dim] {t('menu.go_back')}")
            self.console.print("  ".join(nav_parts))
            self.console.print(f"[dim]{t('menu.select_tool_prompt')}[/dim]")

            # 입력 처리
            choice = self.console.input("> ").strip()

            if not choice:
                continue

            choice_lower = choice.lower()

            # 종료
            if choice == "0" or choice_lower == "q":
                return

            # 페이지 이동
            if choice_lower == "n":
                if current_page < total_pages:
                    current_page += 1
                else:
                    self.console.print(f"[dim]{t('menu.last_page')}[/dim]")
                continue

            if choice_lower == "p":
                if current_page > 1:
                    current_page -= 1
                else:
                    self.console.print(f"[dim]{t('menu.first_page')}[/dim]")
                continue

            # 숫자 입력: 도구 선택
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= total_count:
                    selected = all_tools[idx - 1]
                    module = selected.get("module", "")
                    self._run_tool_directly(selected["category"], module)
                    return
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=total_count)}[/]")
                continue

            # 키워드 검색
            self._handle_search_in_all_tools(choice, all_tools)

    def _handle_search_in_all_tools(self, query: str, all_tools: list) -> None:
        """전체 도구 목록 내에서 검색 및 선택

        지원하는 검색 방식:
        - 키워드 검색: 카테고리, 이름, 설명에서 매칭
        - Area 키워드: "보안", "비용", "미사용" 등 → 해당 area 도구
        - /command 필터: /cost, /security 등 → 해당 area만 필터
        """
        from rich.table import Table

        query_lower = query.lower()
        filter_area = None
        display_title = query

        # 1. /command 스타일 필터 체크
        if query_lower in AREA_COMMANDS:
            filter_area = AREA_COMMANDS[query_lower]
            display_title = f"{query} ({filter_area})"

        # 2. Area 키워드 매칭 체크
        if not filter_area and query in AREA_KEYWORDS:
            filter_area = AREA_KEYWORDS[query]

        # 검색 수행
        results = []
        for idx, tool in enumerate(all_tools, 1):
            tool_area = tool.get("area", "")

            # Area 필터가 있으면 area만 매칭
            if filter_area:
                if tool_area == filter_area:
                    results.append((idx, tool))
            else:
                # 일반 키워드 검색: 카테고리, 이름, 설명, area에서 매칭
                cat = tool.get("category", "").lower()
                name = tool.get("name", "").lower()
                desc = tool.get("description", "").lower()

                if query_lower in cat or query_lower in name or query_lower in desc or query_lower in tool_area:
                    results.append((idx, tool))

        if not results:
            self.console.print()
            self.console.print(f"[yellow]{t('menu.no_results', query=query)}[/]")
            wait_for_any_key()
            return

        # 검색 결과 표시
        self.console.print()
        table = Table(
            title=f"[bold]{t('common.search')}: {display_title}[/bold] ({t('menu.search_results_count', count=len(results))})",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column(t("menu.header_category"), width=18)  # 14 → 18
        table.add_column(t("menu.header_tools"), width=28)      # 22 → 28
        table.add_column(t("menu.header_description"), style="dim")

        for orig_idx, tool in results:
            table.add_row(
                str(orig_idx),
                tool.get("category_display", tool["category"]).upper(),
                tool.get("name", ""),
                tool.get("description", "")[:55],  # 40 → 55
            )

        self.console.print(table)
        self.console.print()
        self.console.print(f"[dim]{t('menu.select_tool_or_return')}[/dim]")

        # 선택
        choice = self.console.input("> ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            # 원본 번호로 선택
            if 1 <= idx <= len(all_tools):
                selected = all_tools[idx - 1]
                module = selected.get("module", "")
                self._run_tool_directly(selected["category"], module)

    def _show_help(self) -> None:
        """도움말 표시"""
        self.console.print()
        self.console.print(f"[bold cyan]=== {t('menu.help_title')} ===[/bold cyan]")
        self.console.print()

        # 메뉴 탐색
        self.console.print(f"[bold yellow]{t('menu.tool_navigation')}[/bold yellow]")
        self.console.print(f"  [cyan]a[/cyan]  {t('menu.all_tools'):14} {t('menu.help_all_tools_desc')}")
        self.console.print(f"  [cyan]s[/cyan]  {t('menu.aws_services'):14} {t('menu.help_services_desc')}")
        self.console.print(f"  [cyan]c[/cyan]  {t('menu.aws_category'):14} {t('menu.help_categories_desc')}")
        self.console.print(f"  [cyan]t[/cyan]  {t('menu.check_types'):14} {t('menu.help_check_types_desc')}")
        self.console.print(f"  [cyan]f[/cyan]  {t('menu.favorites'):14} {t('menu.help_favorites_desc')}")
        self.console.print()
        self.console.print(f"[bold yellow]{t('menu.settings')}[/bold yellow]")
        self.console.print(f"  [cyan]g[/cyan]  {t('menu.profile_groups'):14} {t('menu.help_groups_desc')}")
        self.console.print(f"  [cyan]p[/cyan]  {t('menu.profiles'):14} {t('menu.help_profiles_desc')}")
        self.console.print(f"  [cyan]h[/cyan]  {t('common.help'):14} {t('menu.help_help_desc')}")
        self.console.print(f"  [cyan]q[/cyan]  {t('common.exit'):14} {t('menu.help_quit_desc')}")
        self.console.print(f"  [cyan]1-5[/cyan]               {t('menu.help_favorites_quick_desc')}")
        self.console.print()

        # 검색
        self.console.print(f"[bold yellow]{t('common.search')}[/bold yellow]")
        self.console.print(f"  [white]rds, ec2, iam ...[/white]     {t('menu.help_search_services')}")
        self.console.print(f"  [white]snapshot, backup[/white]      {t('menu.help_search_keyword_en')}")
        self.console.print()

        # /command 필터 (AREA_REGISTRY에서 생성)
        self.console.print(f"[bold yellow]{t('menu.help_domain_filter')}[/bold yellow]")
        for area in AREA_REGISTRY:
            cmd = area["command"].ljust(12)
            label = area.get("label_en", area["label"]) if self.lang == "en" else area["label"]
            desc = area.get("desc_en", area["desc"]) if self.lang == "en" else area["desc"]
            self.console.print(f"  [green]{cmd}[/green] {label}, {desc}")
        self.console.print()

        # CLI 직접 실행
        self.console.print(f"[bold yellow]{t('menu.help_cli_direct')}[/bold yellow]")
        self.console.print(f"  [dim]$[/dim] aa                   {t('menu.help_cli_interactive')}")
        self.console.print(f"  [dim]$[/dim] aa rds                {t('menu.help_cli_tool_list')}")
        self.console.print(f"  [dim]$[/dim] aa ec2 --help         {t('menu.help_cli_service_help')}")
        self.console.print()

        # 출력
        self.console.print(f"[bold yellow]{t('menu.help_output_path')}[/bold yellow]")
        self.console.print(f"  {t('menu.help_output_location')}: [dim]~/aa-output/<account>/<date>/[/dim]")
        self.console.print()

        wait_for_any_key()

    def _manage_favorites(self) -> None:
        """즐겨찾기 관리"""
        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            self.console.print(f"[bold]{t('menu.favorites_management')}[/bold]")
            self.console.print()

            assert self._favorites is not None
            fav_items = self._favorites.get_all()

            if fav_items:
                for i, item in enumerate(fav_items, 1):
                    self.console.print(f"  {i:>2}. {item.tool_name} [dim]{item.category}[/dim]")
                self.console.print()
            else:
                self.console.print(f"[dim]{t('menu.no_favorites_registered')}[/dim]")
                self.console.print()

            # 메뉴 옵션
            self.console.print(
                f"[dim]a[/dim] {t('menu.add')}"
                + (f"  [dim]d[/dim] {t('menu.delete')}  [dim]u[/dim] {t('menu.move_up')}  [dim]n[/dim] {t('menu.move_down')}" if fav_items else "")
                + f"  [dim]0[/dim] {t('menu.go_back')}"
            )
            self.console.print()

            choice = self.console.input(f"[bold]{t('common.enter_selection')}:[/bold] ").strip().lower()

            if choice == "0" or choice == "":
                return

            if choice == "a":
                self._add_favorite_interactive()
            elif choice == "d" and fav_items:
                self._remove_favorite_interactive(fav_items)
            elif choice == "u" and fav_items:
                self._reorder_favorite_interactive(fav_items, "up")
            elif choice == "n" and fav_items:
                self._reorder_favorite_interactive(fav_items, "down")

    def _add_favorite_interactive(self) -> None:
        """즐겨찾기 추가"""
        self.console.print()
        self.console.print(f"[bold]{t('menu.add_favorite')}[/bold]")
        self.console.print(f"[dim]{t('menu.tool_name_or_keyword')}[/dim]")

        query = self.console.input(f"{t('common.search')}: ").strip()

        if not query:
            return

        if not self._search_engine:
            self.console.print(f"[dim]{t('menu.search_init_failed')}[/dim]")
            return

        results = self._search_engine.search(query, limit=10)

        if not results:
            self.console.print(f"[dim]{t('menu.no_results', query=query)}[/dim]")
            return

        # 검색 결과 표시
        assert self._favorites is not None
        self.console.print()
        for i, r in enumerate(results, 1):
            is_fav = self._favorites.is_favorite(r.category, r.tool_module)
            fav_marker = " *" if is_fav else ""
            self.console.print(f"  {i:>2}. [{r.category}] {r.tool_name}{fav_marker}")

        self.console.print()
        self.console.print(f"[dim]{t('menu.return_zero')}[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if choice == "0" or not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(results):
                selected = results[idx - 1]
                if self._favorites.is_favorite(selected.category, selected.tool_module):
                    self.console.print(f"[dim]{t('menu.already_registered', name=selected.tool_name)}[/dim]")
                else:
                    success = self._favorites.add(selected.category, selected.tool_name, selected.tool_module)
                    if success:
                        self.console.print(f"[dim]{t('menu.added', name=selected.tool_name)}[/dim]")
                    else:
                        self.console.print(f"[dim]{t('menu.add_failed_max')}[/dim]")

    def _remove_favorite_interactive(self, fav_items: list) -> None:
        """즐겨찾기 삭제"""
        self.console.print()
        self.console.print(f"[bold]{t('menu.delete_number_prompt')}[/bold] [dim]({t('menu.cancel_enter_hint')})[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(fav_items):
                item = fav_items[idx - 1]
                assert self._favorites is not None
                self._favorites.remove(item.category, item.tool_module)
                self.console.print(f"[dim]{t('menu.deleted', name=item.tool_name)}[/dim]")
            else:
                self.console.print(f"[dim]{t('menu.range_info', min=1, max=len(fav_items))}[/dim]")

    def _reorder_favorite_interactive(self, fav_items: list, direction: str) -> None:
        """즐겨찾기 순서 변경"""
        self.console.print()
        label = t('menu.move_up') if direction == "up" else t('menu.move_down')
        self.console.print(f"[bold]{t('menu.move_number_prompt', direction=label)}[/bold] [dim]({t('menu.cancel_enter_hint')})[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(fav_items):
                item = fav_items[idx - 1]
                assert self._favorites is not None
                if direction == "up":
                    success = self._favorites.move_up(item.category, item.tool_module)
                else:
                    success = self._favorites.move_down(item.category, item.tool_module)

                if success:
                    self.console.print(f"[dim]{t('menu.moved', name=item.tool_name)}[/dim]")
                else:
                    pos = t('menu.already_at_top') if direction == "up" else t('menu.already_at_bottom')
                    self.console.print(f"[dim]{pos}[/dim]")
            else:
                self.console.print(f"[dim]{t('menu.range_info', min=1, max=len(fav_items))}[/dim]")

    def _show_profiles(self) -> None:
        """사용 가능한 AWS 프로필 목록 표시"""
        self.console.print()
        self.console.print(f"[bold cyan]=== {t('menu.aws_auth_profiles')} ===[/bold cyan]")
        self.console.print()

        try:
            from core.auth import (
                ProviderType,
                detect_provider_type,
                list_profiles,
                list_sso_sessions,
                load_config,
            )

            config = load_config()

            # SSO 세션 목록
            sso_sessions = list_sso_sessions()
            if sso_sessions:
                self.console.print(f"[bold]{t('menu.sso_session_multi')}[/bold] [dim]({t('menu.sso_session_desc')})[/dim]")
                for session in sso_sessions:
                    session_config = config.sessions.get(session)
                    if session_config:
                        self.console.print(f"  [cyan]●[/cyan] {session} [dim]({session_config.region})[/dim]")
                    else:
                        self.console.print(f"  [cyan]●[/cyan] {session}")
                self.console.print()

            # 프로파일 목록 (타입별 그룹화)
            profiles = list_profiles()
            if profiles:
                sso_profiles: list[tuple[str, AWSProfile]] = []
                static_profiles: list[tuple[str, AWSProfile]] = []
                other_profiles: list[tuple[str, AWSProfile | None]] = []

                for name in profiles:
                    profile_config = config.profiles.get(name)
                    if not profile_config:
                        other_profiles.append((name, None))
                        continue

                    ptype = detect_provider_type(profile_config)
                    if ptype == ProviderType.SSO_PROFILE:
                        sso_profiles.append((name, profile_config))
                    elif ptype == ProviderType.STATIC_CREDENTIALS:
                        static_profiles.append((name, profile_config))
                    else:
                        other_profiles.append((name, profile_config))

                # SSO 프로파일
                if sso_profiles:
                    self.console.print(f"[bold]{t('menu.sso_profile_single')}[/bold] [dim]({t('menu.sso_profile_desc')})[/dim]")
                    for name, cfg in sso_profiles:
                        if cfg and cfg.sso_account_id:
                            self.console.print(f"  [green]●[/green] {name} [dim]({cfg.sso_account_id})[/dim]")
                        else:
                            self.console.print(f"  [green]●[/green] {name}")
                    self.console.print()

                # Static 프로파일
                if static_profiles:
                    self.console.print(f"[bold]{t('menu.iam_access_key')}[/bold] [dim]({t('menu.static_credentials_desc')})[/dim]")
                    for name, cfg in static_profiles:
                        region_info = f" ({cfg.region})" if cfg and cfg.region else ""
                        self.console.print(f"  [yellow]●[/yellow] {name}{region_info}")
                    self.console.print()

                # 기타 (지원하지 않는 타입)
                if other_profiles:
                    self.console.print(f"[bold dim]{t('menu.other_unsupported')}[/bold dim] [dim]({t('menu.unsupported')})[/dim]")
                    for name, _ in other_profiles:
                        self.console.print(f"  [dim]○[/dim] {name}")
                    self.console.print()

            if not sso_sessions and not profiles:
                self.console.print(f"[dim]{t('menu.no_profiles_configured')}[/dim]")
                self.console.print()
                self.console.print(f"[dim]{t('menu.check_aws_config')}[/dim]")

        except Exception as e:
            self.console.print(f"[red]{t('menu.profile_load_failed', error=str(e))}[/red]")

        self.console.print()
        wait_for_any_key()

    def _show_settings(self) -> None:
        """설정 표시"""
        self.console.print()
        self.console.print(f"[bold]{t('menu.settings')}[/bold]")
        self.console.print(f"[dim]{t('menu.preparing')}[/dim]")

        from core.tools.cache import get_cache_dir

        cache_dir = get_cache_dir("history")
        self.console.print(f"[dim]{t('menu.history_location', path=cache_dir)}[/dim]")

    def _show_trusted_advisor_view(self) -> None:
        """Trusted Advisor 영역별 탐색 뷰"""
        from rich.table import Table

        # 모든 도구를 flat list로
        all_tools = []
        for cat in self._categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)
            for tool in cat.get("tools", []):
                all_tools.append(
                    {
                        "category": cat_name,
                        "category_display": cat_display,
                        "tool_module": tool.get("module", ""),
                        **tool,
                    }
                )

        # 영역별 도구 수 계산
        area_tool_counts: dict[str, int] = {}
        for tool in all_tools:
            area = tool.get("area", "")
            if area:
                area_tool_counts[area] = area_tool_counts.get(area, 0) + 1

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            table = Table(
                title=f"[bold]{t('menu.check_types')}[/bold]",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=3, justify="right")
            table.add_column(t("menu.header_area"), width=14)      # 12 → 14
            table.add_column(t("menu.header_description"), width=30)      # 25 → 30
            table.add_column(t("menu.header_tools"), width=6, justify="right")

            for i, area in enumerate(AREA_REGISTRY, 1):
                tool_count = area_tool_counts.get(area["key"], 0)
                label = area.get("label_en", area["label"]) if self.lang == "en" else area["label"]
                desc = area.get("desc_en", area["desc"]) if self.lang == "en" else area["desc"]
                table.add_row(
                    str(i),
                    f"[{area['color']}]{label}[/{area['color']}]",
                    desc,
                    str(tool_count),
                )

            self.console.print(table)
            self.console.print()
            self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(AREA_REGISTRY):
                    selected_area = AREA_REGISTRY[idx - 1]
                    self._show_tools_in_area(selected_area, all_tools)
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=len(AREA_REGISTRY))}[/]")

    def _show_tools_in_area(self, area: "AreaInfo", all_tools: list) -> None:
        """영역 내 도구 목록 표시 및 선택"""
        from rich.table import Table

        area_key = area["key"]
        tools = [tl for tl in all_tools if tl.get("area") == area_key]
        area_label = area.get("label_en", area["label"]) if self.lang == "en" else area["label"]

        if not tools:
            self.console.print(f"[yellow]{t('menu.no_tools_in_area', area=area_label)}[/]")
            wait_for_any_key()
            return

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            table = Table(
                title=f"[bold][{area['color']}]{area_label}[/{area['color']}][/bold] ({t('menu.count_suffix', count=len(tools))})",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=3, justify="right")
            table.add_column(t("menu.header_service"), width=14)    # 12 → 14
            table.add_column(t("menu.header_tools"), width=28)      # 25 → 28
            table.add_column(t("menu.header_permission"), width=6)
            table.add_column(t("menu.header_description"), style="dim")

            for i, tool in enumerate(tools, 1):
                perm = tool.get("permission", "read")
                perm_color = PERMISSION_COLORS.get(perm, "green")
                table.add_row(
                    str(i),
                    tool.get("category_display", tool["category"]).upper(),
                    tool.get("name", ""),
                    f"[{perm_color}]{perm}[/{perm_color}]",
                    (tool.get("description", "") or "")[:50],  # 35 → 50
                )

            self.console.print(table)
            self.console.print()
            self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(tools):
                    selected_tool = tools[idx - 1]
                    self._run_tool_directly(selected_tool["category"], selected_tool["tool_module"])
                    return
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=len(tools))}[/]")

    def _show_aws_category_view(self) -> None:
        """AWS 카테고리별 탐색 뷰"""
        from rich.table import Table

        from core.tools.aws_categories import get_aws_category_view

        aws_categories = get_aws_category_view()

        if not aws_categories:
            self.console.print()
            self.console.print(f"[yellow]{t('menu.no_plugins_in_category')}[/]")
            wait_for_any_key()
            return

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            table = Table(
                title=f"[bold]{t('menu.aws_category')}[/bold]",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=3, justify="right")
            table.add_column(t("menu.header_category"), width=38)  # 30 → 38
            table.add_column(t("menu.header_service"), width=6, justify="right")
            table.add_column(t("menu.header_tools"), width=6, justify="right")

            for i, cat in enumerate(aws_categories, 1):
                table.add_row(
                    str(i),
                    f"{cat['name']} ({cat['name_ko']})",
                    str(len(cat["plugins"])),
                    str(cat["tool_count"]),
                )

            self.console.print(table)
            self.console.print()
            self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(aws_categories):
                    selected_cat = aws_categories[idx - 1]
                    self._show_services_in_category(selected_cat)
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=len(aws_categories))}[/]")

    def _show_services_in_category(self, aws_category: dict) -> None:
        """AWS 카테고리 내 서비스(플러그인) 목록 표시"""
        from rich.table import Table

        plugins = aws_category.get("plugins", [])

        if not plugins:
            self.console.print(f"[yellow]{t('menu.no_services_in_category')}[/]")
            wait_for_any_key()
            return

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            table = Table(
                title=f"[bold]{aws_category['name']}[/bold] ({aws_category['name_ko']})",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=3, justify="right")
            table.add_column(t("menu.header_service"), width=26)    # 20 → 26
            table.add_column(t("menu.header_tools"), width=6, justify="right")
            table.add_column(t("menu.header_description"), style="dim")

            for i, plugin in enumerate(plugins, 1):
                display_name = plugin.get("display_name", plugin.get("name", ""))
                tool_count = len(plugin.get("tools", []))
                desc = plugin.get("description", "")[:55]  # 40 → 55
                table.add_row(str(i), display_name.upper(), str(tool_count), desc)

            self.console.print(table)
            self.console.print()
            self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(plugins):
                    selected_plugin = plugins[idx - 1]
                    self._show_tools_in_service(selected_plugin)
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=len(plugins))}[/]")

    def _show_tools_in_service(self, plugin: dict) -> None:
        """서비스 내 도구 목록 표시 및 선택"""
        from rich.table import Table

        from core.tools.types import AREA_DISPLAY_BY_KEY as AREA_DISPLAY

        tools = plugin.get("tools", [])
        category_name = plugin.get("name", "")

        if not tools:
            self.console.print(f"[yellow]{t('menu.no_tools_in_service')}[/]")
            wait_for_any_key()
            return

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            display_name = plugin.get("display_name", category_name).upper()
            table = Table(
                title=f"[bold]{display_name}[/bold] ({t('menu.count_suffix', count=len(tools))})",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=3, justify="right")
            table.add_column(t("menu.header_tools"), width=30)      # 25 → 30
            table.add_column(t("menu.header_permission"), width=6)
            table.add_column(t("menu.header_area"), width=10)
            table.add_column(t("menu.header_description"), style="dim")

            for i, tool in enumerate(tools, 1):
                perm = tool.get("permission", "read")
                perm_color = PERMISSION_COLORS.get(perm, "green")
                area = tool.get("area", "")
                area_info = AREA_DISPLAY.get(area, {"label": area, "color": "dim"})

                table.add_row(
                    str(i),
                    tool.get("name", ""),
                    f"[{perm_color}]{perm}[/{perm_color}]",
                    f"[{area_info['color']}]{area_info['label']}[/{area_info['color']}]" if area else "",
                    (tool.get("description", "") or "")[:50],  # 35 → 50
                )

            self.console.print(table)
            self.console.print()
            self.console.print(f"[dim]0: {t('menu.go_back')}[/dim]")

            choice = self.console.input("> ").strip()

            if not choice:
                continue

            if choice == "0" or choice.lower() == "q":
                return

            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(tools):
                    selected_tool = tools[idx - 1]
                    tool_module = selected_tool.get("module", "")
                    self._run_tool_directly(category_name, tool_module)
                    return
                else:
                    self.console.print(f"[red]{t('menu.range_info', min=1, max=len(tools))}[/]")

    def _get_profiles_by_kind(self, kind: str) -> list:
        """인증 타입별 프로파일 목록 조회

        Args:
            kind: "sso_profile" 또는 "static"

        Returns:
            프로파일 이름 목록
        """
        from core.auth import detect_provider_type, list_profiles, load_config
        from core.auth.types import ProviderType

        result = []
        try:
            config_data = load_config()

            for profile_name in list_profiles():
                profile_config = config_data.profiles.get(profile_name)
                if not profile_config:
                    continue

                provider_type = detect_provider_type(profile_config)

                if (
                    kind == "sso_profile"
                    and provider_type == ProviderType.SSO_PROFILE
                    or (kind == "static" and provider_type == ProviderType.STATIC_CREDENTIALS)
                ):
                    result.append(profile_name)
        except Exception:
            pass

        return result

    def _manage_profile_groups(self) -> None:
        """프로파일 그룹 관리"""
        from core.tools.history import ProfileGroupsManager

        manager = ProfileGroupsManager()

        while True:
            # 화면 클리어
            clear_screen()

            self.console.print()
            self.console.print(f"[bold]{t('menu.profile_groups_management')}[/bold]")
            self.console.print()

            groups = manager.get_all()

            if groups:
                kind_labels = {"sso_profile": "SSO", "static": "Key"}
                for i, g in enumerate(groups, 1):
                    kind_label = kind_labels.get(g.kind, g.kind)
                    profiles_preview = ", ".join(g.profiles[:2])
                    if len(g.profiles) > 2:
                        profiles_preview += f" {t('cli.and_n_more', count=len(g.profiles) - 2)}"
                    self.console.print(f"  {i:>2}. [{kind_label}] {g.name} [dim]({profiles_preview})[/dim]")
                self.console.print()
            else:
                self.console.print(f"[dim]{t('menu.no_groups_saved')}[/dim]")
                self.console.print()

            # 메뉴 옵션
            self.console.print(
                f"[dim]a[/dim] {t('menu.add')}"
                + (f"  [dim]d[/dim] {t('menu.delete')}  [dim]e[/dim] {t('menu.edit')}  [dim]u[/dim] {t('menu.move_up')}  [dim]n[/dim] {t('menu.move_down')}" if groups else "")
                + f"  [dim]0[/dim] {t('menu.go_back')}"
            )
            self.console.print()

            choice = self.console.input(f"[bold]{t('common.enter_selection')}:[/bold] ").strip().lower()

            if choice == "0" or choice == "":
                return

            if choice == "a":
                self._add_profile_group_interactive(manager)
            elif choice == "d" and groups:
                self._remove_profile_group_interactive(manager, groups)
            elif choice == "e" and groups:
                self._edit_profile_group_interactive(manager, groups)
            elif choice == "u" and groups:
                self._reorder_profile_group_interactive(manager, groups, "up")
            elif choice == "n" and groups:
                self._reorder_profile_group_interactive(manager, groups, "down")

    def _add_profile_group_interactive(self, manager) -> None:
        """프로파일 그룹 추가"""
        self.console.print()
        self.console.print(f"[bold]{t('cli.create_group_title')}[/bold]")
        self.console.print()

        # 1. 인증 타입 선택
        self.console.print(f"{t('cli.select_auth_type')}")
        self.console.print(f"  [cyan]1)[/cyan] {t('cli.sso_profile')}")
        self.console.print(f"  [cyan]2)[/cyan] {t('cli.iam_access_key')}")
        self.console.print(f"  [dim]0) {t('menu.cancel')}[/dim]")
        self.console.print()

        choice = self.console.input(f"{t('cli.select_prompt')}: ").strip()
        if choice == "0" or not choice:
            return
        if choice not in ("1", "2"):
            self.console.print(f"[red]{t('menu.range_info', min=1, max=2)}[/red]")
            return

        kind = "sso_profile" if choice == "1" else "static"

        # 2. 해당 타입의 프로파일 목록 가져오기
        available = self._get_profiles_by_kind(kind)
        type_label = t("cli.sso_profile") if kind == "sso_profile" else t("cli.iam_access_key")

        if not available:
            self.console.print(f"\n[red]{t('cli.no_profiles_available', type=type_label)}[/red]")
            return

        # 3. 프로파일 선택 (멀티)
        self.console.print()
        self.console.print(f"[bold]{t('cli.select_profiles_title', type=type_label)}[/bold] {t('cli.select_2_or_more')}")
        self.console.print()
        for i, p in enumerate(available, 1):
            self.console.print(f"  [cyan]{i:2})[/cyan] {p}")
        self.console.print()
        self.console.print(f"[dim]{t('cli.selection_hint')}[/dim]")
        self.console.print(f"[dim]0) {t('menu.cancel')}[/dim]")

        selection = self.console.input(f"{t('cli.select_prompt')}: ").strip()
        if selection == "0" or not selection:
            return

        selected = self._parse_multi_selection(selection, len(available))
        if len(selected) < 2:
            self.console.print(f"[red]{t('cli.min_2_profiles')}[/red]")
            return

        selected_profiles = [available[i] for i in selected]

        # 4. 그룹 이름 입력
        self.console.print()
        self.console.print(f"{t('cli.selected_profiles')} {', '.join(selected_profiles)}")
        self.console.print()
        name = self.console.input(f"{t('cli.group_name_prompt')} ({t('menu.cancel')}: Enter): ").strip()

        if not name:
            return

        # 5. 저장
        if manager.add(name, kind, selected_profiles):
            self.console.print(f"[green]* {t('cli.group_saved', name=name, count=len(selected_profiles))}[/green]")
        else:
            self.console.print(f"[red]{t('cli.group_save_failed')}[/red]")

    def _parse_multi_selection(self, selection: str, max_count: int) -> list:
        """선택 문자열 파싱 (1 2 3, 1,2,3, 1-3 지원)"""
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
                            result.add(i - 1)
                except ValueError:
                    continue
            else:
                try:
                    num = int(part)
                    if 1 <= num <= max_count:
                        result.add(num - 1)
                except ValueError:
                    continue

        return sorted(result)

    def _remove_profile_group_interactive(self, manager, groups) -> None:
        """프로파일 그룹 삭제"""
        self.console.print()
        self.console.print(f"[bold]{t('menu.delete_number_prompt')}[/bold] [dim]({t('menu.cancel_enter_hint')})[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(groups):
                group = groups[idx - 1]
                manager.remove(group.name)
                self.console.print(f"[dim]{t('menu.deleted', name=group.name)}[/dim]")
            else:
                self.console.print(f"[dim]{t('menu.range_info', min=1, max=len(groups))}[/dim]")

    def _edit_profile_group_interactive(self, manager, groups) -> None:
        """프로파일 그룹 수정"""
        self.console.print()
        self.console.print(f"[bold]{t('menu.edit_number_prompt')}[/bold] [dim]({t('menu.cancel_enter_hint')})[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if not choice:
            return

        if not choice.isdigit():
            return

        idx = int(choice)
        if not 1 <= idx <= len(groups):
            self.console.print(f"[dim]{t('menu.range_info', min=1, max=len(groups))}[/dim]")
            return

        group = groups[idx - 1]

        self.console.print()
        self.console.print(f"[bold]{t('menu.edit_group', name=group.name)}[/bold]")
        self.console.print()
        self.console.print(f"  1) {t('menu.change_name')}")
        self.console.print(f"  2) {t('menu.change_profiles')}")
        self.console.print(f"  [dim]0) {t('menu.cancel')}[/dim]")

        edit_choice = self.console.input(f"{t('menu.selection_prompt')}: ").strip()

        if edit_choice == "1":
            new_name = self.console.input(f"{t('menu.new_name_prompt')}: ").strip()
            if new_name:
                if manager.update(group.name, new_name=new_name):
                    self.console.print(f"[dim]{t('menu.name_changed', name=new_name)}[/dim]")
                else:
                    self.console.print(f"[red]{t('menu.change_failed_duplicate')}[/red]")

        elif edit_choice == "2":
            available = self._get_profiles_by_kind(group.kind)

            if not available:
                self.console.print(f"[red]{t('menu.no_profiles_available')}[/red]")
                return

            self.console.print()
            for i, p in enumerate(available, 1):
                marker = " *" if p in group.profiles else ""
                self.console.print(f"  [cyan]{i:2})[/cyan] {p}{marker}")
            self.console.print()
            self.console.print(f"[dim]{t('menu.selection_hint')}[/dim]")

            selection = self.console.input(f"{t('menu.select_new_profiles')}: ").strip()
            if not selection:
                return

            selected = self._parse_multi_selection(selection, len(available))
            if selected:
                new_profiles = [available[i] for i in selected]
                if manager.update(group.name, profiles=new_profiles):
                    self.console.print(f"[dim]{t('menu.profiles_changed', count=len(new_profiles))}[/dim]")

    def _reorder_profile_group_interactive(self, manager, groups, direction: str) -> None:
        """프로파일 그룹 순서 변경"""
        self.console.print()
        label = t('menu.move_up') if direction == "up" else t('menu.move_down')
        self.console.print(f"[bold]{t('menu.move_number_prompt', direction=label)}[/bold] [dim]({t('menu.cancel_enter_hint')})[/dim]")

        choice = self.console.input(f"{t('menu.number_prompt')}: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(groups):
                group = groups[idx - 1]
                success = manager.move_up(group.name) if direction == "up" else manager.move_down(group.name)

                if success:
                    self.console.print(f"[dim]{t('menu.moved', name=group.name)}[/dim]")
                else:
                    pos = t('menu.already_at_top') if direction == "up" else t('menu.already_at_bottom')
                    self.console.print(f"[dim]{pos}[/dim]")
            else:
                self.console.print(f"[dim]{t('menu.range_info', min=1, max=len(groups))}[/dim]")


def show_main_menu(lang: str = "ko") -> None:
    """메인 메뉴 표시 및 루프 실행

    Args:
        lang: 언어 설정 ("ko" 또는 "en", 기본값: "ko")
    """
    from cli.i18n import set_lang, t

    set_lang(lang)
    menu = MainMenu(lang=lang)

    while True:
        try:
            action, data = menu.show()
            should_continue = menu.run_action(action, data)

            if not should_continue:
                break

        except KeyboardInterrupt:
            menu.console.print(f"\n[dim]{t('common.exit')}[/dim]")
            break
