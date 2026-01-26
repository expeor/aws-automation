"""
plugins/resource_explorer/common/services/helpers.py - 공통 헬퍼 함수

태그 파싱, 이름 추출 등 공통 유틸리티.
"""

from __future__ import annotations


def parse_tags(tags: list | None, exclude_aws: bool = True) -> dict[str, str]:
    """
    태그 리스트를 dict로 변환.

    Args:
        tags: AWS 태그 리스트 [{"Key": "Name", "Value": "my-resource"}, ...]
        exclude_aws: True면 aws: 접두어 태그 제외 (기본값: True)

    Returns:
        {"Name": "my-resource", ...}
    """
    if not tags:
        return {}

    result = {}
    for tag in tags:
        key = tag.get("Key", "")
        value = tag.get("Value", "")

        # aws: 접두어 태그 제외 (AWS 내부 사용)
        if exclude_aws and key.startswith("aws:"):
            continue

        result[key] = value

    return result


def get_name_from_tags(tags: dict[str, str]) -> str:
    """
    태그 dict에서 Name 값 추출.

    Args:
        tags: 태그 dict {"Name": "my-resource", ...}

    Returns:
        Name 태그 값 또는 빈 문자열
    """
    return tags.get("Name", "")


def get_tag_value(tags: list | None, key: str) -> str:
    """
    태그 리스트에서 특정 키 값 추출.

    Args:
        tags: AWS 태그 리스트 [{"Key": "Name", "Value": "my-resource"}, ...]
        key: 찾을 태그 키

    Returns:
        태그 값 또는 빈 문자열
    """
    if not tags:
        return ""
    for tag in tags:
        if tag.get("Key") == key:
            value = tag.get("Value", "")
            return str(value) if value else ""
    return ""


def has_public_access_rule(ip_permissions: list) -> bool:
    """
    Security Group 규칙에서 0.0.0.0/0 또는 ::/0 허용 여부 확인.

    Args:
        ip_permissions: IpPermissions 또는 IpPermissionsEgress 리스트

    Returns:
        True면 공개 접근 규칙 존재
    """
    for rule in ip_permissions:
        # IPv4
        for ip_range in rule.get("IpRanges", []):
            if ip_range.get("CidrIp") == "0.0.0.0/0":
                return True
        # IPv6
        for ip_range in rule.get("Ipv6Ranges", []):
            if ip_range.get("CidrIpv6") == "::/0":
                return True
    return False


def count_rules(ip_permissions: list) -> int:
    """
    Security Group 규칙 수 계산.

    Args:
        ip_permissions: IpPermissions 리스트

    Returns:
        총 규칙 수
    """
    count = 0
    for rule in ip_permissions:
        # IP 범위 수 + 보안 그룹 참조 수 + Prefix List 수
        count += len(rule.get("IpRanges", []))
        count += len(rule.get("Ipv6Ranges", []))
        count += len(rule.get("UserIdGroupPairs", []))
        count += len(rule.get("PrefixListIds", []))
    return count
