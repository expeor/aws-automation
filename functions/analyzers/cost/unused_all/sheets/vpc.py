"""미사용 리소스 리포트 시트 생성 함수"""

from __future__ import annotations

from core.shared.io.excel import ColumnDef, Styles, Workbook


def _create_nat_sheet(wb: Workbook, findings) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="NAT ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Monthly Waste", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("NAT Gateway", columns=columns)

    for nat_result in findings:
        for f in nat_result.findings:
            if f.usage_status.value in ("unused", "low_usage"):
                sheet.add_row(
                    [
                        f.nat.account_name,
                        f.nat.region,
                        f.nat.nat_gateway_id,
                        f.nat.name,
                        f.usage_status.value,
                        f"${f.monthly_waste:,.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_eni_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="ENI ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Type", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ENI", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "pending"):
                sheet.add_row(
                    [
                        f.eni.account_name,
                        f.eni.region,
                        f.eni.id,
                        f.eni.name,
                        f.usage_status.value,
                        f.eni.interface_type,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_endpoint_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Endpoint ID", width=25, style="data"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Service", width=20, style="data"),
        ColumnDef(header="VPC", width=20, style="data"),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("VPC Endpoint", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                ep = f.endpoint
                sheet.add_row(
                    [
                        ep.account_name,
                        ep.region,
                        ep.endpoint_id,
                        ep.endpoint_type,
                        ep.service_name.split(".")[-1],
                        ep.vpc_id,
                        ep.state,
                        round(ep.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_security_group_sheet(wb: Workbook, results) -> None:
    """Security Group 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="SG ID", width=25, style="data"),
        ColumnDef(header="SG Name", width=30, style="data"),
        ColumnDef(header="VPC ID", width=25, style="data"),
        ColumnDef(header="ENI Count", width=10, style="number"),
        ColumnDef(header="Inbound Rules", width=12, style="number"),
        ColumnDef(header="Outbound Rules", width=12, style="number"),
        ColumnDef(header="상태", width=15, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Security Group", columns=columns)

    for sg_result in results:
        # SGAnalysisResult는 SGAnalyzer.analyze()에서 반환되는 개별 결과
        if sg_result.status.value == "Unused":
            sg = sg_result.sg
            sheet.add_row(
                [
                    sg.account_name,
                    sg.region,
                    sg.sg_id,
                    sg.sg_name,
                    sg.vpc_id,
                    sg.eni_count,
                    len(sg.inbound_rules),
                    len(sg.outbound_rules),
                    sg_result.status.value,
                    sg_result.action_recommendation,
                ],
                style=Styles.danger(),
            )
