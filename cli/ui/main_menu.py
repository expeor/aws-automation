"""
cli/ui/main_menu.py - 메인 메뉴 UI (V2)

100+ 서비스 확장 대응:
- 검색 우선 (Search-First)
- 즐겨찾기 (최대 5개 표시)
- 통합 입력 (번호/키워드)
"""

from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console

from cli.ui.banner import print_banner
from cli.ui.console import console as default_console
from cli.ui.console import print_box_end, print_box_line, print_box_start, wait_for_any_key

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
    "b": "browse",
    "f": "favorites",
    "p": "profiles",
    "0": "exit",
    "q": "exit",
    "quit": "exit",
    "exit": "exit",
}

# Area 정의는 core/tools/types.py에서 import (단일 소스)
from core.tools.types import AREA_COMMANDS, AREA_KEYWORDS, AREA_REGISTRY


class MainMenu:
    """메인 메뉴 클래스 (V2 - 확장성 대응)"""

    def __init__(self, console: Optional[Console] = None):
        """초기화"""
        self.console = console or default_console
        self._categories: List[Dict] = []
        self._search_engine = None
        self._recent_history = None
        self._favorites = None
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

    def show(self) -> Tuple[str, Any]:
        """메인 메뉴 표시 및 선택 받기

        Returns:
            (action, data) 튜플
            - action: 액션 이름 (예: "browse", "search", "favorite_select", "exit")
            - data: 추가 데이터 (카테고리명, 검색어, 인덱스 등)
        """
        self._ensure_initialized()

        # 배너 출력
        print_banner(self.console)

        # 즐겨찾기 섹션 (최대 5개)
        fav_items = self._print_favorites_section()

        # 네비게이션 섹션 (서비스 탐색 가이드)
        self._print_navigation_section()

        # 하단 안내
        self._print_footer()

        # 통합 입력
        return self._get_unified_input(fav_items)

    def _print_favorites_section(self) -> List[Any]:
        """즐겨찾기 섹션 출력 (최대 5개)

        Returns:
            favorite items 리스트
        """
        all_favs = self._favorites.get_all()
        fav_items = all_favs[:5]

        if not fav_items:
            return []

        count_info = f" ({len(fav_items)}/{len(all_favs)})" if len(all_favs) > 5 else ""
        self.console.print(f"[bold]즐겨찾기{count_info}[/bold]")

        for i, item in enumerate(fav_items, 1):
            self.console.print(f"  {i}. {item.tool_name} [dim]{item.category}[/dim]")

        return fav_items

    def _print_navigation_section(self) -> None:
        """네비게이션 섹션 출력"""
        from rich.table import Table

        self.console.print()
        self.console.print("[bold]명령어[/bold]")

        # Rich Table로 정렬
        cmd_table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            pad_edge=False,
        )
        cmd_table.add_column(width=2)  # 키
        cmd_table.add_column(width=10)  # 설명
        cmd_table.add_column(width=2)  # 키
        cmd_table.add_column(width=10)  # 설명
        cmd_table.add_column(width=2)  # 키
        cmd_table.add_column(width=10)  # 설명

        cmd_table.add_row(
            "[dim]a[/dim]", "전체 도구",
            "[dim]b[/dim]", "카테고리",
            "[dim]f[/dim]", "즐겨찾기",
        )
        cmd_table.add_row(
            "[dim]p[/dim]", "프로필",
            "[dim]h[/dim]", "도움말",
            "[dim]q[/dim]", "종료",
        )

        self.console.print(cmd_table)
        self.console.print()
        self.console.print("[dim]검색: 키워드 또는 /cost /security /ops /inv[/dim]")

    def _print_footer(self) -> None:
        """하단 안내 출력"""
        pass  # 네비게이션 섹션에 통합됨

    def _get_unified_input(
        self,
        fav_items: List,
    ) -> Tuple[str, Any]:
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
                self.console.print(f"[red]! 1-{fav_count} 범위의 번호를 입력하세요.[/red]")
            else:
                self.console.print("[red]! 즐겨찾기가 없습니다.[/red]")
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
            self.console.print("[dim]종료[/dim]")
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
            # 카테고리 탐색 (FlowRunner로 위임)
            from cli.flow import create_flow_runner

            runner = create_flow_runner()
            runner.run()
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

        return True

    def _run_tool_directly(self, category: str, tool_module: str) -> None:
        """도구 직접 실행 (프로파일/리전 선택 후)"""
        from cli.flow import create_flow_runner

        runner = create_flow_runner()
        runner.run_tool_directly(category, tool_module)

        # 도구 실행 완료 후 메뉴 복귀 전 대기
        self.console.print()
        wait_for_any_key("[dim]아무 키나 눌러 메뉴로 돌아가기...[/dim]")

    def _handle_search(self, query: str) -> None:
        """검색 처리"""
        if not self._search_engine:
            self.console.print("[red]검색 엔진이 초기화되지 않았습니다.[/]")
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
            self.console.print(f"[yellow]'{query}' 검색 결과 없음[/]")
            self.console.print("[dim]다른 키워드로 검색하거나 b 키로 카테고리를 탐색하세요.[/]")
            wait_for_any_key()
            return

        # 검색 결과 표시
        from rich.table import Table

        self.console.print()
        table = Table(
            title=f"[bold]검색: {query}[/bold] ({len(results)}건)",
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
            table.add_row(
                str(i),
                r.category_display.upper(),
                r.tool_name,
                r.description[:35] if r.description else "",
            )

        self.console.print(table)
        self.console.print()
        self.console.print("[dim]0: 돌아가기[/dim]")

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

            self.console.print(f"[red]0-{len(results)} 범위의 번호를 입력하세요.[/]")

    def _handle_area_search(self, query: str, area: str) -> None:
        """영역(area) 기반 검색 처리"""
        from rich.table import Table

        # 모든 도구를 flat list로
        all_tools = []
        for cat in self._categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)
            for tool in cat.get("tools", []):
                all_tools.append({
                    "category": cat_name,
                    "category_display": cat_display,
                    "tool_module": tool.get("module", ""),
                    **tool
                })

        # area 필터링
        results = [(i, t) for i, t in enumerate(all_tools, 1) if t.get("area") == area]

        if not results:
            self.console.print()
            self.console.print(f"[yellow]'{query}' 검색 결과 없음[/]")
            wait_for_any_key()
            return

        # 결과 표시
        self.console.print()
        table = Table(
            title=f"[bold]{query}[/bold] ({len(results)}건)",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=3, justify="right")
        table.add_column("카테고리", width=12)
        table.add_column("도구", width=25)
        table.add_column("설명", style="dim")

        for i, (_, tool) in enumerate(results, 1):
            table.add_row(
                str(i),
                tool.get("category_display", tool.get("category", "")).upper(),
                tool.get("name", ""),
                (tool.get("description", "") or "")[:40],
            )

        self.console.print(table)
        self.console.print()
        self.console.print("[dim]0: 돌아가기[/dim]")

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

            self.console.print(f"[red]0-{len(results)} 범위의 번호를 입력하세요.[/]")

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
                    {"category": cat_name, "category_display": cat_display, "category_desc": cat_desc, **tool}
                )

        total_count = len(all_tools)
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        current_page = 1

        while True:
            # 현재 페이지의 도구들
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, total_count)
            page_tools = all_tools[start_idx:end_idx]

            self.console.print()
            table = Table(
                title=f"[bold]전체 도구[/bold] ({total_count}개) - 페이지 {current_page}/{total_pages}",
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 1),
                title_justify="left",
            )
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column("카테고리", width=14)
            table.add_column("도구", width=22)
            table.add_column("설명", style="dim")

            for idx, tool in enumerate(page_tools, start_idx + 1):
                table.add_row(
                    str(idx),
                    tool.get("category_display", tool["category"]).upper(),
                    tool.get("name", ""),
                    tool.get("description", "")[:40],
                )

            self.console.print(table)
            self.console.print()

            # 네비게이션 안내
            nav_parts = []
            if current_page > 1:
                nav_parts.append("[dim]p[/dim] 이전")
            if current_page < total_pages:
                nav_parts.append("[dim]n[/dim] 다음")
            nav_parts.append("[dim]0[/dim] 돌아가기")
            self.console.print("  ".join(nav_parts))
            self.console.print("[dim]번호 입력: 도구 선택 | 키워드 입력: 검색[/dim]")

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
                    self.console.print("[dim]마지막 페이지입니다.[/dim]")
                continue

            if choice_lower == "p":
                if current_page > 1:
                    current_page -= 1
                else:
                    self.console.print("[dim]첫 번째 페이지입니다.[/dim]")
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
                    self.console.print(f"[red]1-{total_count} 범위의 번호를 입력하세요.[/]")
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

                if (
                    query_lower in cat
                    or query_lower in name
                    or query_lower in desc
                    or query_lower in tool_area
                ):
                    results.append((idx, tool))

        if not results:
            self.console.print()
            self.console.print(f"[yellow]'{query}' 검색 결과 없음[/]")
            wait_for_any_key()
            return

        # 검색 결과 표시
        self.console.print()
        table = Table(
            title=f"[bold]검색: {display_title}[/bold] ({len(results)}건)",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 1),
            title_justify="left",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("카테고리", width=14)
        table.add_column("도구", width=22)
        table.add_column("설명", style="dim")

        for orig_idx, tool in results:
            table.add_row(
                str(orig_idx),
                tool.get("category_display", tool["category"]).upper(),
                tool.get("name", ""),
                tool.get("description", "")[:40],
            )

        self.console.print(table)
        self.console.print()
        self.console.print("[dim]번호 입력: 도구 선택 | Enter: 목록으로 돌아가기[/dim]")

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
        self.console.print("[bold cyan]═══ AWS Automation CLI 도움말 ═══[/bold cyan]")
        self.console.print()

        # 메뉴 탐색
        self.console.print("[bold yellow]메뉴 명령어[/bold yellow]")
        self.console.print("  [cyan]a[/cyan]  전체 도구      모든 도구를 한 화면에 표시")
        self.console.print("  [cyan]b[/cyan]  카테고리       AWS 서비스별 카테고리 메뉴")
        self.console.print("  [cyan]f[/cyan]  즐겨찾기       자주 사용하는 도구 추가/제거")
        self.console.print("  [cyan]p[/cyan]  프로필         AWS 프로필 전환 (SSO/Access Key)")
        self.console.print("  [cyan]h[/cyan]  도움말         이 화면 표시")
        self.console.print("  [cyan]q[/cyan]  종료           프로그램 종료")
        self.console.print("  [cyan]1-5[/cyan]               즐겨찾기 바로 실행")
        self.console.print()

        # 검색
        self.console.print("[bold yellow]검색[/bold yellow]")
        self.console.print("  [white]rds, ec2, iam ...[/white]     AWS 서비스명")
        self.console.print("  [white]미사용, 보안, 비용[/white]    한글 키워드")
        self.console.print("  [white]snapshot, backup[/white]      영문 키워드")
        self.console.print()

        # /command 필터 (AREA_REGISTRY에서 생성)
        self.console.print("[bold yellow]도메인 필터[/bold yellow]")
        for area in AREA_REGISTRY:
            cmd = area["command"].ljust(12)
            self.console.print(f"  [green]{cmd}[/green] {area['label']}, {area['desc']}")
        self.console.print()

        # CLI 직접 실행
        self.console.print("[bold yellow]CLI 직접 실행[/bold yellow]")
        self.console.print("  [dim]$[/dim] aa                   대화형 메뉴")
        self.console.print("  [dim]$[/dim] aa rds                RDS 도구 목록")
        self.console.print("  [dim]$[/dim] aa ec2 --help         EC2 도움말")
        self.console.print()

        # 출력
        self.console.print("[bold yellow]출력 경로[/bold yellow]")
        self.console.print("  결과 파일: [dim]~/aa-output/<account>/<date>/[/dim]")
        self.console.print()

        wait_for_any_key()

    def _manage_favorites(self) -> None:
        """즐겨찾기 관리"""
        while True:
            self.console.print()
            self.console.print("[bold]즐겨찾기 관리[/bold]")
            self.console.print()

            fav_items = self._favorites.get_all()

            if fav_items:
                for i, item in enumerate(fav_items, 1):
                    self.console.print(
                        f"  {i:>2}. {item.tool_name} [dim]{item.category}[/dim]"
                    )
                self.console.print()
            else:
                self.console.print("[dim]등록된 즐겨찾기가 없습니다.[/dim]")
                self.console.print()

            # 메뉴 옵션
            self.console.print(
                "[dim]a[/dim] 추가"
                + (
                    "  [dim]d[/dim] 삭제  [dim]u[/dim] 위로  [dim]n[/dim] 아래로"
                    if fav_items
                    else ""
                )
                + "  [dim]0[/dim] 돌아가기"
            )
            self.console.print()

            choice = self.console.input("[bold]선택:[/bold] ").strip().lower()

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
        self.console.print("[bold]즐겨찾기 추가[/bold]")
        self.console.print("[dim]도구명 또는 키워드 입력 (취소: Enter)[/dim]")

        query = self.console.input("검색: ").strip()

        if not query:
            return

        if not self._search_engine:
            self.console.print("[dim]검색 엔진 초기화 실패[/dim]")
            return

        results = self._search_engine.search(query, limit=10)

        if not results:
            self.console.print(f"[dim]'{query}' 결과 없음[/dim]")
            return

        # 검색 결과 표시
        self.console.print()
        for i, r in enumerate(results, 1):
            is_fav = self._favorites.is_favorite(r.category, r.tool_module)
            fav_marker = " *" if is_fav else ""
            self.console.print(f"  {i:>2}. [{r.category}] {r.tool_name}{fav_marker}")

        self.console.print()
        self.console.print("[dim]0: 돌아가기[/dim]")

        choice = self.console.input("번호: ").strip()

        if choice == "0" or not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(results):
                selected = results[idx - 1]
                if self._favorites.is_favorite(selected.category, selected.tool_module):
                    self.console.print(f"[dim]'{selected.tool_name}' 이미 등록됨[/dim]")
                else:
                    success = self._favorites.add(
                        selected.category, selected.tool_name, selected.tool_module
                    )
                    if success:
                        self.console.print(f"[dim]'{selected.tool_name}' 추가됨[/dim]")
                    else:
                        self.console.print("[dim]추가 실패 (최대 20개)[/dim]")

    def _remove_favorite_interactive(self, fav_items: List) -> None:
        """즐겨찾기 삭제"""
        self.console.print()
        self.console.print("[bold]삭제할 번호[/bold] [dim](취소: Enter)[/dim]")

        choice = self.console.input("번호: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(fav_items):
                item = fav_items[idx - 1]
                self._favorites.remove(item.category, item.tool_module)
                self.console.print(f"[dim]'{item.tool_name}' 삭제됨[/dim]")
            else:
                self.console.print(f"[dim]1-{len(fav_items)} 범위[/dim]")

    def _reorder_favorite_interactive(self, fav_items: List, direction: str) -> None:
        """즐겨찾기 순서 변경"""
        self.console.print()
        label = "위로" if direction == "up" else "아래로"
        self.console.print(f"[bold]{label} 이동할 번호[/bold] [dim](취소: Enter)[/dim]")

        choice = self.console.input("번호: ").strip()

        if not choice:
            return

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(fav_items):
                item = fav_items[idx - 1]
                if direction == "up":
                    success = self._favorites.move_up(item.category, item.tool_module)
                else:
                    success = self._favorites.move_down(item.category, item.tool_module)

                if success:
                    self.console.print(f"[dim]'{item.tool_name}' 이동됨[/dim]")
                else:
                    pos = "최상위" if direction == "up" else "최하위"
                    self.console.print(f"[dim]이미 {pos}[/dim]")
            else:
                self.console.print(f"[dim]1-{len(fav_items)} 범위[/dim]")

    def _show_profiles(self) -> None:
        """사용 가능한 AWS 프로필 목록 표시"""
        self.console.print()
        self.console.print("[bold cyan]═══ AWS 인증 프로필 ═══[/bold cyan]")
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
                self.console.print("[bold]SSO 세션[/bold] [dim](멀티 계정)[/dim]")
                for session in sso_sessions:
                    session_config = config.sessions.get(session)
                    if session_config:
                        self.console.print(
                            f"  [cyan]●[/cyan] {session} [dim]({session_config.region})[/dim]"
                        )
                    else:
                        self.console.print(f"  [cyan]●[/cyan] {session}")
                self.console.print()

            # 프로파일 목록 (타입별 그룹화)
            profiles = list_profiles()
            if profiles:
                sso_profiles = []
                static_profiles = []
                other_profiles = []

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
                    self.console.print("[bold]SSO 프로파일[/bold] [dim](고정 계정/역할)[/dim]")
                    for name, cfg in sso_profiles:
                        if cfg and cfg.sso_account_id:
                            self.console.print(
                                f"  [green]●[/green] {name} [dim]({cfg.sso_account_id})[/dim]"
                            )
                        else:
                            self.console.print(f"  [green]●[/green] {name}")
                    self.console.print()

                # Static 프로파일
                if static_profiles:
                    self.console.print("[bold]IAM Access Key[/bold] [dim](정적 자격 증명)[/dim]")
                    for name, cfg in static_profiles:
                        region_info = f" ({cfg.region})" if cfg and cfg.region else ""
                        self.console.print(f"  [yellow]●[/yellow] {name}{region_info}")
                    self.console.print()

                # 기타 (지원하지 않는 타입)
                if other_profiles:
                    self.console.print("[bold dim]기타[/bold dim] [dim](미지원)[/dim]")
                    for name, _ in other_profiles:
                        self.console.print(f"  [dim]○[/dim] {name}")
                    self.console.print()

            if not sso_sessions and not profiles:
                self.console.print("[dim]설정된 프로필이 없습니다.[/dim]")
                self.console.print()
                self.console.print("[dim]~/.aws/config 또는 ~/.aws/credentials를 확인하세요.[/dim]")

        except Exception as e:
            self.console.print(f"[red]프로필 로드 실패: {e}[/red]")

        self.console.print()
        wait_for_any_key()

    def _show_settings(self) -> None:
        """설정 표시"""
        self.console.print()
        self.console.print("[bold]설정[/bold]")
        self.console.print("[dim]준비 중[/dim]")

        from core.tools.cache import get_cache_dir

        cache_dir = get_cache_dir("history")
        self.console.print(f"[dim]이력: {cache_dir}[/dim]")


def show_main_menu() -> None:
    """메인 메뉴 표시 및 루프 실행"""
    menu = MainMenu()

    while True:
        try:
            action, data = menu.show()
            should_continue = menu.run_action(action, data)

            if not should_continue:
                break

        except KeyboardInterrupt:
            menu.console.print("\n[dim]종료[/dim]")
            break
