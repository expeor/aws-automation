"""
functions/analyzers/vpc/sg_inventory.py - Security Group 정책 내역 추출

모든 Security Group의 인바운드/아웃바운드 규칙을 멀티 계정/리전에서 수집하여 Excel로 출력.

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.shared.io.excel import ColumnDef, Workbook
from core.shared.io.output import OutputPath, open_in_explorer, print_report_complete

from .sg_audit_analysis import SGCollector

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

    from .sg_audit_analysis.collector import SecurityGroup

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeVpcs",
    ],
}


def _collect_sgs(session, account_id: str, account_name: str, region: str) -> list | None:
    """단일 계정/리전의 Security Group 수집 (parallel_collect 콜백)

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전

    Returns:
        Security Group 리스트. 없으면 None.
    """
    collector = SGCollector()
    sgs = collector.collect(session, account_id, account_name, region)
    return sgs if sgs else None


def _flatten_rules(sgs: list[SecurityGroup]) -> list[dict]:
    """SG 규칙을 평탄화하여 행 데이터로 변환

    각 SG의 인바운드/아웃바운드 규칙을 개별 행으로 변환합니다.
    규칙이 없는 SG도 빈 규칙 행으로 포함됩니다.

    Args:
        sgs: Security Group 리스트

    Returns:
        규칙별 평탄화된 행 데이터 딕셔너리 리스트
    """
    rows = []

    for sg in sgs:
        base_info = {
            "account_id": sg.account_id,
            "account_name": sg.account_name,
            "region": sg.region,
            "vpc_id": sg.vpc_id,
            "sg_id": sg.sg_id,
            "sg_name": sg.sg_name,
            "sg_description": sg.description,
            "is_default_sg": "Yes" if sg.is_default_sg else "No",
            "is_default_vpc": "Yes" if sg.is_default_vpc else "No",
            "eni_count": sg.eni_count,
        }

        # 인바운드 규칙
        for rule in sg.inbound_rules:
            rows.append(
                {
                    **base_info,
                    "direction": "Inbound",
                    "protocol": rule.protocol,
                    "port_range": rule.port_range,
                    "source_dest": rule.source_dest,
                    "source_dest_type": rule.source_dest_type,
                    "is_ipv6": "Yes" if rule.is_ipv6 else "No",
                    "is_self_reference": "Yes" if rule.is_self_reference else "No",
                    "is_cross_account": "Yes" if rule.is_cross_account else "No",
                    "referenced_account_id": rule.referenced_account_id or "",
                    "rule_description": rule.description,
                }
            )

        # 아웃바운드 규칙
        for rule in sg.outbound_rules:
            rows.append(
                {
                    **base_info,
                    "direction": "Outbound",
                    "protocol": rule.protocol,
                    "port_range": rule.port_range,
                    "source_dest": rule.source_dest,
                    "source_dest_type": rule.source_dest_type,
                    "is_ipv6": "Yes" if rule.is_ipv6 else "No",
                    "is_self_reference": "Yes" if rule.is_self_reference else "No",
                    "is_cross_account": "Yes" if rule.is_cross_account else "No",
                    "referenced_account_id": rule.referenced_account_id or "",
                    "rule_description": rule.description,
                }
            )

        # 규칙이 없는 SG도 기록 (빈 규칙)
        if not sg.inbound_rules and not sg.outbound_rules:
            rows.append(
                {
                    **base_info,
                    "direction": "None",
                    "protocol": "",
                    "port_range": "",
                    "source_dest": "",
                    "source_dest_type": "",
                    "is_ipv6": "",
                    "is_self_reference": "",
                    "is_cross_account": "",
                    "referenced_account_id": "",
                    "rule_description": "(규칙 없음)",
                }
            )

    return rows


def _flatten_resources(sgs: list[SecurityGroup]) -> list[dict]:
    """SG에 연결된 리소스를 평탄화하여 행 데이터로 변환

    Args:
        sgs: Security Group 리스트

    Returns:
        리소스별 평탄화된 행 데이터 딕셔너리 리스트
    """
    rows = []

    for sg in sgs:
        for res in sg.attached_resources:
            rows.append(
                {
                    "account_id": sg.account_id,
                    "account_name": sg.account_name,
                    "region": sg.region,
                    "vpc_id": sg.vpc_id,
                    "sg_id": sg.sg_id,
                    "sg_name": sg.sg_name,
                    "resource_type": res.resource_type,
                    "resource_id": res.resource_id,
                    "resource_name": res.resource_name,
                    "private_ip": res.private_ip,
                    "eni_id": res.eni_id,
                }
            )

    return rows


def _create_excel_report(rows: list[dict], resource_rows: list[dict], output_path: str) -> str:
    """SG 정책 내역 Excel 보고서 생성

    SG Rules, Attached Resources, SG Summary 3개 시트를 포함하는
    Excel 파일을 생성합니다.

    Args:
        rows: 평탄화된 규칙 행 데이터
        resource_rows: 평탄화된 리소스 행 데이터
        output_path: 출력 디렉토리 경로

    Returns:
        생성된 Excel 파일 경로
    """
    wb = Workbook()

    # 전체 규칙 시트
    columns = [
        ColumnDef("계정 ID", width=15),
        ColumnDef("계정명", width=20),
        ColumnDef("리전", width=15),
        ColumnDef("VPC ID", width=22),
        ColumnDef("SG ID", width=22),
        ColumnDef("SG 이름", width=25),
        ColumnDef("SG 설명", width=30),
        ColumnDef("Default SG", width=12, style="center"),
        ColumnDef("Default VPC", width=12, style="center"),
        ColumnDef("ENI 수", width=10, style="number"),
        ColumnDef("방향", width=12, style="center"),
        ColumnDef("프로토콜", width=10, style="center"),
        ColumnDef("포트", width=12, style="center"),
        ColumnDef("소스/대상", width=25),
        ColumnDef("소스 유형", width=12, style="center"),
        ColumnDef("IPv6", width=8, style="center"),
        ColumnDef("Self 참조", width=10, style="center"),
        ColumnDef("Cross Account", width=13, style="center"),
        ColumnDef("참조 계정 ID", width=15),
        ColumnDef("규칙 설명", width=30),
    ]

    sheet = wb.new_sheet("SG Rules", columns)
    for row in rows:
        sheet.add_row(
            [
                row["account_id"],
                row["account_name"],
                row["region"],
                row["vpc_id"],
                row["sg_id"],
                row["sg_name"],
                row["sg_description"],
                row["is_default_sg"],
                row["is_default_vpc"],
                row["eni_count"],
                row["direction"],
                row["protocol"],
                row["port_range"],
                row["source_dest"],
                row["source_dest_type"],
                row["is_ipv6"],
                row["is_self_reference"],
                row["is_cross_account"],
                row["referenced_account_id"],
                row["rule_description"],
            ]
        )

    # 연결된 리소스 시트
    _add_resources_sheet(wb, resource_rows)

    # 요약 시트 (SG별 통계)
    _add_summary_sheet(wb, rows, resource_rows)

    filepath = f"{output_path}/sg_inventory.xlsx"
    wb.save(filepath)
    return filepath


def _add_resources_sheet(wb: Workbook, resource_rows: list[dict]) -> None:
    """SG에 연결된 리소스 시트 추가

    Args:
        wb: Excel Workbook 객체
        resource_rows: 평탄화된 리소스 행 데이터
    """
    columns = [
        ColumnDef("계정 ID", width=15),
        ColumnDef("계정명", width=20),
        ColumnDef("리전", width=15),
        ColumnDef("VPC ID", width=22),
        ColumnDef("SG ID", width=22),
        ColumnDef("SG 이름", width=25),
        ColumnDef("리소스 유형", width=15, style="center"),
        ColumnDef("리소스 ID", width=25),
        ColumnDef("리소스 이름", width=30),
        ColumnDef("Private IP", width=15),
        ColumnDef("ENI ID", width=25),
    ]

    sheet = wb.new_sheet("Attached Resources", columns)
    for row in resource_rows:
        sheet.add_row(
            [
                row["account_id"],
                row["account_name"],
                row["region"],
                row["vpc_id"],
                row["sg_id"],
                row["sg_name"],
                row["resource_type"],
                row["resource_id"],
                row["resource_name"],
                row["private_ip"],
                row["eni_id"],
            ]
        )


def _add_summary_sheet(wb: Workbook, rows: list[dict], resource_rows: list[dict]) -> None:
    """SG별 요약 시트 추가

    SG별 인바운드/아웃바운드 규칙 수, 연결 리소스 수를 집계합니다.

    Args:
        wb: Excel Workbook 객체
        rows: 평탄화된 규칙 행 데이터
        resource_rows: 평탄화된 리소스 행 데이터
    """
    # SG별 규칙 수 집계
    sg_stats: dict[str, dict] = {}

    for row in rows:
        sg_key = f"{row['account_id']}:{row['region']}:{row['sg_id']}"
        if sg_key not in sg_stats:
            sg_stats[sg_key] = {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "region": row["region"],
                "vpc_id": row["vpc_id"],
                "sg_id": row["sg_id"],
                "sg_name": row["sg_name"],
                "is_default_sg": row["is_default_sg"],
                "eni_count": row["eni_count"],
                "inbound_count": 0,
                "outbound_count": 0,
                "total_rules": 0,
                "resource_types": set(),
                "resource_count": 0,
            }

        if row["direction"] == "Inbound":
            sg_stats[sg_key]["inbound_count"] += 1
            sg_stats[sg_key]["total_rules"] += 1
        elif row["direction"] == "Outbound":
            sg_stats[sg_key]["outbound_count"] += 1
            sg_stats[sg_key]["total_rules"] += 1

    # 리소스 정보 집계
    for res in resource_rows:
        sg_key = f"{res['account_id']}:{res['region']}:{res['sg_id']}"
        if sg_key in sg_stats:
            sg_stats[sg_key]["resource_types"].add(res["resource_type"])
            sg_stats[sg_key]["resource_count"] += 1

    summary_columns = [
        ColumnDef("계정 ID", width=15),
        ColumnDef("계정명", width=20),
        ColumnDef("리전", width=15),
        ColumnDef("VPC ID", width=22),
        ColumnDef("SG ID", width=22),
        ColumnDef("SG 이름", width=25),
        ColumnDef("Default SG", width=12, style="center"),
        ColumnDef("ENI 수", width=10, style="number"),
        ColumnDef("Inbound 규칙", width=13, style="number"),
        ColumnDef("Outbound 규칙", width=14, style="number"),
        ColumnDef("전체 규칙", width=12, style="number"),
        ColumnDef("연결 리소스 수", width=14, style="number"),
        ColumnDef("리소스 유형", width=30),
    ]

    sheet = wb.new_sheet("SG Summary", summary_columns)
    for stat in sg_stats.values():
        resource_types = ", ".join(sorted(stat["resource_types"])) if stat["resource_types"] else "-"
        sheet.add_row(
            [
                stat["account_id"],
                stat["account_name"],
                stat["region"],
                stat["vpc_id"],
                stat["sg_id"],
                stat["sg_name"],
                stat["is_default_sg"],
                stat["eni_count"],
                stat["inbound_count"],
                stat["outbound_count"],
                stat["total_rules"],
                stat["resource_count"],
                resource_types,
            ]
        )


def _create_output_directory(ctx: ExecutionContext) -> str:
    """출력 디렉토리 생성

    Args:
        ctx: CLI 실행 컨텍스트

    Returns:
        생성된 출력 디렉토리 경로
    """
    # profile_name: SSO Session 이름 또는 프로파일 이름
    identifier = ctx.profile_name or "default"
    output_path = OutputPath(identifier).sub("vpc", "sg_inventory").with_date().build()
    return output_path


def run(ctx: ExecutionContext) -> None:
    """Security Group 정책 내역 추출 실행

    멀티 계정/리전에서 모든 Security Group의 인바운드/아웃바운드 규칙을
    병렬 수집하고, 규칙 내역 및 연결 리소스를 Excel 보고서로 출력합니다.

    Args:
        ctx: CLI 실행 컨텍스트 (인증, 계정/리전 선택, 출력 설정 포함)
    """
    console.print("[bold]Security Group 정책 내역 추출 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[#FF9900]Step 1: Security Group 데이터 수집 중...[/#FF9900]")

    result = parallel_collect(ctx, _collect_sgs, max_workers=20, service="ec2")

    # 결과 평탄화
    all_sgs: list[SecurityGroup] = []
    for sgs in result.get_data():
        if sgs:
            all_sgs.extend(sgs)

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not all_sgs:
        console.print("[yellow]수집된 Security Group이 없습니다.[/yellow]")
        return

    console.print(f"[green]총 {len(all_sgs)}개 Security Group 수집 완료[/green]")

    # 2. 규칙 평탄화
    console.print("[#FF9900]Step 2: 규칙 데이터 변환 중...[/#FF9900]")
    rows = _flatten_rules(all_sgs)
    console.print(f"[green]총 {len(rows)}개 규칙 행 생성[/green]")

    # 3. 연결된 리소스 추출
    console.print("[#FF9900]Step 3: 연결된 리소스 분석 중...[/#FF9900]")
    resource_rows = _flatten_resources(all_sgs)
    console.print(f"[green]총 {len(resource_rows)}개 리소스 연결 확인[/green]")

    # 4. Excel 보고서 생성
    console.print("[#FF9900]Step 4: Excel 보고서 생성 중...[/#FF9900]")

    output_path = _create_output_directory(ctx)
    filepath = _create_excel_report(rows, resource_rows, output_path)

    print_report_complete(filepath)

    # 폴더 열기
    open_in_explorer(output_path)
