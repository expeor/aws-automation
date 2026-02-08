"""
core/shared/aws/inventory/services/backup.py - Backup 리소스 수집

Backup Vault, Backup Plan 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import BackupPlan, BackupVault

logger = logging.getLogger(__name__)


def collect_backup_vaults(session, account_id: str, account_name: str, region: str) -> list[BackupVault]:
    """AWS Backup Vault 리소스를 수집합니다.

    Vault 목록 조회 후 각 Vault의 암호화 키, 복구 포인트 수, 잠금 상태 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        BackupVault 데이터 클래스 목록
    """
    backup = get_client(session, "backup", region_name=region)
    vaults = []

    try:
        paginator = backup.get_paginator("list_backup_vaults")
        for page in paginator.paginate():
            for vault in page.get("BackupVaultList", []):
                vault_name = vault.get("BackupVaultName", "")
                vault_arn = vault.get("BackupVaultArn", "")

                # 태그 조회
                tags = {}
                try:
                    tags_resp = backup.list_tags(ResourceArn=vault_arn)
                    tags = tags_resp.get("Tags", {})
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

                vaults.append(
                    BackupVault(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        vault_name=vault_name,
                        vault_arn=vault_arn,
                        encryption_key_arn=vault.get("EncryptionKeyArn", ""),
                        creator_request_id=vault.get("CreatorRequestId", ""),
                        number_of_recovery_points=vault.get("NumberOfRecoveryPoints", 0),
                        locked=vault.get("Locked", False),
                        min_retention_days=vault.get("MinRetentionDays", 0),
                        max_retention_days=vault.get("MaxRetentionDays", 0),
                        creation_date=vault.get("CreationDate"),
                        tags=tags,
                    )
                )
    except Exception as e:
        logger.debug("Failed to list backup resources: %s", e)

    return vaults


def collect_backup_plans(session, account_id: str, account_name: str, region: str) -> list[BackupPlan]:
    """AWS Backup Plan 리소스를 수집합니다.

    Plan 목록 조회 후 각 Plan의 상세 정보(규칙 수, 고급 설정 여부 등)와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        BackupPlan 데이터 클래스 목록
    """
    backup = get_client(session, "backup", region_name=region)
    plans = []

    try:
        paginator = backup.get_paginator("list_backup_plans")
        for page in paginator.paginate():
            for plan in page.get("BackupPlansList", []):
                plan_id = plan.get("BackupPlanId", "")
                plan_arn = plan.get("BackupPlanArn", "")

                # 상세 정보 조회
                rule_count = 0
                advanced_settings = False
                try:
                    detail = backup.get_backup_plan(BackupPlanId=plan_id)
                    plan_detail = detail.get("BackupPlan", {})
                    rule_count = len(plan_detail.get("Rules", []))
                    advanced_settings = bool(plan_detail.get("AdvancedBackupSettings"))
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

                # 태그 조회
                tags = {}
                try:
                    tags_resp = backup.list_tags(ResourceArn=plan_arn)
                    tags = tags_resp.get("Tags", {})
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

                plans.append(
                    BackupPlan(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        backup_plan_id=plan_id,
                        backup_plan_arn=plan_arn,
                        backup_plan_name=plan.get("BackupPlanName", ""),
                        version_id=plan.get("VersionId", ""),
                        creator_request_id=plan.get("CreatorRequestId", ""),
                        rule_count=rule_count,
                        advanced_backup_settings=advanced_settings,
                        creation_date=plan.get("CreationDate"),
                        last_execution_date=plan.get("LastExecutionDate"),
                        tags=tags,
                    )
                )
    except Exception as e:
        logger.debug("Failed to list backup resources: %s", e)

    return plans
