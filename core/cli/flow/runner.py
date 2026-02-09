# internal/flow/runner.py
"""
Flow Runner - CLI Flow의 전체 실행을 관리하는 핵심 모듈.

discovery 기반으로 도구를 자동 발견하고 실행합니다.
"""

import logging
import sys
import traceback
from typing import Any

from rich.console import Console

from core.cli.i18n import t
from core.cli.ui.console import clear_screen

from .context import ExecutionContext, FlowResult, ToolInfo
from .steps import AccountStep, CategoryStep, ProfileStep, RegionStep, RoleStep

logger = logging.getLogger(__name__)
console = Console()


class FlowRunner:
    """통합 CLI Flow Runner (discovery 기반)"""

    def run(self, entry_point: str | None = None) -> None:
        """Flow 실행"""
        while True:
            # 화면 클리어
            clear_screen()

            try:
                result = self._run_once(entry_point)

                if not result.success:
                    console.print(f"[red]{t('runner.execution_failed', message=result.message)}[/red]")

                console.print()

                # 다른 보고서 실행 여부 확인
                cont = console.input(f"[dim]{t('runner.run_another')}[/dim] > ").strip().lower()
                if cont == "n":
                    break

                entry_point = None

            except KeyboardInterrupt:
                console.print()
                console.print(f"[dim]{t('common.exit')}[/dim]")
                break
            except Exception as e:
                console.print()
                console.print(f"[red]{t('common.error')}: {e}[/red]")
                if "--debug" in sys.argv:
                    traceback.print_exc()
                console.print()

                cont = console.input(f"[dim]{t('runner.run_another')}[/dim] > ").strip().lower()
                if cont == "n":
                    break

                entry_point = None

    def run_tool_directly(
        self,
        category: str,
        tool_module: str,
        tool_name: str | None = None,
    ) -> None:
        """도구 직접 실행 (최근 사용/즐겨찾기에서 선택 시)

        Args:
            category: 카테고리 이름
            tool_module: 도구 모듈 이름
            tool_name: 도구 이름 (tool_module이 비어있을 때 폴백용)
        """
        # 화면 클리어
        clear_screen()

        try:
            # 도구 정보 조회
            tool_meta = self._find_tool_meta(category, tool_module, tool_name)
            if not tool_meta:
                console.print(f"[red]! {t('runner.tool_not_found', path=f'{category}/{tool_module}')}[/red]")
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
            console.print(f"[dim]{t('runner.done')}[/dim]")

        except KeyboardInterrupt:
            console.print()
            console.print(f"[dim]{t('runner.cancelled')}[/dim]")
        except Exception as e:
            console.print()
            console.print(f"[red]{t('common.error')}: {e}[/red]")
            if "--debug" in sys.argv:
                traceback.print_exc()

    def _find_tool_meta(
        self,
        category: str,
        tool_module: str,
        tool_name: str | None = None,
    ) -> dict | None:
        """도구 메타데이터 조회

        Args:
            category: 카테고리 이름
            tool_module: 도구 모듈 이름
            tool_name: 도구 이름 (tool_module이 비어있을 때 폴백용)
        """
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True)

        for cat in categories:
            if cat["name"] == category:
                for tool_meta in cat.get("tools", []):
                    if not isinstance(tool_meta, dict):
                        continue
                    # module 또는 ref 필드와 매칭 (ref만 정의된 도구 지원)
                    if tool_module and (tool_meta.get("module") == tool_module or tool_meta.get("ref") == tool_module):
                        return tool_meta
                    # tool_module이 비어있으면 tool_name으로 폴백
                    if not tool_module and tool_name and tool_meta.get("name") == tool_name:
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
                    for tool in cat.get("tools", []):
                        if isinstance(tool, dict) and tool.get("name") == ctx.tool.name:
                            # ref만 정의된 도구 지원
                            tool_module = tool.get("module") or tool.get("ref", "")
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
                console.print(f"[dim]{t('runner.history_save_failed', error=str(e))}[/dim]")

    def _run_once(self, entry_point: str | None = None) -> FlowResult:
        """한 번의 Flow 실행"""
        ctx = ExecutionContext()

        # Step 1: 카테고리/도구 선택 (이전 메뉴 지원)
        ctx = CategoryStep().execute(ctx, entry_point)

        # 도구에서 세션이 필요한지 확인
        tool_requires_session = self._tool_requires_session(ctx)

        if tool_requires_session:
            console.print()
            console.print(f"[dim]{t('runner.ctrl_c_hint')}[/dim]")

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
            message=str(ctx.error) if ctx.error else t("runner.done"),
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
            console.print(f"[yellow]{t('runner.tool_config_check_failed', error=str(e))}[/yellow]")
            return True

    def _execute_tool(self, ctx: ExecutionContext) -> None:
        """도구 실행 (discovery 기반, timeline 자동 래핑)"""
        if not ctx.tool or not ctx.category:
            ctx.error = ValueError(t("runner.tool_or_category_not_selected"))
            return

        # discovery로 도구 로드
        try:
            from core.tools.discovery import load_tool

            tool = load_tool(ctx.category, ctx.tool.name)
        except ImportError as e:
            console.print(f"[red]{t('runner.tool_load_failed', error=str(e))}[/red]")
            ctx.error = e
            return

        if tool is None:
            console.print()
            console.print(f"[yellow]{t('runner.tool_not_found', path=f'{ctx.category}/{ctx.tool.name}')}[/yellow]")
            return

        # 필요 권한 정보 추출
        required_permissions = tool.get("required_permissions")

        self._print_execution_summary(ctx, required_permissions)
        console.print()
        console.print(f"[dim]{t('runner.executing')}[/dim]")
        console.print()

        try:
            # 도구 로드 결과 검증
            if not isinstance(tool, dict):
                raise TypeError(f"load_tool returned {type(tool).__name__} instead of dict")

            run_fn = tool.get("run")
            if not run_fn:
                raise ValueError(t("runner.no_run_function"))

            # collect_options는 대화형이므로 timeline 밖에서 먼저 실행
            collect_fn = tool.get("collect_options")
            if collect_fn:
                collect_fn(ctx)

            # 타임라인 phases 결정 (빈 리스트면 timeline 없이 실행)
            phases = _build_phases(tool)

            if not phases:
                # 대화형/메뉴 도구: timeline 없이 바로 실행
                ctx.result = run_fn(ctx)
            else:
                # 타임라인 래핑 실행
                self._execute_with_timeline(ctx, run_fn, phases)

        except Exception as e:
            ctx._timeline = None
            ctx.error = e
            # AccessDenied 오류 시 권한 안내
            self._handle_permission_error(e, required_permissions)
            raise

    def _execute_with_timeline(self, ctx: ExecutionContext, run_fn: Any, phases: list[str]) -> None:
        """타임라인 래핑으로 도구 실행

        parallel_collect 사용 도구는 내부에서 자동으로:
        1. 수집 phase 프로그레스 표시
        2. 수집 완료 후 Live 중단 (도구 출력과 겹침 방지)
        """
        from core.cli.ui.timeline import timeline_progress

        with timeline_progress(phases, console=console) as tl:
            ctx._timeline = tl

            # Phase 0: 수집 (run)
            tl.activate_phase(0)
            ctx._timeline_collect_phase = 0
            ctx.result = run_fn(ctx)

            # run_fn 완료 후 Live가 아직 살아있으면 정리
            # (parallel_collect 미사용 도구인 경우)
            if tl._live is not None:
                tl.complete_phase(0)
                tl.stop()

            ctx._timeline = None

    def _print_execution_summary(self, ctx: ExecutionContext, required_permissions: Any = None) -> None:
        """실행 전 요약 출력"""
        from core.cli.ui.console import print_box_end, print_box_line, print_box_start

        print_box_start(t("runner.execution_summary"))
        if ctx.tool:
            print_box_line(f" {t('runner.summary_tool')}: {ctx.tool.name}")
        if ctx.profile_name:
            print_box_line(f" {t('runner.summary_profile')}: {ctx.profile_name}")

        if ctx.role_selection:
            role_info = ctx.role_selection.primary_role
            if ctx.role_selection.fallback_role:
                role_info += f" / {ctx.role_selection.fallback_role}"
            print_box_line(f" {t('runner.summary_role')}: {role_info}")

        if ctx.regions:
            if len(ctx.regions) == 1:
                print_box_line(f" {t('runner.summary_region')}: {ctx.regions[0]}")
            else:
                print_box_line(
                    f" {t('runner.summary_region')}: {t('runner.summary_regions_count', count=len(ctx.regions))}"
                )

        if ctx.is_multi_account() and ctx.accounts:
            target_count = len(ctx.get_target_accounts())
            print_box_line(f" {t('runner.summary_accounts')}: {t('runner.summary_accounts_count', count=target_count)}")

        # 필요 권한 표시
        if required_permissions:
            self._print_permissions_in_box(required_permissions)

        print_box_end()

    def _print_permissions_in_box(self, permissions: dict) -> None:
        """박스 내에 권한 목록 출력"""
        from core.cli.ui.console import print_box_line

        read_perms = permissions.get("read", [])
        write_perms = permissions.get("write", [])

        if not read_perms and not write_perms:
            return

        print_box_line(f" {t('runner.required_permissions')}")
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
        except Exception as e:
            logger.debug("Failed to extract error code: %s", e)

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
        console.print(f"[yellow]━━━ {t('runner.permission_error_title')} ━━━[/yellow]")
        console.print(f"[red]{t('runner.permission_missing', code=error_code)}[/red]")

        if required_permissions:
            console.print()
            console.print(f"[#FF9900]{t('runner.tool_required_permissions')}[/#FF9900]")

            # read 권한
            read_perms = required_permissions.get("read", [])
            if read_perms:
                console.print(f"[dim]  {t('runner.permission_read')}[/dim]")
                for perm in read_perms:
                    console.print(f"    - {perm}")

            # write 권한
            write_perms = required_permissions.get("write", [])
            if write_perms:
                console.print(f"[dim]  {t('runner.permission_write')}[/dim]")
                for perm in write_perms:
                    console.print(f"    - {perm}")

            console.print()
            console.print(f"[dim]{t('runner.contact_admin')}[/dim]")
        console.print("[yellow]━━━━━━━━━━━━━━━━━[/yellow]")


def _build_phases(tool: dict) -> list[str]:
    """도구 메타데이터에서 타임라인 phases를 결정

    Args:
        tool: load_tool()이 반환한 도구 딕셔너리
              tool["meta"]에 TOOLS 배열의 메타데이터가 들어있음

    Returns:
        Phase 이름 리스트. 빈 리스트면 timeline 없이 실행.
    """
    meta = tool.get("meta") or {}

    # 도구가 명시적으로 timeline_phases를 정의한 경우
    if "timeline_phases" in meta:
        return list(meta["timeline_phases"])

    # 대화형/메뉴 도구: timeline 비활성화
    if meta.get("is_menu"):
        return []

    # 세션 불필요 도구 (대부분 대화형): timeline 비활성화
    if meta.get("require_session") is False:
        return []

    # 기본값: 수집만 표시 (보고서는 도구 내부에서 자체 출력)
    return ["수집"]


def create_flow_runner() -> FlowRunner:
    """FlowRunner 인스턴스 생성"""
    return FlowRunner()
