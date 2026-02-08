"""
NAT Gateway Excel 보고서 생성기

시트 구성:
1. Summary - 전체 요약 (미사용, 저사용, 비용)
2. Findings - 상세 분석 결과
3. All NAT Gateways - 전체 NAT Gateway 목록

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    openpyxl 등 무거운 의존성을 실제 사용 시점에만 로드합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.shared.io.excel import ColumnDef, Styles, Workbook

from .analyzer import NATAnalysisResult, Severity, UsageStatus


class NATExcelReporter:
    """NAT Gateway 감사 결과를 Excel 보고서로 출력하는 생성기.

    Summary, Findings, All NAT Gateways 시트를 생성한다.

    Args:
        results: 계정/리전별 NATAnalysisResult 목록.
        stats_list: 계정/리전별 요약 통계 딕셔너리 목록.
    """

    def __init__(
        self,
        results: list[NATAnalysisResult],
        stats_list: list[dict[str, Any]],
    ):
        self.results = results
        self.stats_list = stats_list

    def build_workbook(self) -> Workbook:
        """Excel Workbook을 구성하여 반환한다 (파일 저장은 하지 않음).

        Returns:
            Summary, Findings, All NAT Gateways 시트가 포함된 Workbook.
        """
        wb = Workbook()

        # 시트 생성
        self._create_summary_sheet(wb)
        self._create_findings_sheet(wb)
        self._create_all_nat_sheet(wb)

        return wb

    def generate(self, output_dir: str) -> str:
        """Excel 보고서를 생성하고 파일로 저장한다 (후방 호환용).

        Args:
            output_dir: 보고서 저장 디렉토리 경로.

        Returns:
            저장된 Excel 파일의 절대 경로.
        """
        wb = self.build_workbook()
        return str(wb.save_as(output_dir, "NAT_Gateway_Audit"))

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """Summary 시트를 생성한다. 핵심 지표, 비용 분석, 계정/리전별 현황을 포함."""
        summary = wb.new_summary_sheet("Summary")

        # 제목
        summary.add_title("NAT Gateway 미사용 분석 보고서")
        summary.add_item("생성일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 전체 통계
        totals = {
            "total_nat_count": sum(s.get("total_nat_count", 0) for s in self.stats_list),
            "unused_count": sum(s.get("unused_count", 0) for s in self.stats_list),
            "low_usage_count": sum(s.get("low_usage_count", 0) for s in self.stats_list),
            "normal_count": sum(s.get("normal_count", 0) for s in self.stats_list),
            "pending_count": sum(s.get("pending_count", 0) for s in self.stats_list),
            "total_monthly_cost": sum(s.get("total_monthly_cost", 0) for s in self.stats_list),
            "total_monthly_waste": sum(s.get("total_monthly_waste", 0) for s in self.stats_list),
            "total_annual_savings": sum(s.get("total_annual_savings", 0) for s in self.stats_list),
        }

        # 핵심 지표
        summary.add_blank_row()
        summary.add_section("핵심 지표")
        summary.add_item("전체 NAT Gateway", totals["total_nat_count"])
        summary.add_item(
            "미사용 (삭제 권장)", totals["unused_count"], highlight="danger" if totals["unused_count"] > 0 else None
        )
        summary.add_item(
            "저사용 (검토 필요)",
            totals["low_usage_count"],
            highlight="warning" if totals["low_usage_count"] > 0 else None,
        )
        summary.add_item(
            "정상 사용", totals["normal_count"], highlight="success" if totals["normal_count"] > 0 else None
        )
        summary.add_item("대기 중", totals["pending_count"])

        summary.add_blank_row()
        summary.add_section("비용 분석")
        summary.add_item("월간 총 비용", f"${totals['total_monthly_cost']:,.2f}")
        summary.add_item(
            "월간 낭비 추정",
            f"${totals['total_monthly_waste']:,.2f}",
            highlight="danger" if totals["total_monthly_waste"] > 0 else None,
        )
        summary.add_item(
            "연간 절감 가능액",
            f"${totals['total_annual_savings']:,.2f}",
            highlight="info" if totals["total_annual_savings"] > 0 else None,
        )

        # 계정/리전별 현황 시트
        account_columns = [
            ColumnDef(header="Account", width=25, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="Total", width=10, style="number"),
            ColumnDef(header="Unused", width=10, style="number"),
            ColumnDef(header="Low Usage", width=12, style="number"),
            ColumnDef(header="Normal", width=10, style="number"),
            ColumnDef(header="Monthly Cost", width=15, style="data"),
            ColumnDef(header="Monthly Waste", width=15, style="data"),
        ]
        account_sheet = wb.new_sheet("By Account", columns=account_columns)

        for stats in self.stats_list:
            row_style = Styles.danger() if stats.get("unused_count", 0) > 0 else None
            account_sheet.add_row(
                [
                    stats.get("account_name", ""),
                    stats.get("region", ""),
                    stats.get("total_nat_count", 0),
                    stats.get("unused_count", 0),
                    stats.get("low_usage_count", 0),
                    stats.get("normal_count", 0),
                    f"${stats.get('total_monthly_cost', 0):,.2f}",
                    f"${stats.get('total_monthly_waste', 0):,.2f}",
                ],
                style=row_style,
            )

    def _create_findings_sheet(self, wb: Workbook) -> None:
        """Findings 시트를 생성한다. 정상 사용이 아닌 항목만 심각도 순으로 표시."""
        columns = [
            ColumnDef(header="Account", width=25, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="NAT Gateway ID", width=25, style="data"),
            ColumnDef(header="Name", width=25, style="data"),
            ColumnDef(header="Status", width=12, style="center"),
            ColumnDef(header="Severity", width=10, style="center"),
            ColumnDef(header="Confidence", width=12, style="center"),
            ColumnDef(header="Description", width=40, style="data"),
            ColumnDef(header="Monthly Waste", width=15, style="data"),
            ColumnDef(header="Annual Savings", width=15, style="data"),
            ColumnDef(header="Recommendation", width=40, style="data"),
            ColumnDef(header="VPC ID", width=22, style="data"),
        ]
        sheet = wb.new_sheet("Findings", columns=columns)

        # 심각도 순으로 정렬
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }

        all_findings = []
        for result in self.results:
            for finding in result.findings:
                # 정상 사용은 제외
                if finding.usage_status != UsageStatus.NORMAL:
                    all_findings.append(finding)

        sorted_findings = sorted(all_findings, key=lambda x: severity_order.get(x.severity, 5))

        for finding in sorted_findings:
            nat = finding.nat
            # 상태에 따른 스타일
            if finding.usage_status == UsageStatus.UNUSED:
                row_style = Styles.danger()
            elif finding.usage_status == UsageStatus.LOW_USAGE:
                row_style = Styles.warning()
            else:
                row_style = None

            sheet.add_row(
                [
                    nat.account_name,
                    nat.region,
                    nat.nat_gateway_id,
                    nat.name,
                    finding.usage_status.value,
                    finding.severity.value.upper(),
                    finding.confidence.value,
                    finding.description,
                    f"${finding.monthly_waste:,.2f}",
                    f"${finding.annual_savings:,.2f}",
                    finding.recommendation,
                    nat.vpc_id,
                ],
                style=row_style,
            )

    def _create_all_nat_sheet(self, wb: Workbook) -> None:
        """All NAT Gateways 시트를 생성한다. 전체 NAT Gateway 목록과 상세 정보 표시."""
        columns = [
            ColumnDef(header="Account", width=25, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="NAT Gateway ID", width=25, style="data"),
            ColumnDef(header="Name", width=25, style="data"),
            ColumnDef(header="VPC ID", width=22, style="data"),
            ColumnDef(header="Subnet ID", width=25, style="data"),
            ColumnDef(header="State", width=12, style="center"),
            ColumnDef(header="Public IP", width=18, style="data"),
            ColumnDef(header="Type", width=10, style="center"),
            ColumnDef(header="Age (Days)", width=12, style="number"),
            ColumnDef(header="Bytes Out (14d)", width=15, style="data"),
            ColumnDef(header="Days with Traffic", width=15, style="number"),
            ColumnDef(header="Monthly Cost", width=15, style="data"),
            ColumnDef(header="Usage Status", width=12, style="center"),
            ColumnDef(header="Tags", width=40, style="data"),
        ]
        sheet = wb.new_sheet("All NAT Gateways", columns=columns)

        for result in self.results:
            for finding in result.findings:
                nat = finding.nat

                # 바이트를 읽기 쉽게 변환
                bytes_out = nat.bytes_out_total
                if bytes_out >= 1024**3:
                    bytes_str = f"{bytes_out / (1024**3):.2f} GB"
                elif bytes_out >= 1024**2:
                    bytes_str = f"{bytes_out / (1024**2):.2f} MB"
                elif bytes_out >= 1024:
                    bytes_str = f"{bytes_out / 1024:.2f} KB"
                else:
                    bytes_str = f"{bytes_out:.0f} B"

                # 태그 문자열
                tags_str = ", ".join(f"{k}={v}" for k, v in nat.tags.items() if k != "Name")

                # 상태에 따른 스타일
                if finding.usage_status == UsageStatus.UNUSED:
                    row_style = Styles.danger()
                elif finding.usage_status == UsageStatus.LOW_USAGE:
                    row_style = Styles.warning()
                elif finding.usage_status == UsageStatus.NORMAL:
                    row_style = Styles.success()
                else:
                    row_style = None

                sheet.add_row(
                    [
                        nat.account_name,
                        nat.region,
                        nat.nat_gateway_id,
                        nat.name,
                        nat.vpc_id,
                        nat.subnet_id,
                        nat.state,
                        nat.public_ip,
                        nat.connectivity_type,
                        nat.age_days,
                        bytes_str,
                        nat.days_with_traffic,
                        f"${nat.total_monthly_cost:,.2f}",
                        finding.usage_status.value,
                        tags_str[:100],  # 최대 100자
                    ],
                    style=row_style,
                )
