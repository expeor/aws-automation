"""
plugins/cloudtrail/trail_audit.py - CloudTrail 전체 계정 보고서

전체 계정의 CloudTrail을 조회하고 분석합니다:
- Trail 목록 및 상세 정보
- Management Event 활성화 여부
- Data Event 활성화 여부
- Logging 활성화 여부
- Multi-region / Global Service Events 설정

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.parallel import get_client, parallel_collect
from shared.io.excel import ColumnDef, Workbook

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "cloudtrail:ListTrails",
        "cloudtrail:DescribeTrails",
        "cloudtrail:GetEventSelectors",
        "cloudtrail:GetTrailStatus",
    ],
}


@dataclass
class TrailInfo:
    """CloudTrail 정보"""

    account_id: str
    account_name: str
    region: str
    trail_name: str
    trail_arn: str
    is_logging: bool
    management_events_enabled: bool
    data_events_enabled: bool
    is_multi_region: bool
    include_global_events: bool
    s3_bucket: str
    s3_prefix: str
    kms_key_id: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "region": self.region,
            "trail_name": self.trail_name,
            "trail_arn": self.trail_arn,
            "is_logging": self.is_logging,
            "management_events_enabled": self.management_events_enabled,
            "data_events_enabled": self.data_events_enabled,
            "is_multi_region": self.is_multi_region,
            "include_global_events": self.include_global_events,
            "s3_bucket": self.s3_bucket,
            "s3_prefix": self.s3_prefix,
            "kms_key_id": self.kms_key_id,
            "error": self.error,
        }


@dataclass
class TrailAuditResult:
    """CloudTrail 감사 결과"""

    account_id: str
    account_name: str
    region: str
    trails: list[TrailInfo] = field(default_factory=list)
    total_count: int = 0
    logging_enabled_count: int = 0
    management_events_count: int = 0
    data_events_count: int = 0
    multi_region_count: int = 0


def collect_trails(session, account_id: str, account_name: str, region: str) -> list[TrailInfo]:
    """CloudTrail 정보 수집"""
    from botocore.exceptions import ClientError

    cloudtrail = get_client(session, "cloudtrail", region_name=region)
    trails = []

    try:
        # Trail 목록 조회
        response = cloudtrail.list_trails()
        trail_list = response.get("Trails", [])

        for trail in trail_list:
            trail_name = trail.get("Name", "")
            trail_arn = trail.get("TrailARN", "")

            trail_info = TrailInfo(
                account_id=account_id,
                account_name=account_name,
                region=region,
                trail_name=trail_name,
                trail_arn=trail_arn,
                is_logging=False,
                management_events_enabled=False,
                data_events_enabled=False,
                is_multi_region=False,
                include_global_events=False,
                s3_bucket="",
                s3_prefix="",
                kms_key_id="",
            )

            try:
                # Trail 상세 정보 조회
                detail_response = cloudtrail.describe_trails(trailNameList=[trail_arn])
                trail_details = detail_response.get("trailList", [])

                if trail_details:
                    detail = trail_details[0]
                    trail_info.is_multi_region = detail.get("IsMultiRegionTrail", False)
                    trail_info.include_global_events = detail.get("IncludeGlobalServiceEvents", False)
                    trail_info.s3_bucket = detail.get("S3BucketName", "")
                    trail_info.s3_prefix = detail.get("S3KeyPrefix", "")
                    trail_info.kms_key_id = detail.get("KMSKeyId", "")

                # Event Selector 정보 조회
                try:
                    event_selectors_response = cloudtrail.get_event_selectors(TrailName=trail_arn)
                    event_selectors = event_selectors_response.get("EventSelectors", [])

                    for selector in event_selectors:
                        if selector.get("ReadWriteType") in [
                            "All",
                            "ReadOnly",
                            "WriteOnly",
                        ] and selector.get("IncludeManagementEvents", False):
                            trail_info.management_events_enabled = True

                        data_resources = selector.get("DataResources", [])
                        if data_resources:
                            trail_info.data_events_enabled = True

                except ClientError as e:
                    logger.warning(f"Event Selector 조회 실패 {trail_name}: {e}")

                # Trail 상태 조회
                try:
                    status_response = cloudtrail.get_trail_status(Name=trail_arn)
                    trail_info.is_logging = status_response.get("IsLogging", False)
                except ClientError as e:
                    logger.warning(f"Trail 상태 조회 실패 {trail_name}: {e}")

            except ClientError as e:
                trail_info.error = str(e)
                logger.warning(f"Trail 상세정보 조회 실패 {trail_name}: {e}")

            trails.append(trail_info)

    except ClientError as e:
        logger.error(f"{account_name}/{region} CloudTrail 조회 실패: {e}")

    return trails


def analyze_trails(trails: list[TrailInfo], account_id: str, account_name: str, region: str) -> TrailAuditResult:
    """CloudTrail 분석"""
    result = TrailAuditResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        trails=trails,
        total_count=len(trails),
    )

    for trail in trails:
        if trail.is_logging:
            result.logging_enabled_count += 1
        if trail.management_events_enabled:
            result.management_events_count += 1
        if trail.data_events_enabled:
            result.data_events_count += 1
        if trail.is_multi_region:
            result.multi_region_count += 1

    return result


# 리포트 컬럼 정의
COLUMNS_TRAILS = [
    ColumnDef(header="Account", width=20, style="data"),
    ColumnDef(header="Region", width=15, style="center"),
    ColumnDef(header="Trail Name", width=25, style="data"),
    ColumnDef(header="Logging", width=10, style="center"),
    ColumnDef(header="Mgmt Events", width=12, style="center"),
    ColumnDef(header="Data Events", width=12, style="center"),
    ColumnDef(header="Multi-Region", width=12, style="center"),
    ColumnDef(header="Global Events", width=12, style="center"),
    ColumnDef(header="S3 Bucket", width=30, style="data"),
    ColumnDef(header="KMS Key", width=20, style="data"),
]


class TrailAuditReporter:
    """CloudTrail 감사 결과 리포터"""

    def __init__(self, results: list[TrailAuditResult]):
        self.results = results

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "cloudtrail_audit",
    ) -> Path:
        """Excel 리포트 생성"""
        wb = Workbook()

        # 요약 시트
        self._create_summary_sheet(wb)

        # 상세 시트
        self._create_detail_sheet(wb)

        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"리포트 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """요약 시트"""
        summary = wb.new_summary_sheet("CloudTrail 감사 요약")

        summary.add_title("CloudTrail 전체 계정 보고서")

        total_trails = sum(r.total_count for r in self.results)
        total_logging = sum(r.logging_enabled_count for r in self.results)
        total_mgmt = sum(r.management_events_count for r in self.results)
        total_data = sum(r.data_events_count for r in self.results)
        total_multi = sum(r.multi_region_count for r in self.results)

        summary.add_section("전체 현황")
        summary.add_item("총 Trail 수", f"{total_trails}개")
        summary.add_item("Logging 활성화", f"{total_logging}개")
        summary.add_item("Management Events 활성화", f"{total_mgmt}개")
        summary.add_item("Data Events 활성화", f"{total_data}개")
        summary.add_item("Multi-Region Trail", f"{total_multi}개")

        summary.add_blank_row()

        summary.add_section("계정별 현황")
        for r in self.results:
            if r.total_count > 0:
                summary.add_item(
                    r.account_name,
                    f"{r.total_count}개 (로깅: {r.logging_enabled_count})",
                )

        summary.add_blank_row()

        summary.add_section("리포트 정보")
        summary.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _create_detail_sheet(self, wb: Workbook) -> None:
        """상세 시트"""
        sheet = wb.new_sheet(name="Trail Details", columns=COLUMNS_TRAILS)

        for result in self.results:
            for trail in result.trails:
                row = [
                    trail.account_name,
                    trail.region,
                    trail.trail_name,
                    "Yes" if trail.is_logging else "No",
                    "Yes" if trail.management_events_enabled else "No",
                    "Yes" if trail.data_events_enabled else "No",
                    "Yes" if trail.is_multi_region else "No",
                    "Yes" if trail.include_global_events else "No",
                    trail.s3_bucket,
                    trail.kms_key_id[:20] + "..." if len(trail.kms_key_id) > 20 else trail.kms_key_id,
                ]
                sheet.add_row(row)

    def print_summary(self) -> None:
        """콘솔에 요약 출력"""
        total_trails = sum(r.total_count for r in self.results)
        total_logging = sum(r.logging_enabled_count for r in self.results)

        print("\n=== CloudTrail 감사 결과 ===")
        print(f"총 Trail 수: {total_trails}개")
        print(f"Logging 활성화: {total_logging}개")

        if total_trails > 0:
            print("\n계정별 현황:")
            for r in self.results:
                if r.total_count > 0:
                    print(f"  {r.account_name}: {r.total_count}개 Trail")


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> TrailAuditResult | None:
    """단일 계정/리전의 CloudTrail 수집 및 분석 (병렬 실행용)"""
    trails = collect_trails(session, account_id, account_name, region)
    if not trails:
        return None
    return analyze_trails(trails, account_id, account_name, region)


def run(ctx: ExecutionContext) -> None:
    """CloudTrail 전체 계정 보고서 생성"""
    from rich.console import Console

    from shared.io.output import OutputPath, open_in_explorer

    console = Console()
    console.print("[bold]CloudTrail 전체 계정 보고서 생성 시작...[/bold]\n")

    # 병렬 수집 및 분석
    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="cloudtrail")
    results: list[TrailAuditResult] = [r for r in result.get_data() if r is not None]

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")

    if not results:
        console.print("\n[yellow]분석 결과 없음[/yellow]")
        return

    reporter = TrailAuditReporter(results)
    reporter.print_summary()

    # 출력 경로 생성
    from shared.io.output import get_context_identifier

    identifier = get_context_identifier(ctx)

    output_dir = OutputPath(identifier).sub("cloudtrail", "inventory").with_date().build()
    output_path = reporter.generate_report(output_dir=output_dir, file_prefix="cloudtrail_audit")

    console.print(f"\n[bold green]완료![/bold green] {output_path}")
    open_in_explorer(output_dir)
