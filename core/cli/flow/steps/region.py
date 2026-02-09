# cli/flow/steps/region.py
"""
리전 선택 Step

단일 리전, 복수 리전, 전체 리전 중 선택.
"""

from rich.console import Console

from core.cli.i18n import t
from core.cli.ui.console import clear_screen, print_box_end, print_box_line, print_box_start
from core.region.data import ALL_REGIONS, REGION_NAMES

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
            console.print(f"[dim]{t('flow.region_label')}[/dim] {t('flow.region_global')}")
            return ctx

        # 단일 리전만 지원하는 도구인지 확인
        is_single_region_only = ctx.tool and ctx.tool.supports_single_region_only

        # 선택 모드 (번호 입력 방식)
        if is_single_region_only:
            modes = [
                t("flow.current_region", region=self.default_region),
                t("flow.select_other_region"),
            ]
        else:
            modes = [
                t("flow.current_region", region=self.default_region),
                t("flow.select_other_region"),
                t("flow.all_regions", count=len(ALL_REGIONS)),
            ]

        # 화면 클리어 (Global 서비스 제외)
        clear_screen()

        print_box_start(t("flow.region_selection"))
        if is_single_region_only:
            print_box_line(f"[yellow]{t('flow.single_region_only')}[/yellow]")
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
                    console.print(f"[dim]{t('flow.number_range_hint', max=len(modes))}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('flow.enter_number')}[/dim]")

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
            elif mode == 2:  # 다른 리전 선택 (1개 이상)
                ctx.regions = self._select_regions()
            else:  # 모든 리전
                ctx.regions = ALL_REGIONS.copy()

        # 결과 출력
        self._print_summary(ctx.regions)

        return ctx

    def _select_single_region(self) -> str:
        """단일 리전 선택 UI (단일 리전만 지원하는 도구용)"""
        console.print()

        # 알파벳순 정렬 (같은 prefix끼리 자연 그룹핑)
        all_regions_for_selection = sorted(ALL_REGIONS)

        print_box_start(t("flow.region_count", count=len(all_regions_for_selection)))

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
                    console.print(f"[dim]{t('flow.number_range_hint', max=len(all_regions_for_selection))}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('flow.enter_number')}[/dim]")

    def _select_regions(self) -> list[str]:
        """리전 선택 UI (1개 이상 선택 가능)"""
        console.print()

        # 알파벳순 정렬 (같은 prefix끼리 자연 그룹핑)
        all_regions = sorted(ALL_REGIONS)

        print_box_start(t("flow.region_count", count=len(all_regions)))

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
                    mark = "*" if region == self.default_region else " "
                    line_parts.append(f"{num:>2}){mark}{region:<15}")
            print_box_line(" " + "".join(line_parts))

        print_box_line()
        print_box_line(f"[dim]{t('flow.number_comma_hint')}[/dim]")
        print_box_end()

        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            # 번호 파싱 (1,2,3 / 1-5 / 1-3,5,7-9 지원)
            try:
                indices: set[int] = set()
                parts = choice.replace(" ", ",").split(",")
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    if "-" in part and not part.startswith("-"):
                        range_parts = part.split("-", 1)
                        start, end = int(range_parts[0]), int(range_parts[1])
                        if start > end:
                            start, end = end, start
                        for i in range(start, end + 1):
                            if 1 <= i <= len(all_regions):
                                indices.add(i)
                    else:
                        num = int(part)
                        if 1 <= num <= len(all_regions):
                            indices.add(num)

                selected = [all_regions[i - 1] for i in sorted(indices)]

                if selected:
                    return selected

                console.print(f"[dim]{t('flow.number_range_hint', max=len(all_regions))}[/dim]")
            except ValueError:
                console.print(f"[dim]{t('flow.enter_number')}[/dim]")

    def _print_summary(self, regions: list[str]) -> None:
        """선택 결과 출력"""
        console.print()

        if len(regions) == 1:
            region = regions[0]
            name = REGION_NAMES.get(region, "")
            if name:
                console.print(f"[dim]{t('flow.region_label')}[/dim] {region} ({name})")
            else:
                console.print(f"[dim]{t('flow.region_label')}[/dim] {region}")
        elif len(regions) == len(ALL_REGIONS):
            console.print(f"[dim]{t('flow.region_label')}[/dim] {t('flow.all_regions_count', count=len(regions))}")
        else:
            console.print(f"[dim]{t('flow.region_label')}[/dim] {t('flow.regions_count', count=len(regions))}")
