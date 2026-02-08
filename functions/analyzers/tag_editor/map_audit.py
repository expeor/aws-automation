"""
plugins/tag_editor/map_audit.py - MAP 태그 현황 분석

AWS 리소스의 map-migrated 태그 현황을 분석하고 리포트 생성

분석 기준:
- ResourceGroupsTaggingAPI로 전체 리소스 스캔
- Native API로 CloudWatch Logs, S3 버킷 태그 수집 (Tagging API가 불완전한 서비스)
- map-migrated 태그 유무 확인
- 리소스 타입별 통계 집계

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 옵션. 사용자 입력 수집.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from core.parallel import get_client, parallel_collect

from .native_api import NATIVE_API_RESOURCE_TYPES, collect_log_group_tags, collect_s3_bucket_tags
from .report import generate_audit_report
from .types import (
    MAP_TAG_KEY,
    MapTagAnalysisResult,
    ResourceTagInfo,
    ResourceTypeStats,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "tag:GetResources",
        # CloudWatch Logs Native API
        "logs:DescribeLogGroups",
        "logs:ListTagsForResource",
        # S3 Native API
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketTagging",
    ],
}

console = Console()


# =============================================================================
# 리소스 수집
# =============================================================================


def _parse_arn(arn: str) -> dict[str, str]:
    """ARN 파싱하여 리소스 정보 추출

    ARN format: arn:partition:service:region:account-id:resource-type/resource-id
    """
    parts = arn.split(":")
    if len(parts) < 6:
        return {
            "service": "",
            "region": "",
            "account_id": "",
            "resource_type": "",
            "resource_id": "",
        }

    service = parts[2]
    region = parts[3]
    account_id = parts[4]

    # resource-type/resource-id 또는 resource-type:resource-id
    resource_part = ":".join(parts[5:])
    if "/" in resource_part:
        resource_type, resource_id = resource_part.split("/", 1)
    elif ":" in resource_part:
        resource_type, resource_id = resource_part.split(":", 1)
    else:
        resource_type = resource_part
        resource_id = resource_part

    return {
        "service": service,
        "region": region,
        "account_id": account_id,
        "resource_type": f"{service}:{resource_type}",
        "resource_id": resource_id,
    }


def _get_resource_name(tags: dict[str, str]) -> str:
    """태그에서 Name 추출"""
    return tags.get("Name", tags.get("name", ""))


def collect_resources_with_tags(
    session,
    account_id: str,
    account_name: str,
    region: str,
    resource_types: list[str] | None = None,
) -> MapTagAnalysisResult:
    """ResourceGroupsTaggingAPI로 리소스 수집 및 태그 분석"""
    result = MapTagAnalysisResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
    )

    try:
        client = get_client(session, "resourcegroupstaggingapi", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: API 접근 오류 - {e}")
        return result

    # 리소스 타입별 통계
    type_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "tagged": 0})

    # 페이지네이션으로 모든 리소스 조회
    paginator = client.get_paginator("get_resources")

    # 리소스 타입 필터 설정
    paginate_kwargs = {}
    if resource_types:
        paginate_kwargs["ResourceTypeFilters"] = resource_types

    try:
        for page in paginator.paginate(**paginate_kwargs):
            for resource in page.get("ResourceTagMappingList", []):
                arn = resource.get("ResourceARN", "")
                tags_list = resource.get("Tags", [])

                # 태그를 dict로 변환
                tags = {t["Key"]: t["Value"] for t in tags_list}

                # ARN 파싱
                arn_info = _parse_arn(arn)
                resource_type = arn_info["resource_type"]

                # map-migrated 태그 확인
                has_map_tag = MAP_TAG_KEY in tags
                map_tag_value = tags.get(MAP_TAG_KEY)

                # 리소스 정보 생성
                resource_info = ResourceTagInfo(
                    resource_arn=arn,
                    resource_type=resource_type,
                    resource_id=arn_info["resource_id"],
                    name=_get_resource_name(tags),
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    tags=tags,
                    has_map_tag=has_map_tag,
                    map_tag_value=map_tag_value,
                )
                result.resources.append(resource_info)

                # 통계 업데이트
                type_counts[resource_type]["total"] += 1
                if has_map_tag:
                    type_counts[resource_type]["tagged"] += 1
                    result.tagged_resources += 1
                else:
                    result.untagged_resources += 1

                result.total_resources += 1

    except Exception as e:
        logger.warning(f"{account_name}/{region}: 리소스 조회 오류 - {e}")
        return result

    # 리소스 타입별 통계 객체 생성
    for res_type, counts in type_counts.items():
        # 표시 이름 생성 (ec2:instance -> EC2 Instance)
        parts = res_type.split(":")
        display_name = " ".join(p.capitalize() for p in parts)

        result.type_stats.append(
            ResourceTypeStats(
                resource_type=res_type,
                display_name=display_name,
                total=counts["total"],
                tagged=counts["tagged"],
                untagged=counts["total"] - counts["tagged"],
            )
        )

    # 정렬 (total 내림차순)
    result.type_stats.sort(key=lambda x: x.total, reverse=True)

    return result


# =============================================================================
# 분석 및 출력
# =============================================================================


def _aggregate_stats(result: MapTagAnalysisResult) -> None:
    """리소스 목록에서 통계 재계산"""
    # 기존 통계 초기화
    result.total_resources = 0
    result.tagged_resources = 0
    result.untagged_resources = 0
    result.type_stats = []

    # 리소스 타입별 통계
    type_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "tagged": 0})

    for res in result.resources:
        result.total_resources += 1
        if res.has_map_tag:
            result.tagged_resources += 1
            type_counts[res.resource_type]["tagged"] += 1
        else:
            result.untagged_resources += 1
        type_counts[res.resource_type]["total"] += 1

    # 리소스 타입별 통계 객체 생성
    for res_type, counts in type_counts.items():
        # 표시 이름 생성 (ec2:instance -> EC2 Instance)
        parts = res_type.split(":")
        display_name = " ".join(p.capitalize() for p in parts)

        result.type_stats.append(
            ResourceTypeStats(
                resource_type=res_type,
                display_name=display_name,
                total=counts["total"],
                tagged=counts["tagged"],
                untagged=counts["total"] - counts["tagged"],
            )
        )

    # 정렬 (total 내림차순)
    result.type_stats.sort(key=lambda x: x.total, reverse=True)


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> MapTagAnalysisResult:
    """단일 계정/리전의 MAP 태그 분석 (병렬 실행용)

    하이브리드 수집 전략:
    1. ResourceGroupsTaggingAPI로 일반 리소스 수집
    2. CloudWatch Logs Native API로 로그 그룹 태그 수집
    3. S3 Native API로 버킷 태그 수집 (us-east-1에서만)

    Native API 수집 결과는 Tagging API 결과를 대체합니다.
    """
    # 1. Tagging API로 기본 수집
    result = collect_resources_with_tags(session, account_id, account_name, region)

    # 2. Native API 리소스 제거 (중복 방지)
    # Tagging API가 불완전하게 반환하는 리소스 타입 제거
    result.resources = [r for r in result.resources if r.resource_type not in NATIVE_API_RESOURCE_TYPES]

    # 3. CloudWatch Logs Native API로 로그 그룹 수집
    try:
        log_resources = collect_log_group_tags(session, account_id, account_name, region)
        result.resources.extend(log_resources)
    except Exception as e:
        logger.debug(f"{account_name}/{region}: CloudWatch Logs 수집 오류 - {e}")

    # 4. S3 Native API로 버킷 수집 (us-east-1에서만, 또는 해당 리전 버킷만)
    # S3는 글로벌 서비스이므로 리전별로 실행하되, 해당 리전의 버킷만 수집
    try:
        s3_resources = collect_s3_bucket_tags(session, account_id, account_name, region, target_region=region)
        result.resources.extend(s3_resources)
    except Exception as e:
        logger.debug(f"{account_name}/{region}: S3 수집 오류 - {e}")

    # 5. 통계 재계산
    _aggregate_stats(result)

    return result


def _print_summary_table(results: list[MapTagAnalysisResult]) -> None:
    """콘솔에 요약 테이블 출력"""
    # 전체 통계
    total_resources = sum(r.total_resources for r in results)
    total_tagged = sum(r.tagged_resources for r in results)
    total_untagged = sum(r.untagged_resources for r in results)
    overall_rate = (total_tagged / total_resources * 100) if total_resources > 0 else 0

    console.print("\n[bold]전체 MAP 태그 현황[/bold]")
    console.print(f"총 리소스: {total_resources:,}개")
    console.print(f"태그됨: [green]{total_tagged:,}개[/green] ({overall_rate:.1f}%)")
    console.print(f"미태그: [red]{total_untagged:,}개[/red]")

    # 리소스 타입별 통계 집계
    type_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "tagged": 0})
    for r in results:
        for ts in r.type_stats:
            type_totals[ts.resource_type]["total"] += ts.total
            type_totals[ts.resource_type]["tagged"] += ts.tagged

    # 테이블 출력
    if type_totals:
        console.print("\n[bold]리소스 타입별 현황[/bold]")
        table = Table(show_header=True)
        table.add_column("리소스 타입", style="cyan")
        table.add_column("전체", justify="right")
        table.add_column("태그됨", justify="right", style="green")
        table.add_column("미태그", justify="right", style="red")
        table.add_column("적용률", justify="right")

        # 정렬 (total 내림차순)
        sorted_types = sorted(type_totals.items(), key=lambda x: x[1]["total"], reverse=True)

        for res_type, counts in sorted_types[:15]:  # 상위 15개만
            total = counts["total"]
            tagged = counts["tagged"]
            untagged = total - tagged
            rate = (tagged / total * 100) if total > 0 else 0

            # 표시 이름
            parts = res_type.split(":")
            display = " ".join(p.capitalize() for p in parts)

            table.add_row(
                display,
                str(total),
                str(tagged),
                str(untagged),
                f"{rate:.1f}%",
            )

        console.print(table)

        if len(sorted_types) > 15:
            console.print(f"[dim]... 외 {len(sorted_types) - 15}개 타입[/dim]")


# =============================================================================
# 실행
# =============================================================================


def collect_options(ctx: ExecutionContext) -> None:
    """MAP 태그 분석 옵션 수집"""
    from rich.prompt import Confirm

    console.print("\n[bold cyan]MAP 태그 분석 설정[/bold cyan]")

    # 리소스 타입 선택 옵션 (향후 확장)
    # 현재는 전체 리소스 분석
    ctx.options["resource_types"] = None  # None = 전체

    # 미태그 리소스만 표시 옵션
    show_untagged_only = Confirm.ask(
        "미태그 리소스만 리포트에 포함?",
        default=False,
    )
    ctx.options["untagged_only"] = show_untagged_only


def run(ctx: ExecutionContext) -> None:
    """MAP 태그 분석 실행"""
    console.print("[bold]MAP 태그 분석 시작...[/bold]\n")
    console.print(f"[dim]분석 태그: {MAP_TAG_KEY}[/dim]\n")

    # 병렬 수집 및 분석
    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="resourcegroupstaggingapi")

    results: list[MapTagAnalysisResult] = result.get_data()

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not results:
        console.print("\n[yellow]분석 결과 없음[/yellow]")
        return

    # 빈 결과 제외
    results = [r for r in results if r.total_resources > 0]

    if not results:
        console.print("\n[yellow]태그 분석 대상 리소스 없음[/yellow]")
        return

    # 요약 출력
    _print_summary_table(results)

    # 보고서 생성
    from core.shared.io.output import OutputPath, get_context_identifier, open_in_explorer

    identifier = get_context_identifier(ctx)

    untagged_only = ctx.options.get("untagged_only", False)

    output_path = OutputPath(identifier).sub("tag", "compliance").with_date().build()
    filepath = generate_audit_report(results, output_path, untagged_only=untagged_only)

    console.print(f"\n[bold green]완료![/bold green] {filepath}")
    open_in_explorer(output_path)
