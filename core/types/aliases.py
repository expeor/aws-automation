"""
core/types/aliases.py - 타입 별칭 정의

AWS 리소스 식별자와 공통 타입에 대한 별칭을 정의합니다.
코드 가독성과 타입 안전성을 높이기 위해 사용합니다.

Usage:
    from core.types.aliases import AccountId, RegionName, ResourceId

    def get_resource(account: AccountId, region: RegionName) -> ResourceId:
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NewType, TypeAlias

# =============================================================================
# AWS 식별자 타입
# =============================================================================

# 계정 식별자 (12자리 숫자 문자열)
AccountId = NewType("AccountId", str)

# 리전 이름 (예: ap-northeast-2)
RegionName = NewType("RegionName", str)

# 리소스 ID (서비스별 고유 식별자)
ResourceId = NewType("ResourceId", str)

# ARN (Amazon Resource Name)
Arn = NewType("Arn", str)

# IAM Role 이름
RoleName = NewType("RoleName", str)

# 프로파일 이름
ProfileName = NewType("ProfileName", str)

# =============================================================================
# 리소스 별 식별자 타입
# =============================================================================

# EC2
InstanceId = NewType("InstanceId", str)
VolumeId = NewType("VolumeId", str)
SnapshotId = NewType("SnapshotId", str)
ImageId = NewType("ImageId", str)
SecurityGroupId = NewType("SecurityGroupId", str)

# VPC
VpcId = NewType("VpcId", str)
SubnetId = NewType("SubnetId", str)
RouteTableId = NewType("RouteTableId", str)
InternetGatewayId = NewType("InternetGatewayId", str)
NatGatewayId = NewType("NatGatewayId", str)
NetworkInterfaceId = NewType("NetworkInterfaceId", str)

# S3
BucketName = NewType("BucketName", str)

# RDS
DBInstanceId = NewType("DBInstanceId", str)
DBClusterId = NewType("DBClusterId", str)

# Lambda
FunctionName = NewType("FunctionName", str)

# IAM
UserName = NewType("UserName", str)
GroupName = NewType("GroupName", str)
PolicyArn = NewType("PolicyArn", str)

# CloudWatch
LogGroupName = NewType("LogGroupName", str)
MetricName = NewType("MetricName", str)
AlarmName = NewType("AlarmName", str)
DimensionName = NewType("DimensionName", str)
DimensionValue = NewType("DimensionValue", str)

# KMS
KeyId = NewType("KeyId", str)

# Secrets Manager
SecretId = NewType("SecretId", str)

# =============================================================================
# 공통 타입 별칭
# =============================================================================

# JSON 호환 타입
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonDict: TypeAlias = dict[str, JsonValue]
JsonList: TypeAlias = list[JsonValue]

# AWS 태그
TagKey = NewType("TagKey", str)
TagValue = NewType("TagValue", str)
Tags: TypeAlias = dict[str, str]

# 시간 관련
IsoTimestamp = NewType("IsoTimestamp", str)
UnixTimestamp = NewType("UnixTimestamp", int)

# CIDR 블록
CidrBlock = NewType("CidrBlock", str)

# IP 주소
IpAddress = NewType("IpAddress", str)

# =============================================================================
# 콜백 타입 별칭
# =============================================================================

# 병렬 수집 콜백 반환 타입
CollectResult: TypeAlias = list[dict[str, JsonValue]]

# 에러 핸들러 콜백
if TYPE_CHECKING:
    from collections.abc import Callable

    ErrorHandler: TypeAlias = Callable[[Exception, str, str], None]


# =============================================================================
# 유틸리티 함수
# =============================================================================


def is_valid_account_id(value: str) -> bool:
    """계정 ID 유효성 검사 (12자리 숫자)"""
    return len(value) == 12 and value.isdigit()


def is_valid_region(value: str) -> bool:
    """리전 이름 유효성 검사 (기본 패턴)"""
    import re

    pattern = r"^[a-z]{2}(-[a-z]+)+-\d+$"
    return bool(re.match(pattern, value))


def is_valid_arn(value: str) -> bool:
    """ARN 유효성 검사"""
    return value.startswith("arn:aws:") or value.startswith("arn:aws-")
