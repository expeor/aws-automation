# cli/flow/steps/region.py
"""
리전 선택 Step

단일 리전, 복수 리전, 전체 리전 중 선택.
"""

from typing import List

from rich.console import Console

from cli.ui.console import print_box_end, print_box_line, print_box_start
from core.region.data import ALL_REGIONS, COMMON_REGIONS, REGION_NAMES

from ..context import ExecutionContext

console = Console()


class RegionStep:
    """리전 선택 Step

    선택 모드:
    - 현재 리전만 (기본 리전)
    - 여러 리전 선택
    - 모든 리전
    """

    def __init__(self, default_region: str = "ap-northeast-2"):
        self.default_region = default_region

    def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        """리전 선택 실행

        Args:
            ctx: 실행 컨텍스트

        Returns:
            업데이트된 컨텍스트 (regions 설정)
        """
        # Global 서비스인 경우 리전 선택 스킵 (IAM, Route53 등)
        if ctx.tool and ctx.tool.is_global:
            # Global 서비스는 us-east-1 사용 (IAM API 엔드포인트)
            ctx.regions = ["us-east-1"]
            console.print()
            console.print("[dim]리전:[/dim] Global (us-east-1)")
            return ctx

        # 단일 리전만 지원하는 도구인지 확인
        is_single_region_only = ctx.tool and ctx.tool.supports_single_region_only

        # 선택 모드 (번호 입력 방식)
        if is_single_region_only:
            modes = [
                f"현재 리전 ({self.default_region})",
                "다른 리전 선택",
            ]
        else:
            modes = [
                f"현재 리전 ({self.default_region})",
                "다른 리전 1개 선택",
                "여러 리전 선택 (2개 이상)",
                f"모든 리전 ({len(ALL_REGIONS)}개)",
            ]

        print_box_start("리전 선택")
        if is_single_region_only:
            print_box_line("[yellow]단일 리전만 지원[/yellow]")
            print_box_line()

        for i, mode_title in enumerate(modes, 1):
            print_box_line(f" {i}) {mode_title}")

        print_box_end()

        # 번호로 선택
        while True:
            answer = console.input("> ").strip()

            if not answer:
                continue

            try:
                num = int(answer)
                if 1 <= num <= len(modes):
                    mode = num
                    break
                else:
                    console.print(f"[dim]1-{len(modes)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

        # 모드별 처리
        if is_single_region_only:
            # 단일 리전만 지원하는 경우
            if mode == 1:  # 현재 리전
                ctx.regions = [self.default_region]
            else:  # 다른 리전 선택
                ctx.regions = [self._select_single_region()]
        else:
            # 다중 리전 지원하는 경우
            if mode == 1:  # 현재 리전
                ctx.regions = [self.default_region]
            elif mode == 2:  # 다른 리전 1개
                ctx.regions = [self._select_single_region()]
            elif mode == 4:  # 모든 리전
                ctx.regions = ALL_REGIONS.copy()
            else:  # 여러 리전 (2개 이상)
                ctx.regions = self._select_multiple_regions()

        # 결과 출력
        self._print_summary(ctx.regions)

        return ctx

    def _select_single_region(self) -> str:
        """단일 리전 선택 UI (번호 입력 방식)"""
        console.print()

        # 자주 사용하는 리전을 우선 표시
        common_region_codes = [region for region, _ in COMMON_REGIONS]
        other_regions = [r for r in ALL_REGIONS if r not in common_region_codes]
        all_regions_for_selection = common_region_codes + other_regions

        print_box_start(f"리전 선택 ({len(all_regions_for_selection)}개)")

        # 2열 레이아웃
        half = (len(all_regions_for_selection) + 1) // 2
        for i in range(half):
            left_idx = i + 1
            left = all_regions_for_selection[i]
            left_name = REGION_NAMES.get(left, "")[:8]
            left_mark = "*" if left == self.default_region else " "
            left_str = f"{left_idx:>2}){left_mark}{left:<16} {left_name:<8}"

            if i + half < len(all_regions_for_selection):
                right_idx = i + half + 1
                right = all_regions_for_selection[i + half]
                right_name = REGION_NAMES.get(right, "")[:8]
                right_str = f"{right_idx:>2}) {right:<16} {right_name}"
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
                if 1 <= num <= len(all_regions_for_selection):
                    return all_regions_for_selection[num - 1]
                else:
                    console.print(f"[dim]1-{len(all_regions_for_selection)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _select_multiple_regions(self) -> List[str]:
        """복수 리전 선택 UI (2개 이상)"""
        console.print()

        # 자주 사용하는 리전 우선 표시
        common_region_codes = [region for region, _ in COMMON_REGIONS]
        other_regions = [r for r in ALL_REGIONS if r not in common_region_codes]
        all_regions = common_region_codes + other_regions

        # 빈 상태에서 시작 (사용자가 직접 선택)
        selected_indices = set()

        def display():
            print_box_start(f"리전 선택 ({len(all_regions)}개)")

            # 2열 레이아웃
            half = (len(all_regions) + 1) // 2
            for i in range(half):
                left_idx = i + 1
                left = all_regions[i]
                left_check = "[green]v[/green]" if i in selected_indices else " "
                left_name = REGION_NAMES.get(left, "")[:6]
                left_str = f"{left_idx:>2}){left_check}{left:<14} {left_name:<6}"

                if i + half < len(all_regions):
                    right_idx = i + half + 1
                    right = all_regions[i + half]
                    right_check = (
                        "[green]v[/green]" if (i + half) in selected_indices else " "
                    )
                    right_name = REGION_NAMES.get(right, "")[:6]
                    right_str = f"{right_idx:>2}){right_check}{right:<14} {right_name}"
                    print_box_line(f" {left_str}  {right_str}")
                else:
                    print_box_line(f" {left_str}")

            print_box_line()
            count_display = f"{len(selected_indices)}개" if len(selected_indices) >= 2 else f"{len(selected_indices)}개 [yellow](2개 이상 필요)[/yellow]"
            print_box_line(
                f"[dim]번호: 토글 | a: 전체 | d: 완료 ({count_display})[/dim]"
            )
            print_box_end()

        display()

        while True:
            choice = console.input("> ").strip().lower()

            if not choice:
                continue

            if choice == "d":
                if len(selected_indices) < 2:
                    console.print("[yellow]2개 이상 선택해주세요[/yellow]")
                    continue
                return [all_regions[i] for i in sorted(selected_indices)]

            if choice == "a":
                if len(selected_indices) == len(all_regions):
                    selected_indices.clear()
                else:
                    selected_indices = set(range(len(all_regions)))
                display()
                continue

            # 번호 토글
            try:
                nums = [int(n) for n in choice.replace(",", " ").split()]
                for num in nums:
                    if 1 <= num <= len(all_regions):
                        idx = num - 1
                        if idx in selected_indices:
                            selected_indices.discard(idx)
                        else:
                            selected_indices.add(idx)
                display()
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _print_summary(self, regions: List[str]) -> None:
        """선택 결과 출력"""
        console.print()

        if len(regions) == 1:
            region = regions[0]
            name = REGION_NAMES.get(region, "")
            if name:
                console.print(f"[dim]리전:[/dim] {region} ({name})")
            else:
                console.print(f"[dim]리전:[/dim] {region}")
        elif len(regions) == len(ALL_REGIONS):
            console.print(f"[dim]리전:[/dim] 전체 {len(regions)}개")
        else:
            console.print(f"[dim]리전:[/dim] {len(regions)}개")
