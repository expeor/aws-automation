"""
plugins/tag_editor/map_apply.py - MAP 태그 적용

AWS 리소스에 map-migrated 태그 일괄 적용

하이브리드 적용 전략:
- ResourceGroupsTaggingAPI: 일반 리소스 태그 적용
- CloudWatch Logs Native API: 로그 그룹 태그 적용
- S3 Native API: 버킷 태그 적용 (기존 태그 보존!)

안전장치:
- Dry-run 모드 기본 활성화
- 적용 전 확인 프롬프트
- 롤백 정보 저장

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 옵션. 사용자 입력 수집.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.parallel import get_client, parallel_collect

from .map_audit import _aggregate_stats, collect_resources_with_tags
from .native_api import (
    NATIVE_API_RESOURCE_TYPES,
    apply_log_group_tag,
    apply_s3_bucket_tag,
    collect_log_group_tags,
    collect_s3_bucket_tags,
)
from .report import generate_apply_report
from .types import (
    MAP_TAG_KEY,
    RESOURCE_TYPE_GROUPS,
    MapTagApplyResult,
    ResourceTagInfo,
    TagOperationLog,
    TagOperationResult,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

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
    "write": [
        "tag:TagResources",
        # CloudWatch Logs Native API
        "logs:TagResource",
        # S3 Native API
        "s3:PutBucketTagging",
    ],
}

console = Console()


# =============================================================================
# 태그 적용
# =============================================================================


def _apply_via_tagging_api(
    session,
    account_id: str,
    account_name: str,
    region: str,
    resources: list[ResourceTagInfo],
    tag_value: str,
    dry_run: bool,
    result: MapTagApplyResult,
) -> None:
    """ResourceGroupsTaggingAPI로 일반 리소스에 태그 적용"""
    if not resources:
        return

    try:
        client = get_client(session, "resourcegroupstaggingapi", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: Tagging API 접근 오류 - {e}")
        for res in resources:
            result.operation_logs.append(
                TagOperationLog(
                    resource_arn=res.resource_arn,
                    resource_type=res.resource_type,
                    resource_id=res.resource_id,
                    name=res.name,
                    operation="add",
                    result=TagOperationResult.FAILED,
                    error_message=str(e),
                    new_value=tag_value,
                )
            )
            result.failed_count += 1
        return

    # 배치 처리 (최대 20개씩)
    batch_size = 20
    for i in range(0, len(resources), batch_size):
        batch = resources[i : i + batch_size]
        arns = [res.resource_arn for res in batch]

        if dry_run:
            # Dry-run: 실제 적용하지 않음
            for res in batch:
                result.operation_logs.append(
                    TagOperationLog(
                        resource_arn=res.resource_arn,
                        resource_type=res.resource_type,
                        resource_id=res.resource_id,
                        name=res.name,
                        operation="add (dry-run)",
                        result=TagOperationResult.SKIPPED,
                        previous_value=res.map_tag_value,
                        new_value=tag_value,
                    )
                )
                result.skipped_count += 1
        else:
            # 실제 태그 적용
            try:
                response = client.tag_resources(
                    ResourceARNList=arns,
                    Tags={MAP_TAG_KEY: tag_value},
                )

                # 실패한 리소스 확인
                failed_arns = response.get("FailedResourcesMap", {})

                for res in batch:
                    if res.resource_arn in failed_arns:
                        error_info = failed_arns[res.resource_arn]
                        result.operation_logs.append(
                            TagOperationLog(
                                resource_arn=res.resource_arn,
                                resource_type=res.resource_type,
                                resource_id=res.resource_id,
                                name=res.name,
                                operation="add",
                                result=TagOperationResult.FAILED,
                                error_message=error_info.get("ErrorMessage", "Unknown error"),
                                previous_value=res.map_tag_value,
                                new_value=tag_value,
                            )
                        )
                        result.failed_count += 1
                    else:
                        result.operation_logs.append(
                            TagOperationLog(
                                resource_arn=res.resource_arn,
                                resource_type=res.resource_type,
                                resource_id=res.resource_id,
                                name=res.name,
                                operation="add",
                                result=TagOperationResult.SUCCESS,
                                previous_value=res.map_tag_value,
                                new_value=tag_value,
                            )
                        )
                        result.success_count += 1

            except Exception as e:
                for res in batch:
                    result.operation_logs.append(
                        TagOperationLog(
                            resource_arn=res.resource_arn,
                            resource_type=res.resource_type,
                            resource_id=res.resource_id,
                            name=res.name,
                            operation="add",
                            result=TagOperationResult.FAILED,
                            error_message=str(e),
                            previous_value=res.map_tag_value,
                            new_value=tag_value,
                        )
                    )
                    result.failed_count += 1


def apply_map_tag(
    session,
    account_id: str,
    account_name: str,
    region: str,
    resources: list[ResourceTagInfo],
    tag_value: str,
    dry_run: bool = True,
) -> MapTagApplyResult:
    """리소스에 MAP 태그 적용 (하이브리드)

    리소스 타입에 따라 적절한 API 사용:
    - logs:log-group: CloudWatch Logs Native API
    - s3:bucket: S3 Native API (기존 태그 보존!)
    - 기타: ResourceGroupsTaggingAPI
    """
    result = MapTagApplyResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        tag_value=tag_value,
        total_targeted=len(resources),
    )

    if not resources:
        return result

    # 리소스 타입별 분류
    logs_resources = [r for r in resources if r.resource_type == "logs:log-group"]
    s3_resources = [r for r in resources if r.resource_type == "s3:bucket"]
    tagging_api_resources = [r for r in resources if r.resource_type not in NATIVE_API_RESOURCE_TYPES]

    # 1. ResourceGroupsTaggingAPI로 일반 리소스 적용
    _apply_via_tagging_api(session, account_id, account_name, region, tagging_api_resources, tag_value, dry_run, result)

    # 2. CloudWatch Logs Native API로 로그 그룹 적용
    if logs_resources:
        try:
            logs_result = apply_log_group_tag(
                session, account_id, account_name, region, logs_resources, tag_value, dry_run
            )
            # 결과 병합
            result.operation_logs.extend(logs_result.operation_logs)
            result.success_count += logs_result.success_count
            result.failed_count += logs_result.failed_count
            result.skipped_count += logs_result.skipped_count
        except Exception as e:
            logger.warning(f"{account_name}/{region}: CloudWatch Logs 태그 적용 오류 - {e}")
            for res in logs_resources:
                result.operation_logs.append(
                    TagOperationLog(
                        resource_arn=res.resource_arn,
                        resource_type=res.resource_type,
                        resource_id=res.resource_id,
                        name=res.name,
                        operation="add",
                        result=TagOperationResult.FAILED,
                        error_message=str(e),
                        new_value=tag_value,
                    )
                )
                result.failed_count += 1

    # 3. S3 Native API로 버킷 적용 (기존 태그 보존!)
    if s3_resources:
        try:
            s3_result = apply_s3_bucket_tag(session, account_id, account_name, region, s3_resources, tag_value, dry_run)
            # 결과 병합
            result.operation_logs.extend(s3_result.operation_logs)
            result.success_count += s3_result.success_count
            result.failed_count += s3_result.failed_count
            result.skipped_count += s3_result.skipped_count
        except Exception as e:
            logger.warning(f"{account_name}/{region}: S3 태그 적용 오류 - {e}")
            for res in s3_resources:
                result.operation_logs.append(
                    TagOperationLog(
                        resource_arn=res.resource_arn,
                        resource_type=res.resource_type,
                        resource_id=res.resource_id,
                        name=res.name,
                        operation="add",
                        result=TagOperationResult.FAILED,
                        error_message=str(e),
                        new_value=tag_value,
                    )
                )
                result.failed_count += 1

    return result


# =============================================================================
# 옵션 수집
# =============================================================================


def _select_resource_types() -> list[str] | None:
    """리소스 타입 선택"""
    console.print("\n[bold]리소스 타입 선택[/bold]")
    console.print("1. 전체 리소스")
    console.print("2. 카테고리별 선택")
    console.print("3. 개별 타입 선택")

    choice = Prompt.ask("선택", choices=["1", "2", "3"], default="1")

    if choice == "1":
        return None  # 전체

    if choice == "2":
        console.print("\n[bold]카테고리 선택[/bold]")
        categories = list(RESOURCE_TYPE_GROUPS.keys())
        for i, cat in enumerate(categories, 1):
            types_count = len(RESOURCE_TYPE_GROUPS[cat])
            console.print(f"{i}. {cat} ({types_count} types)")

        selected = Prompt.ask("선택 (쉼표로 구분)", default="1")
        selected_indices = [int(s.strip()) - 1 for s in selected.split(",")]

        resource_types = []
        for idx in selected_indices:
            if 0 <= idx < len(categories):
                resource_types.extend(RESOURCE_TYPE_GROUPS[categories[idx]])

        return resource_types if resource_types else None

    if choice == "3":
        console.print("\n[dim]예: ec2:instance, rds:db, lambda:function[/dim]")
        types_input = Prompt.ask("리소스 타입 입력 (쉼표로 구분)")
        return [t.strip() for t in types_input.split(",") if t.strip()]

    return None


def collect_options(ctx: ExecutionContext) -> None:
    """MAP 태그 적용 옵션 수집"""
    console.print("\n[bold cyan]MAP 태그 적용 설정[/bold cyan]")

    # 1. MAP 태그 값 입력
    console.print("\n[bold]태그 설정[/bold]")
    console.print(f"태그 키: {MAP_TAG_KEY}")
    console.print("\n[dim]태그 값 형식 (MPE ID 기반):[/dim]")
    console.print("[dim]  - 일반 마이그레이션: mig12345 또는 migABCDE12345[/dim]")
    console.print("[dim]  - SAP 워크로드: sap12345 또는 sapABCDE12345[/dim]")
    console.print("[dim]  - Oracle 워크로드: oracle12345 또는 oracleABCDE12345[/dim]")
    console.print("[dim]  - Commercial DB&A: comm12345 또는 commABCDE12345[/dim]")
    console.print("[dim]  - EC2 → AWS DB&A: mig_ec2_12345 또는 comm_ec2_12345[/dim]")

    tag_value = Prompt.ask("\n태그 값 입력")
    ctx.options["tag_value"] = tag_value

    # 2. 대상 선택
    console.print("\n[bold]적용 대상 선택[/bold]")
    console.print("1. 미태그 리소스만 (권장)")
    console.print("2. 전체 리소스 (기존 값 덮어쓰기)")

    target_choice = Prompt.ask("선택", choices=["1", "2"], default="1")
    ctx.options["untagged_only"] = target_choice == "1"

    # 3. 리소스 타입 선택
    resource_types = _select_resource_types()
    ctx.options["resource_types"] = resource_types

    # 4. Dry-run 모드
    dry_run = Confirm.ask(
        "\nDry-run 모드로 실행? (실제 적용하지 않음)",
        default=True,
    )
    ctx.options["dry_run"] = dry_run

    if not dry_run:
        # 실제 적용 시 재확인
        console.print("\n[yellow bold]경고: 실제로 태그가 적용됩니다![/yellow bold]")
        confirm = Confirm.ask("계속하시겠습니까?", default=False)
        if not confirm:
            ctx.options["dry_run"] = True
            console.print("[dim]Dry-run 모드로 전환됨[/dim]")


# =============================================================================
# 실행
# =============================================================================


def _collect_and_apply(
    session,
    account_id: str,
    account_name: str,
    region: str,
    tag_value: str,
    untagged_only: bool,
    dry_run: bool,
) -> MapTagApplyResult:
    """단일 계정/리전의 MAP 태그 적용 (하이브리드 수집)

    하이브리드 수집 전략:
    1. ResourceGroupsTaggingAPI로 일반 리소스 수집
    2. CloudWatch Logs Native API로 로그 그룹 수집
    3. S3 Native API로 버킷 수집 (리전별)
    """
    # 1. Tagging API로 기본 수집
    audit_result = collect_resources_with_tags(session, account_id, account_name, region)

    # 2. Native API 리소스 제거 (중복 방지)
    audit_result.resources = [r for r in audit_result.resources if r.resource_type not in NATIVE_API_RESOURCE_TYPES]

    # 3. CloudWatch Logs Native API로 로그 그룹 수집
    try:
        log_resources = collect_log_group_tags(session, account_id, account_name, region)
        audit_result.resources.extend(log_resources)
    except Exception as e:
        logger.debug(f"{account_name}/{region}: CloudWatch Logs 수집 오류 - {e}")

    # 4. S3 Native API로 버킷 수집 (해당 리전의 버킷만)
    try:
        s3_resources = collect_s3_bucket_tags(session, account_id, account_name, region, target_region=region)
        audit_result.resources.extend(s3_resources)
    except Exception as e:
        logger.debug(f"{account_name}/{region}: S3 수집 오류 - {e}")

    # 5. 통계 재계산
    _aggregate_stats(audit_result)

    # 6. 대상 필터링
    targets = [r for r in audit_result.resources if not r.has_map_tag] if untagged_only else audit_result.resources

    if not targets:
        return MapTagApplyResult(
            account_id=account_id,
            account_name=account_name,
            region=region,
            tag_value=tag_value,
        )

    # 7. 태그 적용 (하이브리드)
    return apply_map_tag(session, account_id, account_name, region, targets, tag_value, dry_run)


def run(ctx: ExecutionContext) -> None:
    """MAP 태그 적용 실행"""
    tag_value = ctx.options.get("tag_value", "")
    if not tag_value:
        console.print("[red]태그 값이 설정되지 않았습니다.[/red]")
        return

    untagged_only = ctx.options.get("untagged_only", True)
    dry_run = ctx.options.get("dry_run", True)

    mode_str = "[yellow](Dry-run)[/yellow]" if dry_run else "[red](실제 적용)[/red]"
    target_str = "미태그 리소스" if untagged_only else "전체 리소스"

    console.print(f"[bold]MAP 태그 적용 시작... {mode_str}[/bold]\n")
    console.print(f"태그: {MAP_TAG_KEY} = {tag_value}")
    console.print(f"대상: {target_str}\n")

    # 병렬 수집 및 적용
    def worker(session, account_id: str, account_name: str, region: str):
        return _collect_and_apply(session, account_id, account_name, region, tag_value, untagged_only, dry_run)

    result = parallel_collect(ctx, worker, max_workers=10, service="resourcegroupstaggingapi")

    results: list[MapTagApplyResult] = result.get_data()

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not results:
        console.print("\n[yellow]적용 결과 없음[/yellow]")
        return

    # 빈 결과 제외
    results = [r for r in results if r.total_targeted > 0]

    if not results:
        console.print("\n[yellow]적용 대상 리소스 없음[/yellow]")
        return

    # 요약
    total_targeted = sum(r.total_targeted for r in results)
    total_success = sum(r.success_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    total_skipped = sum(r.skipped_count for r in results)

    console.print("\n[bold]적용 결과[/bold]")

    table = Table(show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("개수", justify="right")

    table.add_row("대상 리소스", str(total_targeted))
    if total_success > 0:
        table.add_row("성공", f"[green]{total_success}[/green]")
    if total_failed > 0:
        table.add_row("실패", f"[red]{total_failed}[/red]")
    if total_skipped > 0:
        table.add_row("스킵 (dry-run)", f"[yellow]{total_skipped}[/yellow]")

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry-run 모드: 실제 태그는 적용되지 않았습니다.[/yellow]")
        console.print("[dim]실제 적용하려면 dry-run 모드를 해제하고 다시 실행하세요.[/dim]")

    # 보고서 생성
    from core.tools.output import OutputPath, open_in_explorer

    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("tag", "compliance").with_date().build()
    filepath = generate_apply_report(results, output_path)

    console.print(f"\n[bold green]완료![/bold green] {filepath}")
    open_in_explorer(output_path)
