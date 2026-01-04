# cli/flow/steps/region.py
"""
리전 선택 Step

단일 리전, 복수 리전, 전체 리전 중 선택.
"""

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

        print_box_start(f"리전 ({len(all_regions_for_selection)}개)")

        # 3열 레이아웃 (리전 코드만)
        cols = 3
        rows = (len(all_regions_for_selection) + cols - 1) // cols
        for row in range(rows):
            line_parts = []
            for col in range(cols):
                idx = row + col * rows
                if idx < len(all_regions_for_selection):
                    num = idx + 1
                    region = all_regions_for_selection[idx]
                    mark = "*" if region == self.default_region else " "
                    line_parts.append(f"{num:>2}){mark}{region:<15}")
            print_box_line(" " + "".join(line_parts))

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

    def _select_multiple_regions(self) -> list[str]:
        """복수 리전 선택 UI (2개 이상)"""
        console.print()

        # 자주 사용하는 리전 우선 표시
        common_region_codes = [region for region, _ in COMMON_REGIONS]
        other_regions = [r for r in ALL_REGIONS if r not in common_region_codes]
        all_regions = common_region_codes + other_regions

        print_box_start(f"리전 ({len(all_regions)}개)")

        # 3열 레이아웃 (리전 코드만)
        cols = 3
        rows = (len(all_regions) + cols - 1) // cols
        for row in range(rows):
            line_parts = []
            for col in range(cols):
                idx = row + col * rows
                if idx < len(all_regions):
                    num = idx + 1
                    region = all_regions[idx]
                    line_parts.append(f"{num:>2}) {region:<16}")
            print_box_line(" " + "".join(line_parts))

        print_box_line()
        print_box_line("[dim]번호 (쉼표 구분) | a: 전체[/dim]")
        print_box_end()

        while True:
            choice = console.input("> ").strip().lower()

            if not choice:
                continue

            if choice == "a":
                return all_regions.copy()

            # 번호 파싱 및 즉시 반환
            try:
                nums = [int(n) for n in choice.replace(",", " ").split()]
                selected = []
                for num in nums:
                    if 1 <= num <= len(all_regions):
                        region = all_regions[num - 1]
                        if region not in selected:
                            selected.append(region)

                if len(selected) < 2:
                    console.print("[yellow]2개 이상 선택해주세요[/yellow]")
                    continue

                return selected
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _print_summary(self, regions: list[str]) -> None:
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
