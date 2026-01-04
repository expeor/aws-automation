# internal/flow/steps/role.py
"""
Role 선택 Step (SSO 전용)

SSO 멀티계정 환경에서 사용할 Role을 선택.
모든 계정에서 공통으로 사용할 Role을 선택하고,
해당 Role이 없는 계정을 위한 Fallback 설정을 지원.
"""

from collections import defaultdict

from rich.console import Console

from cli.ui.console import print_box_end, print_box_line, print_box_start

from ..context import ExecutionContext, FallbackStrategy, RoleSelection

console = Console()


class RoleStep:
    """Role 선택 Step (SSO 전용)

    SSO 멀티계정 환경에서:
    1. 모든 계정의 Role을 집계
    2. 사용자가 Primary Role 선택
    3. Primary Role이 없는 계정에 대한 Fallback 처리
    """

    def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        """Role 선택 실행

        Args:
            ctx: 실행 컨텍스트 (accounts가 로드되어 있어야 함)

        Returns:
            업데이트된 컨텍스트 (role_selection 설정)
        """
        if not ctx.needs_role_selection():
            # SSO Session이 아니면 스킵 (SSO Profile은 역할 고정)
            return ctx

        if not ctx.accounts:
            console.print("[yellow]* 계정 목록이 없습니다.[/yellow]")
            return ctx

        # 모든 계정에서 사용 가능한 Role 집계
        role_account_map = self._aggregate_roles(ctx)

        if not role_account_map:
            console.print("[red]! 사용 가능한 Role이 없습니다.[/red]")
            raise RuntimeError("Role 없음")

        # Primary Role 선택
        primary_role = self._select_primary_role(role_account_map, len(ctx.accounts))

        # Primary Role이 모든 계정에 있으면 Fallback 불필요
        primary_accounts = set(role_account_map[primary_role])
        all_account_ids = {acc.id for acc in ctx.accounts}
        missing_accounts = all_account_ids - primary_accounts

        if not missing_accounts:
            # 모든 계정에 Primary Role 있음
            ctx.role_selection = RoleSelection(
                primary_role=primary_role,
                role_account_map=role_account_map,
            )
            console.print(f"[green]> 모든 계정에서 '{primary_role}' 사용[/green]")
            return ctx

        # Fallback 처리 필요
        fallback_role, strategy = self._handle_fallback(
            primary_role=primary_role,
            missing_accounts=missing_accounts,
            role_account_map=role_account_map,
            total_accounts=len(ctx.accounts),
        )

        # 스킵할 계정 결정
        skipped = []
        if strategy == FallbackStrategy.SKIP_ACCOUNT:
            skipped = list(missing_accounts)
        elif fallback_role:
            # Fallback Role도 없는 계정은 스킵
            fallback_accounts = set(role_account_map.get(fallback_role, []))
            still_missing = missing_accounts - fallback_accounts
            skipped = list(still_missing)

        ctx.role_selection = RoleSelection(
            primary_role=primary_role,
            fallback_role=fallback_role,
            fallback_strategy=strategy,
            role_account_map=role_account_map,
            skipped_accounts=skipped,
        )

        # 결과 출력
        self._print_summary(ctx.role_selection, len(ctx.accounts))

        return ctx

    def _aggregate_roles(self, ctx: ExecutionContext) -> dict[str, list[str]]:
        """모든 계정에서 사용 가능한 Role 집계

        Returns:
            role_name -> [account_ids] 매핑
        """
        role_account_map: dict[str, list[str]] = defaultdict(list)

        console.print("[dim]Role 수집 중...[/dim]")

        for account in ctx.accounts:
            roles = getattr(account, "roles", [])
            for role in roles:
                role_name = role if isinstance(role, str) else role.role_name
                role_account_map[role_name].append(account.id)

        console.print(f"[dim]{len(role_account_map)}개 Role[/dim]")

        return dict(role_account_map)

    def _select_primary_role(
        self,
        role_account_map: dict[str, list[str]],
        total_accounts: int,
    ) -> str:
        """Primary Role 선택 UI"""
        # 이름순 정렬
        sorted_roles = sorted(
            role_account_map.items(),
            key=lambda x: x[0].lower(),
        )

        print_box_start(f"Role 선택 ({len(sorted_roles)}개)")

        # 2열 레이아웃
        half = (len(sorted_roles) + 1) // 2
        for i in range(half):
            left_idx = i + 1
            left_name, left_ids = sorted_roles[i]
            left_pct = len(left_ids) / total_accounts * 100
            left_str = f"{left_idx:>2}) {left_name[:18]:<18} {left_pct:>3.0f}%"

            if i + half < len(sorted_roles):
                right_idx = i + half + 1
                right_name, right_ids = sorted_roles[i + half]
                right_pct = len(right_ids) / total_accounts * 100
                right_str = f"{right_idx:>2}) {right_name[:18]:<18} {right_pct:>3.0f}%"
                print_box_line(f" {left_str}  {right_str}")
            else:
                print_box_line(f" {left_str}")

        print_box_end()

        # 번호로 선택
        while True:
            answer = console.input("> ").strip()

            if not answer:
                continue

            try:
                num = int(answer)
                if 1 <= num <= len(sorted_roles):
                    return sorted_roles[num - 1][0]
                console.print(f"[dim]1-{len(sorted_roles)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _handle_fallback(
        self,
        primary_role: str,
        missing_accounts: set[str],
        role_account_map: dict[str, list[str]],
        total_accounts: int,
    ) -> tuple:
        """Fallback 처리

        Returns:
            (fallback_role, strategy) 튜플
        """
        missing_count = len(missing_accounts)

        console.print(f"[yellow]{primary_role} 미지원 계정: {missing_count}개[/yellow]")

        # Fallback 후보 찾기
        fallback_candidates = []
        for role_name, account_ids in role_account_map.items():
            if role_name == primary_role:
                continue
            covers = len(missing_accounts & set(account_ids))
            if covers > 0:
                fallback_candidates.append((role_name, covers, account_ids))

        fallback_candidates.sort(key=lambda x: x[1], reverse=True)

        if not fallback_candidates:
            console.print("[dim]Fallback 없음 - 해당 계정 스킵[/dim]")
            confirm = (
                console.input(f"[dim]{missing_count}개 스킵? [y/N][/dim] > ")
                .strip()
                .lower()
            )
            if confirm != "y":
                raise KeyboardInterrupt("사용자 취소")
            return None, FallbackStrategy.SKIP_ACCOUNT

        best_fallback = fallback_candidates[0]

        print_box_start("Fallback 설정")
        print_box_line(f" 1) {best_fallback[0]} (권장, {best_fallback[1]}개 커버)")
        print_box_line(" 2) 다른 Role 선택")
        print_box_line(f" 3) {missing_count}개 계정 스킵")
        print_box_end()

        while True:
            action = console.input("> ").strip()

            if action == "1":
                return best_fallback[0], FallbackStrategy.USE_FALLBACK
            elif action == "3":
                return None, FallbackStrategy.SKIP_ACCOUNT
            elif action == "2":
                # Fallback Role 선택
                print_box_start("Fallback Role")
                for i, (role, covers, _) in enumerate(fallback_candidates, 1):
                    print_box_line(f" {i}) {role} ({covers}개)")
                print_box_end()

                while True:
                    role_input = console.input("> ").strip()
                    try:
                        idx = int(role_input)
                        if 1 <= idx <= len(fallback_candidates):
                            return (
                                fallback_candidates[idx - 1][0],
                                FallbackStrategy.USE_FALLBACK,
                            )
                        console.print(f"[dim]1-{len(fallback_candidates)} 범위[/dim]")
                    except ValueError:
                        console.print("[dim]숫자 입력[/dim]")
            elif action:
                console.print("[dim]1-3 입력[/dim]")

    def _print_summary(self, rs: RoleSelection, total: int) -> None:
        """선택 결과 요약 출력"""
        console.print()
        total - len(rs.skipped_accounts)
        summary = f"[dim]Role:[/dim] {rs.primary_role}"
        if rs.fallback_role:
            summary += f" / Fallback: {rs.fallback_role}"
        if rs.skipped_accounts:
            summary += f" / 스킵: {len(rs.skipped_accounts)}개"
        console.print(summary)
