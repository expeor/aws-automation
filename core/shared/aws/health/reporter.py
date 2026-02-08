"""
core/shared/aws/health/reporter.py - AWS Health 패치 보고서 생성기

수집된 패치/유지보수 이벤트를 Excel 형식으로 출력합니다.
- 요약 시트: 긴급도별, 서비스별 현황
- 패치 목록: 전체 패치 상세 정보
- 월별 일정표: 월별 예정 패치 캘린더

사용법:
    from functions.analyzers.health.phd.reporter import PatchReporter

    reporter = PatchReporter(collection_result)
    reporter.generate_report(output_dir, "patch_analysis")
"""

from __future__ import annotations

import logging
from calendar import monthcalendar
from datetime import datetime
from pathlib import Path
from typing import Any

from core.shared.io.excel import ColumnDef, Styles, Workbook

from .collector import CollectionResult, PatchItem

logger = logging.getLogger(__name__)


# 리포트 컬럼 정의
COLUMNS_PATCHES = [
    ColumnDef(header="긴급도", width=10, style="center"),
    ColumnDef(header="서비스", width=12, style="center"),
    ColumnDef(header="이벤트 유형", width=30, style="data"),
    ColumnDef(header="예정일", width=12, style="date"),
    ColumnDef(header="마감일", width=12, style="date"),
    ColumnDef(header="D-Day", width=8, style="center"),
    ColumnDef(header="상태", width=10, style="center"),
    ColumnDef(header="필요 조치", width=18, style="data"),
    ColumnDef(header="영향 리소스", width=10, style="center"),
    ColumnDef(header="리전", width=15, style="center"),
    ColumnDef(header="설명", width=50, style="data"),
]

COLUMNS_RESOURCES = [
    ColumnDef(header="서비스", width=12, style="center"),
    ColumnDef(header="리소스 ID", width=30, style="data"),
    ColumnDef(header="이벤트 유형", width=30, style="data"),
    ColumnDef(header="긴급도", width=10, style="center"),
    ColumnDef(header="예정일", width=12, style="date"),
    ColumnDef(header="필요 조치", width=18, style="data"),
    ColumnDef(header="상태", width=10, style="center"),
]


class PatchReporter:
    """AWS Health 패치 보고서 생성기

    수집된 패치/유지보수 이벤트를 Excel 형식으로 출력합니다.
    """

    def __init__(self, result: CollectionResult):
        """초기화

        Args:
            result: CollectionResult 객체
        """
        self.result = result

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "patch_analysis",
        include_calendar: bool = True,
    ) -> Path:
        """Excel 리포트 생성

        Args:
            output_dir: 출력 디렉토리
            file_prefix: 파일명 접두사
            include_calendar: 월별 일정표 포함 여부

        Returns:
            생성된 파일 경로
        """
        wb = Workbook()

        # 요약 시트
        self._create_summary_sheet(wb)

        # 긴급 패치 시트 (critical + high)
        self._create_urgent_patches_sheet(wb)

        # 전체 패치 목록
        self._create_all_patches_sheet(wb)

        # 영향받는 리소스 목록
        self._create_affected_resources_sheet(wb)

        # 월별 일정표
        if include_calendar:
            self._create_calendar_sheets(wb)

        # 파일 저장
        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"패치 보고서 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """요약 시트 생성

        전체 현황, 긴급도별, 서비스별, 월별 통계를 포함하는 요약 시트를 생성합니다.

        Args:
            wb: Workbook 인스턴스
        """
        summary = wb.new_summary_sheet("분석 요약")

        summary.add_title("AWS 필수 패치 분석 보고서")

        # ===== 전체 현황 =====
        summary.add_section("전체 현황")

        summary.add_item(
            "긴급 패치 (3일 이내)",
            f"{self.result.critical_count}건",
            highlight="danger" if self.result.critical_count > 0 else None,
        )
        summary.add_item(
            "높은 우선순위 (7일 이내)",
            f"{self.result.high_count}건",
            highlight="warning" if self.result.high_count > 0 else None,
        )
        summary.add_item("전체 패치", f"{self.result.patch_count}건")
        summary.add_item("영향받는 리소스", f"{self.result.affected_resource_count}개")

        summary.add_blank_row()

        # ===== 긴급도별 현황 =====
        summary.add_section("긴급도별 현황")

        urgency_order = ["critical", "high", "medium", "low"]
        urgency_display = {
            "critical": "긴급 (3일 이내)",
            "high": "높음 (7일 이내)",
            "medium": "중간 (14일 이내)",
            "low": "낮음 (14일 이후)",
        }
        urgency_highlight = {
            "critical": "danger",
            "high": "warning",
            "medium": None,
            "low": None,
        }

        for urgency in urgency_order:
            data = self.result.summary_by_urgency.get(urgency, {})
            count = data.get("count", 0)
            if count > 0:
                services = data.get("services", [])
                service_str = ", ".join(services[:3])
                if len(services) > 3:
                    service_str += f" 외 {len(services) - 3}개"

                summary.add_item(
                    urgency_display[urgency],
                    f"{count}건 ({service_str})",
                    highlight=urgency_highlight[urgency],
                )

        summary.add_blank_row()

        # ===== 서비스별 현황 =====
        summary.add_section("서비스별 현황")

        sorted_services = sorted(
            self.result.summary_by_service.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:10]

        for service, data in sorted_services:
            critical = data.get("critical", 0)
            high = data.get("high", 0)

            status = ""
            highlight = None
            if critical > 0:
                status = f"(긴급 {critical}건)"
                highlight = "danger"
            elif high > 0:
                status = f"(높음 {high}건)"
                highlight = "warning"

            summary.add_item(
                service,
                f"{data['count']}건, 리소스 {data['affected_resources']}개 {status}",
                highlight=highlight,
            )

        summary.add_blank_row()

        # ===== 월별 현황 =====
        summary.add_section("월별 예정 현황")

        for month_key in sorted(self.result.summary_by_month.keys()):
            patches = self.result.summary_by_month[month_key]
            critical_in_month = sum(1 for p in patches if p.urgency == "critical")
            high_in_month = sum(1 for p in patches if p.urgency == "high")

            status = ""
            highlight = None
            if critical_in_month > 0:
                status = f"(긴급 {critical_in_month}건)"
                highlight = "danger"
            elif high_in_month > 0:
                status = f"(높음 {high_in_month}건)"
                highlight = "warning"

            summary.add_item(
                month_key,
                f"{len(patches)}건 {status}",
                highlight=highlight,
            )

        summary.add_blank_row()

        # ===== 리포트 정보 =====
        summary.add_section("리포트 정보")
        summary.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        summary.add_item("조회 기간", "향후 90일")
        summary.add_item("데이터 소스", "AWS Personal Health Dashboard")

    def _create_urgent_patches_sheet(self, wb: Workbook) -> None:
        """긴급 패치 시트 생성

        critical 또는 high 긴급도의 패치만 별도 시트로 생성합니다.

        Args:
            wb: Workbook 인스턴스
        """
        urgent_patches = [p for p in self.result.patches if p.urgency in ["critical", "high"]]

        if not urgent_patches:
            return

        sheet = wb.new_sheet(name="긴급 패치", columns=COLUMNS_PATCHES)

        for patch in urgent_patches:
            row = self._patch_to_row(patch)
            style = self._get_row_style(patch)
            sheet.add_row(row, style=style)

        sheet.add_summary_row(
            [
                "합계",
                "",
                f"{len(urgent_patches)}건",
                "",
                "",
                "",
                "",
                "",
                sum(len(p.affected_resources) for p in urgent_patches),
                "",
                "",
            ]
        )

    def _create_all_patches_sheet(self, wb: Workbook) -> None:
        """전체 패치 목록 시트

        Args:
            wb: Workbook 인스턴스
        """
        sheet = wb.new_sheet(name="전체 패치", columns=COLUMNS_PATCHES)

        for patch in self.result.patches:
            row = self._patch_to_row(patch)
            style = self._get_row_style(patch)
            sheet.add_row(row, style=style)

        sheet.add_summary_row(
            [
                "합계",
                "",
                f"{len(self.result.patches)}건",
                "",
                "",
                "",
                "",
                "",
                self.result.affected_resource_count,
                "",
                "",
            ]
        )

    def _create_affected_resources_sheet(self, wb: Workbook) -> None:
        """영향받는 리소스 시트

        각 패치의 영향받는 리소스를 개별 행으로 나열하는 시트를 생성합니다.

        Args:
            wb: Workbook 인스턴스
        """
        # 영향받는 리소스가 있는 패치만
        patches_with_resources = [p for p in self.result.patches if p.affected_resources]

        if not patches_with_resources:
            return

        sheet = wb.new_sheet(name="영향 리소스", columns=COLUMNS_RESOURCES)

        for patch in patches_with_resources:
            for resource_id in patch.affected_resources:
                row = [
                    patch.service,
                    resource_id,
                    patch.event_type,
                    self._urgency_display(patch.urgency),
                    patch.scheduled_date,
                    patch.action_required,
                    patch.event.status_code,
                ]
                style = self._get_row_style(patch)
                sheet.add_row(row, style=style)

    def _create_calendar_sheets(self, wb: Workbook) -> None:
        """월별 일정표 시트 생성

        최대 3개월까지 달력 형태의 시트를 생성합니다.

        Args:
            wb: Workbook 인스턴스
        """
        if not self.result.summary_by_month:
            return

        # 각 월별로 시트 생성 (최대 3개월)
        months = sorted([k for k in self.result.summary_by_month if k != "미정"])[:3]

        for month_key in months:
            patches = self.result.summary_by_month[month_key]
            self._create_month_calendar_sheet(wb, month_key, patches)

    def _create_month_calendar_sheet(
        self,
        wb: Workbook,
        month_key: str,
        patches: list[PatchItem],
    ) -> None:
        """개별 월 캘린더 시트 생성"""
        # 월 파싱
        try:
            year, month = map(int, month_key.split("-"))
        except ValueError:
            return

        sheet_name = f"일정_{month_key}"

        # 캘린더 컬럼 정의
        calendar_columns = [
            ColumnDef(header="일", width=20, style="data"),
            ColumnDef(header="월", width=20, style="data"),
            ColumnDef(header="화", width=20, style="data"),
            ColumnDef(header="수", width=20, style="data"),
            ColumnDef(header="목", width=20, style="data"),
            ColumnDef(header="금", width=20, style="data"),
            ColumnDef(header="토", width=20, style="data"),
        ]

        sheet = wb.new_sheet(name=sheet_name, columns=calendar_columns)

        # 일자별 패치 매핑
        patches_by_day: dict[int, list[PatchItem]] = {}
        for patch in patches:
            if patch.scheduled_date:
                day = patch.scheduled_date.day
                if day not in patches_by_day:
                    patches_by_day[day] = []
                patches_by_day[day].append(patch)

        # 캘린더 생성
        cal = monthcalendar(year, month)

        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append("")
                else:
                    day_patches = patches_by_day.get(day, [])
                    if day_patches:
                        # 패치 있는 날
                        patch_info = []
                        for p in day_patches[:2]:  # 최대 2개만 표시
                            urgency_mark = {
                                "critical": "[!!!]",
                                "high": "[!!]",
                                "medium": "[!]",
                                "low": "",
                            }.get(p.urgency, "")
                            patch_info.append(f"{urgency_mark}{p.service}")

                        if len(day_patches) > 2:
                            patch_info.append(f"+{len(day_patches) - 2}")

                        row.append(f"{day}일\n" + "\n".join(patch_info))
                    else:
                        row.append(f"{day}일")

            sheet.add_row(row)

    def _patch_to_row(self, patch: PatchItem) -> list[Any]:
        """PatchItem을 행 데이터로 변환

        Args:
            patch: PatchItem 객체

        Returns:
            COLUMNS_PATCHES 순서에 맞는 셀 값 리스트
        """
        days_until = patch.event.days_until_start
        d_day = f"D-{days_until}" if days_until is not None else "-"

        return [
            self._urgency_display(patch.urgency),
            patch.service,
            patch.event_type,
            patch.scheduled_date,
            patch.deadline,
            d_day,
            patch.event.status_code,
            patch.action_required,
            len(patch.affected_resources),
            patch.event.region,
            patch.description_summary,
        ]

    def _urgency_display(self, urgency: str) -> str:
        """긴급도 영문 코드를 한글 표시명으로 변환

        Args:
            urgency: 긴급도 코드 ("critical", "high", "medium", "low")

        Returns:
            한글 긴급도 문자열 ("긴급", "높음", "중간", "낮음")
        """
        return {
            "critical": "긴급",
            "high": "높음",
            "medium": "중간",
            "low": "낮음",
        }.get(urgency, urgency)

    def _get_row_style(self, patch: PatchItem) -> dict | None:
        """패치에 따른 행 스타일 결정

        Args:
            patch: PatchItem 객체

        Returns:
            critical이면 danger 스타일, high이면 warning 스타일, 그 외 None
        """
        if patch.urgency == "critical":
            return Styles.danger()
        if patch.urgency == "high":
            return Styles.warning()
        return None

    def print_summary(self) -> None:
        """콘솔에 요약 정보 출력"""
        try:
            from rich.console import Console

            console = Console()
            self._print_rich_summary(console)
        except ImportError:
            self._print_plain_summary()

    def _print_rich_summary(self, console) -> None:
        """Rich 라이브러리를 사용한 요약 출력"""
        from rich.table import Table

        console.print("\n[bold cyan]AWS 필수 패치 분석 요약[/bold cyan]")
        console.print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print()

        # 긴급도별 요약
        table = Table(title="긴급도별 현황")
        table.add_column("긴급도", style="cyan")
        table.add_column("건수", justify="right")
        table.add_column("서비스")
        table.add_column("영향 리소스", justify="right")

        urgency_order = ["critical", "high", "medium", "low"]
        urgency_style = {
            "critical": "bold red",
            "high": "yellow",
            "medium": "",
            "low": "dim",
        }

        for urgency in urgency_order:
            data = self.result.summary_by_urgency.get(urgency, {})
            if data.get("count", 0) > 0:
                services = ", ".join(data.get("services", [])[:3])
                style = urgency_style[urgency]
                table.add_row(
                    f"[{style}]{self._urgency_display(urgency)}[/{style}]",
                    f"{data['count']}",
                    services,
                    f"{data.get('affected_resources', 0)}",
                )

        console.print(table)

        # 긴급 패치 상세
        urgent = [p for p in self.result.patches if p.urgency in ["critical", "high"]]
        if urgent:
            console.print()
            console.print("[bold red]긴급 조치 필요 항목:[/bold red]")
            for p in urgent[:5]:
                d_day = f"D-{p.event.days_until_start}" if p.event.days_until_start else ""
                style = "red" if p.urgency == "critical" else "yellow"
                console.print(f"  [{style}]{p.service}[/{style}] - {p.event_type} ({p.action_required}) [{d_day}]")

            if len(urgent) > 5:
                console.print(f"  ... 외 {len(urgent) - 5}건")

    def _print_plain_summary(self) -> None:
        """일반 텍스트 요약 출력"""
        print("\n=== AWS 필수 패치 분석 요약 ===")
        print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        print("긴급도별 현황:")
        print("-" * 60)

        urgency_order = ["critical", "high", "medium", "low"]
        for urgency in urgency_order:
            data = self.result.summary_by_urgency.get(urgency, {})
            if data.get("count", 0) > 0:
                print(
                    f"  {self._urgency_display(urgency)}: "
                    f"{data['count']}건, 리소스 {data.get('affected_resources', 0)}개"
                )

        print("-" * 60)
        print(f"  합계: {self.result.patch_count}건")


def generate_report(
    result: CollectionResult,
    output_dir: str,
    file_prefix: str = "patch_analysis",
) -> Path:
    """리포트 파일 생성 (편의 함수)

    Args:
        result: CollectionResult 객체
        output_dir: 출력 디렉토리
        file_prefix: 파일명 접두사

    Returns:
        생성된 파일 경로
    """
    reporter = PatchReporter(result)
    return reporter.generate_report(output_dir, file_prefix)
