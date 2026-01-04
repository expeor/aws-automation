"""
Security Group Audit Excel 보고서 생성기

시트 구성:
1. Summary - 계정/리전별 SG 현황
2. HIGH Risk Rules - 위험 포트 노출 규칙 (최우선 검토)
3. Security Warnings - Egress ALL, Self ALL, Cross-account 등 추가 경고
4. Action Required - SG - 미사용 SG
5. Action Required - Rules - 확인 필요 규칙
6. Security Groups - SG 목록 + 미사용 판단 근거
7. Rules - 전체 SGR + Stale 판단 근거
"""

import os
from datetime import datetime

from core.tools.io.excel import ColumnDef, Workbook

from .analyzer import RuleAnalysisResult, RuleStatus, SGAnalysisResult, SGStatus


def _format_port_range(port_range: str) -> int | str:
    """Port Range를 적절한 타입으로 변환

    - 단일 포트 (예: "22", "443"): 정수로 변환 → Excel에서 숫자로 정렬
    - 범위/특수값 (예: "80-443", "ALL", "N/A"): 문자열 유지
    """
    if port_range.isdigit():
        return int(port_range)
    return port_range


class SGExcelReporter:
    """Security Group Audit Excel 보고서 생성기"""

    def __init__(
        self,
        sg_results: list[SGAnalysisResult],
        rule_results: list[RuleAnalysisResult],
        summary: dict[str, dict[str, int]],
    ):
        self.sg_results = sg_results
        self.rule_results = rule_results
        self.summary = summary

    def generate(self, output_dir: str) -> str:
        """Excel 보고서 생성"""
        os.makedirs(output_dir, exist_ok=True)

        wb = Workbook()

        # 1. Summary 시트
        self._add_summary_sheet(wb)

        # 2. HIGH Risk Rules (최우선 검토)
        self._add_high_risk_rules_sheet(wb)

        # 3. Security Warnings (추가 경고)
        self._add_security_warnings_sheet(wb)

        # 4. Action Required - SG (확인 필요 SG)
        self._add_action_sg_sheet(wb)

        # 5. Action Required - Rules (확인 필요 규칙)
        self._add_action_rules_sheet(wb)

        # 6. Security Groups 시트 (전체)
        self._add_sg_sheet(wb)

        # 7. Rules 시트 (전체)
        self._add_rules_sheet(wb)

        # 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SG_Audit_Report_{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)
        wb.save(filepath)

        return filepath

    def _add_summary_sheet(self, wb: Workbook) -> None:
        """Summary 시트 추가"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            # 통계
            ColumnDef(header="Total SGs", width=10, style="number"),
            ColumnDef(header="Active", width=10, style="number"),
            ColumnDef(header="Unused", width=10, style="number"),
            ColumnDef(header="Default SG", width=10, style="number"),
            ColumnDef(header="Default VPC", width=10, style="number"),
        ]

        ws = wb.new_sheet("Summary", columns=columns)

        for _key, stats in sorted(self.summary.items()):
            ws.add_row(
                [
                    str(stats["account_id"]),  # 텍스트 강제
                    stats["account_name"],
                    stats["region"],
                    int(stats["total"]),
                    int(stats["active"]),
                    int(stats["unused"]),
                    int(stats["default_sg"]),
                    int(stats["in_default_vpc"]),
                ]
            )

        # 합계
        if self.summary:
            totals = {
                "total": sum(s["total"] for s in self.summary.values()),
                "active": sum(s["active"] for s in self.summary.values()),
                "unused": sum(s["unused"] for s in self.summary.values()),
                "default_sg": sum(s["default_sg"] for s in self.summary.values()),
                "in_default_vpc": sum(
                    s["in_default_vpc"] for s in self.summary.values()
                ),
            }
            ws.add_row(
                [
                    "TOTAL",
                    "",
                    "",
                    int(totals["total"]),
                    int(totals["active"]),
                    int(totals["unused"]),
                    int(totals["default_sg"]),
                    int(totals["in_default_vpc"]),
                ]
            )

    def _add_high_risk_rules_sheet(self, wb: Workbook) -> None:
        """HIGH Risk Rules 시트 (최우선 검토 대상 - 위험 포트 노출)"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=25, style="data"),
            # 규칙 정보
            ColumnDef(header="Direction", width=10, style="center"),
            ColumnDef(header="Protocol", width=10, style="center"),
            ColumnDef(header="Port Range", width=12, style="center"),
            ColumnDef(header="Source/Dest", width=20, style="data"),
            # 위험 분석
            ColumnDef(header="Exposed Ports", width=50, style="data"),
            ColumnDef(header="Reason", width=50, style="data"),
        ]

        ws = wb.new_sheet("HIGH Risk Rules", columns=columns)

        for result in self.rule_results:
            # HIGH 위험 규칙만 표시
            if result.risk_level != "HIGH":
                continue

            rule = result.rule

            # Exposed ports (전체)
            exposed_ports_str = ", ".join(
                [f"{p.port}/{p.name}" for p in result.exposed_critical_ports]
            )

            # Reason
            port_info = ""
            if rule.port_range == "ALL" or result.is_all_protocols:
                port_info = "모든 포트가 "
            elif rule.port_range == "0-65535":
                port_info = "전체 포트(0-65535)가 "
            else:
                port_info = f"위험 포트({rule.port_range})가 "

            if result.is_open_to_world:
                reason = port_info + "0.0.0.0/0 (전체)에 노출"
            elif result.is_wide_cidr:
                reason = port_info + f"/{result.cidr_prefix} 범위에 노출"
            else:
                reason = port_info + "넓은 범위에 노출"

            ws.add_row(
                [
                    str(result.account_id),  # 텍스트 강제
                    result.account_name,
                    result.region,
                    result.sg_id,
                    result.sg_name,
                    rule.direction.upper(),
                    rule.protocol.upper(),
                    _format_port_range(rule.port_range),
                    rule.source_dest,
                    exposed_ports_str,
                    reason,
                ]
            )

    def _add_security_warnings_sheet(self, wb: Workbook) -> None:
        """Security Warnings 시트 (Egress ALL, Self ALL, Cross-account 등)"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=25, style="data"),
            # 규칙 정보
            ColumnDef(header="Direction", width=10, style="center"),
            ColumnDef(header="Protocol", width=10, style="center"),
            ColumnDef(header="Port Range", width=12, style="center"),
            ColumnDef(header="Source/Dest", width=20, style="data"),
            # 경고 정보
            ColumnDef(header="Warning Type", width=18, style="center"),
            ColumnDef(header="Warning", width=60, style="data"),
        ]

        ws = wb.new_sheet("Security Warnings", columns=columns)

        for result in self.rule_results:
            # 경고가 있는 규칙만 표시
            if not result.warnings:
                continue

            rule = result.rule

            # 경고 유형 결정
            warning_types = []
            if result.is_egress_all_open:
                warning_types.append("Egress ALL")
            if result.is_self_all_ports:
                warning_types.append("Self ALL")
            if result.is_cross_account:
                warning_types.append("Cross-Account")
            if result.hidden_risky_ports:
                warning_types.append("Hidden Ports")

            warning_type = ", ".join(warning_types) if warning_types else "Warning"

            ws.add_row(
                [
                    str(result.account_id),  # 텍스트 강제
                    result.account_name,
                    result.region,
                    result.sg_id,
                    result.sg_name,
                    rule.direction.upper(),
                    rule.protocol.upper(),
                    _format_port_range(rule.port_range),
                    rule.source_dest,
                    warning_type,
                    "; ".join(result.warnings),
                ]
            )

    def _add_action_sg_sheet(self, wb: Workbook) -> None:
        """Action Required - SG 시트 (미사용 SG만)"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            # VPC 정보
            ColumnDef(header="VPC ID", width=25, style="data"),
            ColumnDef(header="Default VPC", width=10, style="center"),
            # SG 정보
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=30, style="data"),
            ColumnDef(header="Default SG", width=10, style="center"),
            # 사용 현황
            ColumnDef(header="ENI Count", width=10, style="number"),
            ColumnDef(header="Referenced By", width=30, style="data"),
            # 분석 결과
            ColumnDef(header="Status", width=12, style="center"),
            ColumnDef(header="Reason", width=50, style="data"),
            ColumnDef(header="Recommendation", width=50, style="data"),
        ]

        ws = wb.new_sheet("Action Required - SG", columns=columns)

        # 미사용 SG만 필터링
        for result in self.sg_results:
            if result.status != SGStatus.UNUSED:
                continue

            sg = result.sg
            refs_str = ", ".join(sg.referenced_by_sgs)

            ws.add_row(
                [
                    str(sg.account_id),  # 텍스트 강제
                    sg.account_name,
                    sg.region,
                    sg.vpc_id,
                    "Y" if sg.is_default_vpc else "N",
                    sg.sg_id,
                    sg.sg_name,
                    "Y" if sg.is_default_sg else "N",
                    int(sg.eni_count),
                    refs_str,
                    result.status.value,
                    "; ".join(result.unused_reasons),
                    result.action_recommendation,
                ]
            )

    def _add_action_rules_sheet(self, wb: Workbook) -> None:
        """Action Required - Rules 시트 (확인 필요 규칙만)"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=25, style="data"),
            # 규칙 정보
            ColumnDef(header="Direction", width=10, style="center"),
            ColumnDef(header="Protocol", width=10, style="center"),
            ColumnDef(header="Port Range", width=12, style="center"),
            ColumnDef(header="Source/Dest", width=20, style="data"),
            # 분석 결과 (Action Required이므로 Issue 먼저)
            ColumnDef(header="Issue", width=18, style="center"),
            ColumnDef(header="Exposed Ports", width=40, style="data"),
            ColumnDef(header="Warnings", width=60, style="data"),
        ]

        ws = wb.new_sheet("Action Required - Rules", columns=columns)

        for result in self.rule_results:
            # 확인 필요 조건: Stale, HIGH/MEDIUM 위험, 또는 경고가 있는 규칙
            is_stale = result.status != RuleStatus.ACTIVE
            is_risky = result.risk_level in ("HIGH", "MEDIUM")
            has_warnings = bool(result.warnings)

            if not (is_stale or is_risky or has_warnings):
                continue

            rule = result.rule

            # Issue 통합 (Stale + Risk Level + 추가 경고)
            issues = []
            if is_stale:
                issues.append("Stale")
            if result.risk_level:
                issues.append(result.risk_level)
            if result.is_egress_all_open:
                issues.append("Egress ALL")
            if result.is_self_all_ports:
                issues.append("Self ALL")
            if result.is_cross_account:
                issues.append("Cross-Acct")

            issue = " / ".join(issues)

            # Exposed ports (전체)
            exposed_ports_str = ""
            if result.exposed_critical_ports:
                port_names = [
                    f"{p.port}/{p.name}" for p in result.exposed_critical_ports
                ]
                exposed_ports_str = ", ".join(port_names)

            # Warnings 통합 (stale_reason + warnings)
            all_warnings = []
            if result.stale_reason:
                all_warnings.append(result.stale_reason)
            all_warnings.extend(result.warnings)

            ws.add_row(
                [
                    str(result.account_id),  # 텍스트 강제
                    result.account_name,
                    result.region,
                    result.sg_id,
                    result.sg_name,
                    rule.direction.upper(),
                    rule.protocol.upper(),
                    _format_port_range(rule.port_range),
                    rule.source_dest,
                    issue,
                    exposed_ports_str,
                    "; ".join(all_warnings),
                ]
            )

    def _add_sg_sheet(self, wb: Workbook) -> None:
        """Security Groups 시트 추가"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            # VPC 정보
            ColumnDef(header="VPC ID", width=25, style="data"),
            ColumnDef(header="Default VPC", width=10, style="center"),
            # SG 정보
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=30, style="data"),
            ColumnDef(header="Default SG", width=10, style="center"),
            ColumnDef(header="Description", width=40, style="data"),
            # 사용 현황
            ColumnDef(header="ENI Count", width=10, style="number"),
            ColumnDef(header="ENI Resources", width=50, style="data"),
            ColumnDef(header="Referenced By", width=30, style="data"),
            ColumnDef(header="Inbound", width=10, style="number"),
            ColumnDef(header="Outbound", width=10, style="number"),
            # 분석 결과
            ColumnDef(header="Status", width=12, style="center"),
            ColumnDef(header="Reason", width=50, style="data"),
            ColumnDef(header="Recommendation", width=50, style="data"),
        ]

        ws = wb.new_sheet("Security Groups", columns=columns)

        for result in self.sg_results:
            sg = result.sg

            # ENI 리소스 (전체)
            eni_resources = "; ".join(sg.eni_descriptions)

            # 참조하는 SG 목록 (전체)
            refs_str = ", ".join(sg.referenced_by_sgs)

            ws.add_row(
                [
                    str(sg.account_id),  # 텍스트 강제
                    sg.account_name,
                    sg.region,
                    sg.vpc_id,
                    "Y" if sg.is_default_vpc else "N",
                    sg.sg_id,
                    sg.sg_name,
                    "Y" if sg.is_default_sg else "N",
                    sg.description,
                    int(sg.eni_count),
                    eni_resources,
                    refs_str,
                    int(len(sg.inbound_rules)),
                    int(len(sg.outbound_rules)),
                    result.status.value,
                    "; ".join(result.unused_reasons),
                    result.action_recommendation,
                ]
            )

    def _add_rules_sheet(self, wb: Workbook) -> None:
        """Rules 시트 추가"""
        columns = [
            # 식별 정보
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="SG ID", width=25, style="data"),
            ColumnDef(header="SG Name", width=25, style="data"),
            # 규칙 정보
            ColumnDef(header="Direction", width=10, style="center"),
            ColumnDef(header="Protocol", width=10, style="center"),
            ColumnDef(header="Port Range", width=12, style="center"),
            ColumnDef(header="Source/Dest", width=20, style="data"),
            ColumnDef(header="Type", width=8, style="center"),
            # 분석 플래그
            ColumnDef(header="Issue", width=15, style="center"),
            ColumnDef(header="ALL Ports", width=8, style="center"),
            ColumnDef(header="No Desc", width=8, style="center"),
            # 상세 정보
            ColumnDef(header="Exposed Ports", width=40, style="data"),
            ColumnDef(header="Warnings", width=50, style="data"),
        ]

        ws = wb.new_sheet("Rules", columns=columns)

        for result in self.rule_results:
            rule = result.rule

            # 포트 정보 (전체)
            exposed_ports_str = ""
            if result.exposed_critical_ports:
                port_names = [
                    f"{p.port}/{p.name}" for p in result.exposed_critical_ports
                ]
                exposed_ports_str = ", ".join(port_names)

            # Issue 통합 (Stale + Risk Level + 추가 경고)
            issues = []
            if result.stale_reason:
                issues.append("Stale")
            if result.risk_level:
                issues.append(result.risk_level)
            if result.is_egress_all_open:
                issues.append("Egress")
            if result.is_self_all_ports:
                issues.append("Self")
            if result.is_cross_account:
                issues.append("X-Acct")
            issue = " / ".join(issues) if issues else ""

            # Warnings 통합
            warnings_str = "; ".join(result.warnings) if result.warnings else ""

            # ALL Ports 표시 (ALL 또는 0-65535)
            all_ports = "Y" if (result.is_all_ports or result.is_all_protocols) else ""

            # No Description
            no_desc = "Y" if result.has_no_description else ""

            ws.add_row(
                [
                    str(result.account_id),  # 텍스트 강제
                    result.account_name,
                    result.region,
                    result.sg_id,
                    result.sg_name,
                    rule.direction.upper(),
                    rule.protocol.upper(),
                    _format_port_range(rule.port_range),
                    rule.source_dest,
                    rule.source_dest_type.upper(),
                    issue,
                    all_ports,
                    no_desc,
                    exposed_ports_str,
                    warnings_str,
                ]
            )
