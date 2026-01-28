"""
tests/shared/aws/inventory/test_helpers.py - Inventory 헬퍼 함수 테스트
"""

import pytest

from shared.aws.inventory.services.helpers import (
    count_rules,
    get_name_from_tags,
    get_tag_value,
    has_public_access_rule,
    parse_tags,
)


class TestParseTags:
    """parse_tags 함수 테스트"""

    def test_empty_tags(self):
        """빈 태그 리스트"""
        assert parse_tags(None) == {}
        assert parse_tags([]) == {}

    def test_simple_tags(self):
        """기본 태그 변환"""
        tags = [
            {"Key": "Name", "Value": "my-resource"},
            {"Key": "Environment", "Value": "production"},
        ]
        result = parse_tags(tags)

        assert result == {"Name": "my-resource", "Environment": "production"}

    def test_excludes_aws_prefix_by_default(self):
        """aws: 접두어 태그 제외 (기본값)"""
        tags = [
            {"Key": "Name", "Value": "my-resource"},
            {"Key": "aws:cloudformation:stack-name", "Value": "my-stack"},
            {"Key": "aws:autoscaling:groupName", "Value": "my-asg"},
        ]
        result = parse_tags(tags)

        assert result == {"Name": "my-resource"}
        assert "aws:cloudformation:stack-name" not in result
        assert "aws:autoscaling:groupName" not in result

    def test_includes_aws_prefix_when_disabled(self):
        """aws: 접두어 태그 포함 옵션"""
        tags = [
            {"Key": "Name", "Value": "my-resource"},
            {"Key": "aws:cloudformation:stack-name", "Value": "my-stack"},
        ]
        result = parse_tags(tags, exclude_aws=False)

        assert result == {"Name": "my-resource", "aws:cloudformation:stack-name": "my-stack"}

    def test_handles_missing_key_or_value(self):
        """Key/Value 누락 처리"""
        tags = [
            {"Key": "Name"},
            {"Value": "some-value"},
            {"Key": "", "Value": "empty-key"},
        ]
        result = parse_tags(tags)

        assert "Name" in result
        assert result["Name"] == ""


class TestGetNameFromTags:
    """get_name_from_tags 함수 테스트"""

    def test_returns_name(self):
        """Name 태그 반환"""
        tags = {"Name": "my-resource", "Environment": "prod"}
        assert get_name_from_tags(tags) == "my-resource"

    def test_returns_empty_when_no_name(self):
        """Name 태그 없으면 빈 문자열"""
        tags = {"Environment": "prod"}
        assert get_name_from_tags(tags) == ""

    def test_returns_empty_for_empty_dict(self):
        """빈 dict에서 빈 문자열"""
        assert get_name_from_tags({}) == ""


class TestGetTagValue:
    """get_tag_value 함수 테스트"""

    def test_returns_value(self):
        """태그 값 반환"""
        tags = [
            {"Key": "Name", "Value": "my-resource"},
            {"Key": "Environment", "Value": "production"},
        ]
        assert get_tag_value(tags, "Name") == "my-resource"
        assert get_tag_value(tags, "Environment") == "production"

    def test_returns_empty_when_key_not_found(self):
        """키가 없으면 빈 문자열"""
        tags = [{"Key": "Name", "Value": "my-resource"}]
        assert get_tag_value(tags, "NonExistent") == ""

    def test_returns_empty_for_none(self):
        """None 입력 시 빈 문자열"""
        assert get_tag_value(None, "Name") == ""

    def test_returns_empty_for_empty_list(self):
        """빈 리스트 시 빈 문자열"""
        assert get_tag_value([], "Name") == ""


class TestHasPublicAccessRule:
    """has_public_access_rule 함수 테스트"""

    def test_detects_ipv4_public_access(self):
        """IPv4 0.0.0.0/0 탐지"""
        rules = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ]
        assert has_public_access_rule(rules) is True

    def test_detects_ipv6_public_access(self):
        """IPv6 ::/0 탐지"""
        rules = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
            }
        ]
        assert has_public_access_rule(rules) is True

    def test_no_public_access(self):
        """공개 접근 없음"""
        rules = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
            }
        ]
        assert has_public_access_rule(rules) is False

    def test_empty_rules(self):
        """빈 규칙 리스트"""
        assert has_public_access_rule([]) is False

    def test_multiple_rules_with_one_public(self):
        """여러 규칙 중 하나가 공개"""
        rules = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
        ]
        assert has_public_access_rule(rules) is True


class TestCountRules:
    """count_rules 함수 테스트"""

    def test_empty_rules(self):
        """빈 규칙"""
        assert count_rules([]) == 0

    def test_counts_ip_ranges(self):
        """IP 범위 카운트"""
        rules = [
            {
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}, {"CidrIp": "192.168.0.0/16"}],
            }
        ]
        assert count_rules(rules) == 2

    def test_counts_ipv6_ranges(self):
        """IPv6 범위 카운트"""
        rules = [
            {
                "IpProtocol": "tcp",
                "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
            }
        ]
        assert count_rules(rules) == 1

    def test_counts_security_group_refs(self):
        """보안 그룹 참조 카운트"""
        rules = [
            {
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [
                    {"GroupId": "sg-12345678"},
                    {"GroupId": "sg-87654321"},
                ],
            }
        ]
        assert count_rules(rules) == 2

    def test_counts_prefix_lists(self):
        """Prefix List 카운트"""
        rules = [
            {
                "IpProtocol": "tcp",
                "PrefixListIds": [{"PrefixListId": "pl-12345678"}],
            }
        ]
        assert count_rules(rules) == 1

    def test_counts_all_types(self):
        """모든 타입 종합 카운트"""
        rules = [
            {
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
                "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
                "UserIdGroupPairs": [{"GroupId": "sg-12345678"}],
                "PrefixListIds": [{"PrefixListId": "pl-12345678"}],
            },
            {
                "IpProtocol": "udp",
                "IpRanges": [{"CidrIp": "192.168.0.0/16"}],
            },
        ]
        # 첫 번째 규칙: 1 + 1 + 1 + 1 = 4
        # 두 번째 규칙: 1
        assert count_rules(rules) == 5
