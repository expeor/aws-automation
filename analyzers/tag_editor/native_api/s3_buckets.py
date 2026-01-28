"""
plugins/tag_editor/native_api/s3_buckets.py - S3 Buckets Native API

S3 버킷의 태그 수집/적용을 위한 Native API 모듈

중요: put_bucket_tagging은 기존 태그를 덮어쓰므로,
기존 태그를 조회하고 병합한 후 전체 태그 세트를 적용해야 합니다.

참고:
- S3는 글로벌 서비스이지만 버킷은 특정 리전에 생성됨
- 버킷 목록 조회는 어느 리전에서든 가능하지만, 보통 us-east-1에서 실행
- get_bucket_location으로 각 버킷의 실제 리전 확인 가능
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


def _get_bucket_arn(bucket_name: str) -> str:
    """S3 버킷 ARN 생성"""
    return f"arn:aws:s3:::{bucket_name}"


def _get_bucket_region(s3_client, bucket_name: str) -> str | None:
    """버킷의 실제 리전 조회

    Args:
        s3_client: S3 클라이언트
        bucket_name: 버킷 이름

    Returns:
        리전 문자열 (None이면 us-east-1)
    """
    try:
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        # LocationConstraint가 None이면 us-east-1
        location = response.get("LocationConstraint")
        return location if location else "us-east-1"
    except ClientError:
        return None


def collect_s3_bucket_tags(
    session,
    account_id: str,
    account_name: str,
    region: str,
    target_region: str | None = None,
) -> list[ResourceTagInfo]:
    """S3 Native API로 버킷 태그 수집

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 현재 실행 리전 (버킷 목록 조회용)
        target_region: 특정 리전의 버킷만 수집할 경우 지정

    Returns:
        버킷별 태그 정보 목록

    Note:
        S3는 글로벌 서비스이므로 us-east-1에서 한 번만 실행하는 것이 효율적.
        target_region을 지정하면 해당 리전의 버킷만 반환합니다.
    """
    resources: list[ResourceTagInfo] = []

    try:
        client = get_client(session, "s3", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: S3 API 접근 오류 - {e}")
        return resources

    # 모든 버킷 조회
    try:
        response = client.list_buckets()
        buckets = response.get("Buckets", [])
    except Exception as e:
        logger.warning(f"{account_name}/{region}: 버킷 목록 조회 오류 - {e}")
        return resources

    for bucket in buckets:
        bucket_name = bucket.get("Name", "")
        if not bucket_name:
            continue

        # 버킷 리전 확인
        bucket_region = _get_bucket_region(client, bucket_name)
        if bucket_region is None:
            # 리전 확인 실패 (접근 권한 없음 등)
            continue

        # target_region이 지정되었으면 해당 리전만 처리
        if target_region and bucket_region != target_region:
            continue

        bucket_arn = _get_bucket_arn(bucket_name)

        # 태그 조회
        tags: dict[str, str] = {}
        try:
            tag_response = client.get_bucket_tagging(Bucket=bucket_name)
            tag_set = tag_response.get("TagSet", [])
            tags = {t["Key"]: t["Value"] for t in tag_set}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchTagSet":
                # 태그가 없는 경우 정상
                tags = {}
            elif error_code == "AccessDenied":
                logger.debug(f"버킷 태그 조회 권한 없음 {bucket_name}")
                continue
            else:
                logger.debug(f"버킷 태그 조회 실패 {bucket_name}: {e}")
                continue
        except Exception as e:
            logger.debug(f"버킷 태그 조회 실패 {bucket_name}: {e}")
            continue

        # MAP 태그 확인
        has_map_tag = MAP_TAG_KEY in tags
        map_tag_value = tags.get(MAP_TAG_KEY)

        resource_info = ResourceTagInfo(
            resource_arn=bucket_arn,
            resource_type="s3:bucket",
            resource_id=bucket_name,
            name=bucket_name,  # 버킷은 이름이 곧 ID
            account_id=account_id,
            account_name=account_name,
            region=bucket_region,  # 버킷의 실제 리전 사용
            tags=tags,
            has_map_tag=has_map_tag,
            map_tag_value=map_tag_value,
        )
        resources.append(resource_info)

    return resources


def apply_s3_bucket_tag(
    session,
    account_id: str,
    account_name: str,
    region: str,
    resources: list[ResourceTagInfo],
    tag_value: str,
    dry_run: bool = True,
) -> MapTagApplyResult:
    """S3 버킷에 MAP 태그 적용 (기존 태그 보존!)

    중요: put_bucket_tagging은 기존 태그를 모두 덮어쓰므로,
    반드시 기존 태그를 조회하고 병합한 후 적용해야 합니다.

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 리전
        resources: 태그 적용 대상 버킷 목록
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
        client = get_client(session, "s3", region_name=region)
    except Exception as e:
        logger.warning(f"{account_name}/{region}: S3 API 접근 오류 - {e}")
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
        bucket_name = res.resource_id

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
            try:
                # 1. 기존 태그 조회 (최신 상태 확인)
                existing_tags: dict[str, str] = {}
                try:
                    tag_response = client.get_bucket_tagging(Bucket=bucket_name)
                    tag_set = tag_response.get("TagSet", [])
                    existing_tags = {t["Key"]: t["Value"] for t in tag_set}
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code != "NoSuchTagSet":
                        raise

                # 2. MAP 태그 병합 (기존 태그 보존!)
                merged_tags = existing_tags.copy()
                merged_tags[MAP_TAG_KEY] = tag_value

                # 3. 태그 세트 생성
                tag_set = [{"Key": k, "Value": v} for k, v in merged_tags.items()]

                # 4. 전체 태그 세트 적용
                client.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={"TagSet": tag_set},
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
