# internal/flow/runner.py
"""
Flow Runner - CLI Flow의 전체 실행을 관리하는 핵심 모듈.

discovery 기반으로 도구를 자동 발견하고 실행합니다.
"""

import sys
import traceback
from typing import Any

from rich.console import Console

from .context import ExecutionContext, FlowResult, ToolInfo
from .steps import AccountStep, CategoryStep, ProfileStep, RegionStep, RoleStep

console = Console()


class FlowRunner:
    """통합 CLI Flow Runner (discovery 기반)"""

    def run(self, entry_point: str | None = None) -> None:
        """Flow 실행"""
        while True:
            try:
                result = self._run_once(entry_point)

                if not result.success:
                    console.print(f"[red]실행 실패: {result.message}[/red]")

                console.print()

                # 계속 실행 여부 확인
                cont = console.input("[dim]계속? [Y/n][/dim] > ").strip().lower()
                if cont == "n":
                    break

                entry_point = None

            except KeyboardInterrupt:
                console.print()
                console.print("[dim]종료[/dim]")
                break
            except Exception as e:
                console.print()
                console.print(f"[red]오류: {e}[/red]")
                if "--debug" in sys.argv:
                    traceback.print_exc()
                console.print()

                cont = console.input("[dim]계속? [Y/n][/dim] > ").strip().lower()
                if cont == "n":
                    break

                entry_point = None

    def run_tool_directly(
        self,
        category: str,
        tool_module: str,
    ) -> None:
        """도구 직접 실행 (최근 사용/즐겨찾기에서 선택 시)

        Args:
            category: 카테고리 이름
            tool_module: 도구 모듈 이름
        """
        try:
            # 도구 정보 조회
            tool_meta = self._find_tool_meta(category, tool_module)
            if not tool_meta:
                console.print(f"[red]! '{category}/{tool_module}' 도구를 찾을 수 없습니다.[/red]")
                return

            # Context 구성
            ctx = ExecutionContext()
            ctx.category = category
            ctx.tool = ToolInfo(
                name=tool_meta.get("name", tool_module),
                description=tool_meta.get("description", ""),
                category=category,
                permission=tool_meta.get("permission", "read"),
                supports_single_region_only=tool_meta.get("supports_single_region_only", False),
                supports_single_account_only=tool_meta.get("supports_single_account_only", False),
                is_global=tool_meta.get("is_global", False),
            )

            # 세션이 필요한지 확인
            require_session = tool_meta.get("require_session", True)

            if require_session:
                # 프로파일/계정/역할/리전 선택
                ctx = ProfileStep().execute(ctx)

                if ctx.is_multi_account():
                    ctx = AccountStep().execute(ctx)

                if ctx.needs_role_selection():
                    ctx = RoleStep().execute(ctx)

                ctx = RegionStep().execute(ctx)

            # 실행
            self._execute_tool(ctx)

            # 이력 저장
            self._save_history(ctx)

            console.print()
            console.print("[dim]완료[/dim]")

        except KeyboardInterrupt:
            console.print()
            console.print("[dim]취소됨[/dim]")
        except Exception as e:
            console.print()
            console.print(f"[red]오류: {e}[/red]")
            if "--debug" in sys.argv:
                traceback.print_exc()

    def _find_tool_meta(
        self,
        category: str,
        tool_module: str,
    ) -> dict | None:
        """도구 메타데이터 조회"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True)

        for cat in categories:
            if cat["name"] == category:
                for tool_meta in cat.get("tools", []):
                    if not isinstance(tool_meta, dict):
                        continue
                    if tool_meta.get("module") == tool_module:
                        return tool_meta

        return None

    def _save_history(self, ctx: ExecutionContext) -> None:
        """실행 이력 저장"""
        if not ctx.tool or not ctx.category:
            return

        try:
            from core.tools.history import RecentHistory

            history = RecentHistory()
            tool_module = ""

            # 이름으로 모듈 찾기
            from core.tools.discovery import discover_categories

            for cat in discover_categories(include_aws_services=True):
                if cat["name"] == ctx.category:
                    for t in cat.get("tools", []):
                        if isinstance(t, dict) and t.get("name") == ctx.tool.name:
                            tool_module = t.get("module", "")
                            break
                    break

            if tool_module:
                history.add(
                    category=ctx.category,
                    tool_name=ctx.tool.name,
                    tool_module=tool_module,
                )

        except Exception as e:
            # 이력 저장 실패는 무시 (실행에 영향 없음)
            if "--debug" in sys.argv:
                console.print(f"[dim]이력 저장 실패: {e}[/dim]")

    def _run_once(self, entry_point: str | None = None) -> FlowResult:
        """한 번의 Flow 실행"""
        ctx = ExecutionContext()

        # Step 1: 카테고리/도구 선택 (이전 메뉴 지원)
        ctx = CategoryStep().execute(ctx, entry_point)

        # 도구에서 세션이 필요한지 확인
        tool_requires_session = self._tool_requires_session(ctx)

        if tool_requires_session:
            console.print()
            console.print("[dim]Ctrl+C: 취소[/dim]")

            # Step 2~4: 프로파일/계정/역할/리전 선택
            ctx = ProfileStep().execute(ctx)

            if ctx.is_multi_account():
                ctx = AccountStep().execute(ctx)

            if ctx.needs_role_selection():
                ctx = RoleStep().execute(ctx)

            ctx = RegionStep().execute(ctx)

        self._execute_tool(ctx)

        # 이력 저장
        self._save_history(ctx)

        return FlowResult(
            success=ctx.error is None,
            context=ctx,
            message=str(ctx.error) if ctx.error else "완료",
        )

    def _tool_requires_session(self, ctx: ExecutionContext) -> bool:
        """도구가 세션을 필요로 하는지 확인

        Returns:
            True: 프로파일/계정/역할/리전 선택 필요
            False: 세션 선택 스킵
        """
        if not ctx.tool or not ctx.category:
            return True  # 기본값: 세션 필요

        try:
            from core.tools.discovery import discover_categories

            categories = discover_categories(include_aws_services=True)
            for cat in categories:
                if cat["name"] == ctx.category:
                    tools = cat.get("tools", [])
                    for tool_meta in tools:
                        # tool_meta가 dict인지 확인
                        if not isinstance(tool_meta, dict):
                            continue
                        if tool_meta.get("name") == ctx.tool.name:
                            # require_session 옵션 확인 (기본값: True)
                            return bool(tool_meta.get("require_session", True))

            # 찾지 못하면 기본값 True
            return True
        except Exception as e:
            console.print(f"[yellow]도구 설정 확인 실패: {e}[/yellow]")
            return True

    def _execute_tool(self, ctx: ExecutionContext) -> None:
        """도구 실행 (discovery 기반)"""
        if not ctx.tool or not ctx.category:
            ctx.error = ValueError("도구 또는 카테고리가 선택되지 않음")
            return

        # discovery로 도구 로드
        try:
            from core.tools.discovery import load_tool

            tool = load_tool(ctx.category, ctx.tool.name)
        except ImportError as e:
            console.print(f"[red]discovery 모듈 로드 실패: {e}[/red]")
            ctx.error = e
            return

        if tool is None:
            console.print()
            console.print(f"[yellow]{ctx.category}/{ctx.tool.name} 도구를 찾을 수 없습니다.[/yellow]")
            return

        # 필요 권한 정보 추출
        required_permissions = tool.get("required_permissions")

        self._print_execution_summary(ctx, required_permissions)
        console.print()
        console.print("[dim]실행 중...[/dim]")
        console.print()

        try:
            # 도구 로드 결과 검증
            if not isinstance(tool, dict):
                raise TypeError(f"load_tool이 dict가 아닌 {type(tool).__name__}를 반환함")

            # 커스텀 옵션 수집 (있으면)
            collect_fn = tool.get("collect_options")
            if collect_fn:
                collect_fn(ctx)

            # 실행
            run_fn = tool.get("run")
            if not run_fn:
                raise ValueError("도구에 run 함수가 없습니다")
            ctx.result = run_fn(ctx)

        except Exception as e:
            ctx.error = e
            # AccessDenied 오류 시 권한 안내
            self._handle_permission_error(e, required_permissions)
            raise

    def _print_execution_summary(self, ctx: ExecutionContext, required_permissions: Any = None) -> None:
        """실행 전 요약 출력"""
        from cli.ui.console import print_box_end, print_box_line, print_box_start

        print_box_start("실행 요약")
        if ctx.tool:
            print_box_line(f" 도구: {ctx.tool.name}")
        if ctx.profile_name:
            print_box_line(f" 프로파일: {ctx.profile_name}")

        if ctx.role_selection:
            role_info = ctx.role_selection.primary_role
            if ctx.role_selection.fallback_role:
                role_info += f" / {ctx.role_selection.fallback_role}"
            print_box_line(f" Role: {role_info}")

        if ctx.regions:
            if len(ctx.regions) == 1:
                print_box_line(f" 리전: {ctx.regions[0]}")
            else:
                print_box_line(f" 리전: {len(ctx.regions)}개")

        if ctx.is_multi_account() and ctx.accounts:
            target_count = len(ctx.get_target_accounts())
            print_box_line(f" 계정: {target_count}개")

        # 필요 권한 표시
        if required_permissions:
            self._print_permissions_in_box(required_permissions)

        print_box_end()

    def _print_permissions_in_box(self, permissions: dict) -> None:
        """박스 내에 권한 목록 출력"""
        from cli.ui.console import print_box_line

        read_perms = permissions.get("read", [])
        write_perms = permissions.get("write", [])

        if not read_perms and not write_perms:
            return

        print_box_line(" 필요 권한:")
        if read_perms:
            for perm in read_perms:
                print_box_line(f"   [dim]•[/dim] {perm}")
        if write_perms:
            for perm in write_perms:
                print_box_line(f"   [yellow]•[/yellow] {perm} [dim](write)[/dim]")

    def _count_permissions(self, permissions: dict) -> int:
        """권한 개수 계산"""
        count = 0
        for perm_list in permissions.values():
            if isinstance(perm_list, list):
                count += len(perm_list)
        return count

    def _handle_permission_error(self, error: Exception, required_permissions: Any) -> None:
        """권한 오류 시 안내 메시지 출력"""
        # botocore ClientError에서 AccessDenied 확인
        error_code = None
        try:
            if hasattr(error, "response"):
                error_code = getattr(error, "response", {}).get("Error", {}).get("Code")
        except Exception:
            pass

        # AccessDenied 관련 오류인 경우에만 권한 안내
        access_denied_codes = {
            "AccessDenied",
            "AccessDeniedException",
            "UnauthorizedAccess",
            "UnauthorizedOperation",
            "AuthorizationError",
        }

        if error_code not in access_denied_codes:
            return

        console.print()
        console.print("[yellow]━━━ 권한 오류 ━━━[/yellow]")
        console.print(f"[red]{error_code}: 필요한 권한이 없습니다.[/red]")

        if required_permissions:
            console.print()
            console.print("[cyan]이 도구에 필요한 권한:[/cyan]")

            # read 권한
            read_perms = required_permissions.get("read", [])
            if read_perms:
                console.print("[dim]  Read:[/dim]")
                for perm in read_perms:
                    console.print(f"    - {perm}")

            # write 권한
            write_perms = required_permissions.get("write", [])
            if write_perms:
                console.print("[dim]  Write:[/dim]")
                for perm in write_perms:
                    console.print(f"    - {perm}")

            console.print()
            console.print("[dim]IAM 정책에 위 권한을 추가하거나 관리자에게 문의하세요.[/dim]")
        console.print("[yellow]━━━━━━━━━━━━━━━━━[/yellow]")


def create_flow_runner() -> FlowRunner:
    """FlowRunner 인스턴스 생성"""
    return FlowRunner()
