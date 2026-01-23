# internal/flow/steps/role.py
"""
Role 선택 Step (SSO 전용)

SSO 멀티계정 환경에서 사용할 Role을 선택.
모든 계정에서 공통으로 사용할 Role을 선택하고,
해당 Role이 없는 계정을 위한 Fallback 설정을 지원.
"""

from collections import defaultdict

from rich.console import Console

from cli.i18n import t
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
            console.print(f"[yellow]* {t('flow.no_accounts')}[/yellow]")
            return ctx

        # 모든 계정에서 사용 가능한 Role 집계
        role_account_map = self._aggregate_roles(ctx)

        if not role_account_map:
            console.print(f"[red]! {t('flow.no_roles_available')}[/red]")
            raise RuntimeError(t('flow.no_roles_error'))

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
            console.print(f"[green]> {t('flow.all_accounts_use_role', role=primary_role)}[/green]")
            return ctx

        # Fallback 처리 필요
        fallback_role, strategy = self._handle_fallback(
            primary_role=primary_role,
            missing_accounts=missing_accounts,
            role_account_map=role_account_map,
            total_accounts=len(ctx.accounts),
            accounts=ctx.accounts,
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

        console.print(f"[dim]{t('flow.collecting_roles')}[/dim]")

        for account in ctx.accounts:
            roles = getattr(account, "roles", [])
            for role in roles:
                role_name = role if isinstance(role, str) else role.role_name
                role_account_map[role_name].append(account.id)

        console.print(f"[dim]{t('flow.roles_count', count=len(role_account_map))}[/dim]")

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

        print_box_start(t('flow.role_selection', count=len(sorted_roles)))

        # 1열 레이아웃 (Role 이름 전체 표시)
        for idx, (role_name, account_ids) in enumerate(sorted_roles, 1):
            pct = len(account_ids) / total_accounts * 100
            account_count = len(account_ids)
            print_box_line(f"  {idx:>2}) {role_name:<40} {t('flow.count_pct', count=account_count, pct=f'{pct:.0f}')}")

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
                console.print(f"[dim]{t('flow.number_range_hint', max=len(sorted_roles))}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('flow.enter_number')}[/dim]")

    def _handle_fallback(
        self,
        primary_role: str,
        missing_accounts: set[str],
        role_account_map: dict[str, list[str]],
        total_accounts: int,
        accounts: list | None = None,
    ) -> tuple:
        """Fallback 처리

        Returns:
            (fallback_role, strategy) 튜플
        """
        missing_count = len(missing_accounts)

        console.print(f"[yellow]{t('flow.role_unsupported_accounts', role=primary_role, count=missing_count)}[/yellow]")

        # 미지원 계정 목록 표시
        if accounts:
            account_map = {acc.id: acc.name for acc in accounts}
            missing_names = [account_map.get(acc_id, acc_id) for acc_id in sorted(missing_accounts)]
            console.print(f"[dim]  → {', '.join(missing_names)}[/dim]")

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
            console.print(f"[dim]{t('flow.no_fallback_skip')}[/dim]")
            console.print(f"[dim]{t('flow.skip_accounts_confirm', count=missing_count)}[/dim]")
            confirm = console.input("> ").strip().lower()
            if confirm != "y":
                console.print(f"[yellow]{t('flow.terminated')}[/yellow]")
                raise KeyboardInterrupt(t('flow.user_cancelled'))
            return None, FallbackStrategy.SKIP_ACCOUNT

        best_fallback = fallback_candidates[0]

        print_box_start(t('flow.fallback_setup'))
        print_box_line(f"  1) {best_fallback[0]:<40} ({t('flow.recommended_covers', count=best_fallback[1])})")
        print_box_line(f"  2) {t('flow.select_other_role')}")
        print_box_line(f"  3) {t('flow.skip_accounts', count=missing_count)}")
        print_box_end()

        while True:
            action = console.input("> ").strip()

            if action == "1":
                return best_fallback[0], FallbackStrategy.USE_FALLBACK
            elif action == "3":
                return None, FallbackStrategy.SKIP_ACCOUNT
            elif action == "2":
                # Fallback Role 선택
                print_box_start(t('flow.select_fallback_role'))
                for i, (role, covers, _) in enumerate(fallback_candidates, 1):
                    print_box_line(f"  {i:>2}) {role:<40} ({t('flow.covers_count', count=covers)})")
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
                        console.print(f"[dim]{t('flow.number_range_hint', max=len(fallback_candidates))}[/dim]")
                    except ValueError:
                        console.print(f"[dim]{t('flow.enter_number')}[/dim]")
            elif action:
                console.print(f"[dim]{t('flow.enter_1_to_3')}[/dim]")

    def _print_summary(self, rs: RoleSelection, total: int) -> None:
        """선택 결과 요약 출력"""
        console.print()
        total - len(rs.skipped_accounts)
        summary = f"[dim]{t('flow.role_label')}[/dim] {rs.primary_role}"
        if rs.fallback_role:
            summary += f" / {t('flow.fallback_label')} {rs.fallback_role}"
        if rs.skipped_accounts:
            summary += f" / {t('flow.skipped_count', count=len(rs.skipped_accounts))}"
        console.print(summary)
