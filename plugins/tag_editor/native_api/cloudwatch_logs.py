"""
plugins/tag_editor/native_api/cloudwatch_logs.py - CloudWatch Logs Native API

CloudWatch Logs의 태그 수집/적용을 위한 Native API 모듈

ResourceGroupsTaggingAPI는 CloudWatch Logs의 태그를 불완전하게 반환하는 경우가 있어
Native API (list_tags_for_resource, tag_resource)를 사용합니다.

참고:
- list_tags_log_group은 deprecated, list_tags_for_resource 사용 권장
- tag_log_group은 deprecated, tag_resource 사용 권장
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from core.parallel import get_client

from ..types import (
    MAP_TAG_KEY,
    MapTagApplyResult,
    ResourceTagInfo,
    TagOperationLog,
    TagOperationResult,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _get_log_group_arn(account_id: str, region: str, log_group_name: str) -> str:
    """로그 그룹 ARN 생성"""
    return f"arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}"


def collect_log_group_tags(
    session,
    account_id: str,
    account_name: str,
    region: str,
) -> list[ResourceTagInfo]:
    """CloudWatch Logs Native API로 로그 그룹 태그 수집

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 리전

    Returns:
        로그 그룹별 태그 정보 목록
    """
    resources: list[ResourceTagInfo] = []

    try:
        client = get_client(session, "logs", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: CloudWatch Logs API 접근 오류 - {e}")
        return resources

    # 모든 로그 그룹 조회
    paginator = client.get_paginator("describe_log_groups")

    try:
        for page in paginator.paginate():
            for log_group in page.get("logGroups", []):
                log_group_name = log_group.get("logGroupName", "")
                log_group_arn = log_group.get("arn", "")

                # ARN이 없으면 생성
                if not log_group_arn:
                    log_group_arn = _get_log_group_arn(account_id, region, log_group_name)

                # ARN에서 :* 제거 (CloudWatch Logs ARN 형식)
                if log_group_arn.endswith(":*"):
                    log_group_arn = log_group_arn[:-2]

                # 태그 조회 (list_tags_for_resource 사용)
                tags: dict[str, str] = {}
                try:
                    tag_response = client.list_tags_for_resource(resourceArn=log_group_arn)
                    tags = tag_response.get("tags", {})
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code != "ResourceNotFoundException":
                        logger.debug(f"로그 그룹 태그 조회 실패 {log_group_name}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"로그 그룹 태그 조회 실패 {log_group_name}: {e}")
                    continue

                # MAP 태그 확인
                has_map_tag = MAP_TAG_KEY in tags
                map_tag_value = tags.get(MAP_TAG_KEY)

                resource_info = ResourceTagInfo(
                    resource_arn=log_group_arn,
                    resource_type="logs:log-group",
                    resource_id=log_group_name,
                    name=log_group_name,  # 로그 그룹은 이름이 곧 ID
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    tags=tags,
                    has_map_tag=has_map_tag,
                    map_tag_value=map_tag_value,
                )
                resources.append(resource_info)

    except Exception as e:
        logger.warning(f"{account_name}/{region}: 로그 그룹 조회 오류 - {e}")

    return resources


def apply_log_group_tag(
    session,
    account_id: str,
    account_name: str,
    region: str,
    resources: list[ResourceTagInfo],
    tag_value: str,
    dry_run: bool = True,
) -> MapTagApplyResult:
    """CloudWatch Logs에 MAP 태그 적용

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 리전
        resources: 태그 적용 대상 로그 그룹 목록
        tag_value: MAP 태그 값 (예: mig12345)
        dry_run: True면 실제 적용하지 않음

    Returns:
        태그 적용 결과
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

    try:
        client = get_client(session, "logs", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: CloudWatch Logs API 접근 오류 - {e}")
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
        return result

    for res in resources:
        if dry_run:
            # Dry-run: 실제 적용하지 않음
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
            # 실제 태그 적용 (tag_resource 사용)
            try:
                client.tag_resource(
                    resourceArn=res.resource_arn,
                    tags={MAP_TAG_KEY: tag_value},
                )

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

    return result
