# internal/flow/steps/account.py
"""
계정 선택 Step (SSO 전용)

SSO 멀티계정 환경에서 작업할 계정을 선택.
"""

from typing import List

from rich.console import Console

from cli.ui.console import print_box_end, print_box_line, print_box_start

from ..context import ExecutionContext

console = Console()


class AccountStep:
    """계정 선택 Step (SSO 전용)

    SSO 멀티계정 환경에서:
    1. 사용 가능한 계정 목록 표시
    2. 사용자가 계정 선택 (단일/다중/전체)

    supports_single_account_only 옵션:
    - True: 단일 계정만 선택 가능 (ALB 로그 분석 등)
    - False: 다중 계정 선택 가능 (기본값)
    """

    def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        """계정 선택 실행

        Args:
            ctx: 실행 컨텍스트 (accounts가 로드되어 있어야 함)

        Returns:
            업데이트된 컨텍스트 (accounts가 선택된 계정만 포함)
        """
        if not ctx.accounts:
            console.print("[yellow]* 계정 목록이 없습니다.[/yellow]")
            return ctx

        # 계정이 1개면 자동 선택
        if len(ctx.accounts) == 1:
            account = ctx.accounts[0]
            console.print()
            console.print(f"[dim]계정:[/dim] {account.name} ({account.id})")
            return ctx

        # 단일 계정만 지원하는 도구인지 확인
        is_single_account_only = bool(
            ctx.tool and ctx.tool.supports_single_account_only
        )

        # 계정 선택 UI
        selected_accounts = self._select_accounts(
            ctx.accounts, single_only=is_single_account_only
        )
        ctx.accounts = selected_accounts

        return ctx

    def _select_accounts(self, accounts: list, single_only: bool = False) -> list:
        """계정 선택 UI

        Args:
            accounts: AccountInfo 목록
            single_only: 단일 계정만 선택 가능 여부

        Returns:
            선택된 AccountInfo 목록
        """
        # 이름순 정렬
        sorted_accounts = sorted(accounts, key=lambda x: x.name.lower())

        # 박스로 계정 목록 표시
        print_box_start(f"계정 선택 ({len(sorted_accounts)}개)")

        if single_only:
            print_box_line("[yellow]단일 계정만 지원[/yellow]")
            print_box_line()

        # 2열 레이아웃
        half = (len(sorted_accounts) + 1) // 2
        for i in range(half):
            left_idx = i + 1
            left = sorted_accounts[i]
            left_str = f"{left_idx:>2}) {left.name[:20]:<20} {left.id}"

            if i + half < len(sorted_accounts):
                right_idx = i + half + 1
                right = sorted_accounts[i + half]
                right_str = f"{right_idx:>2}) {right.name[:20]:<20} {right.id}"
                print_box_line(f" {left_str}  {right_str}")
            else:
                print_box_line(f" {left_str}")

        print_box_line()
        if single_only:
            print_box_line(f"[dim]번호 입력 (1-{len(sorted_accounts)})[/dim]")
        else:
            print_box_line("[dim]번호 (1,2,3 / 1-5) | all: 전체[/dim]")
        print_box_end()

        while True:
            selection = console.input("> ").strip()

            if not selection:
                continue

            selection = selection.lower()

            # 단일 계정 모드에서 all 입력 방지
            if single_only and selection == "all":
                console.print("[dim]단일 계정만 지원[/dim]")
                continue

            # 전체 선택 (다중 모드에서만)
            if selection == "all":
                console.print(f"[dim]{len(sorted_accounts)}개 전체 선택[/dim]")
                return sorted_accounts

            # 번호 파싱
            try:
                indices = self._parse_selection(
                    selection, len(sorted_accounts), single_only=single_only
                )
                if not indices:
                    console.print("[dim]올바른 번호 입력[/dim]")
                    continue

                selected = [sorted_accounts[i - 1] for i in indices]

                # 결과 출력
                console.print()
                if len(selected) == 1:
                    acc = selected[0]
                    console.print(f"[dim]계정:[/dim] {acc.name} ({acc.id})")
                else:
                    console.print(f"[dim]{len(selected)}개 계정 선택[/dim]")

                return selected

            except ValueError as e:
                console.print(f"[dim]{e}[/dim]")
                continue

    def _parse_selection(
        self, selection: str, max_num: int, single_only: bool = False
    ) -> List[int]:
        """선택 문자열 파싱

        Args:
            selection: 사용자 입력 (예: "1,2,3" 또는 "1-5")
            max_num: 최대 번호
            single_only: 단일 선택만 허용

        Returns:
            선택된 인덱스 목록 (1-based)
        """
        indices = set()

        # 쉼표로 분리
        parts = [p.strip() for p in selection.split(",")]

        # 단일 모드에서 여러 입력 방지
        if single_only and len(parts) > 1:
            raise ValueError("단일 계정만 선택 가능합니다")

        for part in parts:
            if not part:
                continue

            # 범위 (1-5)
            if "-" in part:
                # 단일 모드에서 범위 입력 방지
                if single_only:
                    raise ValueError("단일 계정만 선택 가능합니다")

                range_parts = part.split("-")
                if len(range_parts) != 2:
                    raise ValueError(f"잘못된 범위 형식: {part}")

                try:
                    start = int(range_parts[0].strip())
                    end = int(range_parts[1].strip())
                except ValueError:
                    raise ValueError(f"잘못된 숫자: {part}")

                if start > end:
                    start, end = end, start

                for i in range(start, end + 1):
                    if 1 <= i <= max_num:
                        indices.add(i)
                    else:
                        raise ValueError(f"범위 벗어남: {i} (1-{max_num})")
            else:
                # 단일 번호
                try:
                    num = int(part)
                except ValueError:
                    raise ValueError(f"잘못된 숫자: {part}")

                if 1 <= num <= max_num:
                    indices.add(num)
                else:
                    raise ValueError(f"범위 벗어남: {num} (1-{max_num})")

        # 단일 모드에서 여러 결과 방지 (안전장치)
        if single_only and len(indices) > 1:
            raise ValueError("단일 계정만 선택 가능합니다")

        return sorted(indices)
