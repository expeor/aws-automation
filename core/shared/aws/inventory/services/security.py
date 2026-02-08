"""
core/shared/aws/inventory/services/security.py - Security 리소스 수집

KMS Key, Secrets Manager Secret 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import KMSKey, Secret

logger = logging.getLogger(__name__)


def collect_kms_keys(session, account_id: str, account_name: str, region: str) -> list[KMSKey]:
    """KMS Key 리소스를 수집합니다.

    먼저 Alias 매핑을 구성한 후, Key 목록을 조회하여 각 키의 상세 정보
    (상태, 용도, Spec, Origin, Key Manager 등)와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        KMSKey 데이터 클래스 목록
    """
    kms = get_client(session, "kms", region_name=region)
    keys = []

    # Alias 매핑 먼저 구성
    alias_map: dict[str, str] = {}
    try:
        paginator = kms.get_paginator("list_aliases")
        for page in paginator.paginate():
            for alias in page.get("Aliases", []):
                if alias.get("TargetKeyId"):
                    alias_map[alias["TargetKeyId"]] = alias.get("AliasName", "")
    except Exception as e:
        logger.debug("Failed to list aliases: %s", e)

    # Key 목록 조회
    paginator = kms.get_paginator("list_keys")
    for page in paginator.paginate():
        for key in page.get("Keys", []):
            key_id = key["KeyId"]
            key_arn = key["KeyArn"]

            # Key 상세 정보 조회
            try:
                desc_resp = kms.describe_key(KeyId=key_id)
                metadata = desc_resp.get("KeyMetadata", {})

                # AWS 관리형 키는 제외 옵션
                key_manager = metadata.get("KeyManager", "")

                # 태그 조회
                tags = {}
                try:
                    tags_resp = kms.list_resource_tags(KeyId=key_id)
                    tags = {tag["TagKey"]: tag["TagValue"] for tag in tags_resp.get("Tags", [])}
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

                keys.append(
                    KMSKey(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        key_id=key_id,
                        key_arn=key_arn,
                        alias=alias_map.get(key_id, ""),
                        description=metadata.get("Description", ""),
                        key_state=metadata.get("KeyState", ""),
                        key_usage=metadata.get("KeyUsage", ""),
                        key_spec=metadata.get("KeySpec", ""),
                        origin=metadata.get("Origin", ""),
                        key_manager=key_manager,
                        creation_date=metadata.get("CreationDate"),
                        enabled=metadata.get("Enabled", True),
                        multi_region=metadata.get("MultiRegion", False),
                        tags=tags,
                    )
                )
            except Exception as e:
                logger.debug("Failed to get KMS key details: %s", e)

    return keys


def collect_secrets(session, account_id: str, account_name: str, region: str) -> list[Secret]:
    """Secrets Manager Secret 리소스를 수집합니다.

    Secret 목록 조회 후 각 시크릿의 KMS 암호화 키, Rotation 설정,
    마지막 접근/회전 일시 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        Secret 데이터 클래스 목록
    """
    sm = get_client(session, "secretsmanager", region_name=region)
    secrets = []

    paginator = sm.get_paginator("list_secrets")
    for page in paginator.paginate():
        for secret in page.get("SecretList", []):
            # 태그 파싱
            tags = {tag["Key"]: tag["Value"] for tag in secret.get("Tags", [])}

            secrets.append(
                Secret(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    secret_id=secret.get("Name", ""),
                    secret_arn=secret.get("ARN", ""),
                    name=secret.get("Name", ""),
                    description=secret.get("Description", ""),
                    kms_key_id=secret.get("KmsKeyId", ""),
                    rotation_enabled=secret.get("RotationEnabled", False),
                    rotation_lambda_arn=secret.get("RotationLambdaARN", ""),
                    last_rotated_date=secret.get("LastRotatedDate"),
                    last_accessed_date=secret.get("LastAccessedDate"),
                    created_date=secret.get("CreatedDate"),
                    tags=tags,
                )
            )

    return secrets
