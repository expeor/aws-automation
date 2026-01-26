"""
tests/plugins/tag_editor/native_api/test_cloudwatch_logs.py - CloudWatch Logs Native API 테스트

CloudWatch Logs 태그 수집/적용 테스트
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from plugins.tag_editor.native_api.cloudwatch_logs import (
    _get_log_group_arn,
    apply_log_group_tag,
    collect_log_group_tags,
)
from plugins.tag_editor.types import MAP_TAG_KEY, ResourceTagInfo, TagOperationResult


class TestGetLogGroupArn:
    """_get_log_group_arn 함수 테스트"""

    def test_generates_correct_arn(self):
        """올바른 ARN 생성"""
        arn = _get_log_group_arn("123456789012", "ap-northeast-2", "/aws/lambda/my-function")
        assert arn == "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/my-function"

    def test_handles_simple_name(self):
        """단순한 로그 그룹 이름"""
        arn = _get_log_group_arn("111111111111", "us-east-1", "my-log-group")
        assert arn == "arn:aws:logs:us-east-1:111111111111:log-group:my-log-group"


class TestCollectLogGroupTags:
    """collect_log_group_tags 함수 테스트"""

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_collects_log_groups_with_tags(self, mock_get_client):
        """태그가 있는 로그 그룹 수집"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 페이지네이터 모킹
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/func1",
                        "arn": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                    },
                    {
                        "logGroupName": "/aws/lambda/func2",
                        "arn": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func2:*",
                    },
                ]
            }
        ]

        # list_tags_for_resource 모킹
        mock_client.list_tags_for_resource.side_effect = [
            {"tags": {MAP_TAG_KEY: "mig12345", "Environment": "prod"}},
            {"tags": {"Environment": "dev"}},  # MAP 태그 없음
        ]

        mock_session = MagicMock()
        resources = collect_log_group_tags(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(resources) == 2

        # 첫 번째 리소스: MAP 태그 있음
        assert resources[0].has_map_tag is True
        assert resources[0].map_tag_value == "mig12345"
        assert resources[0].resource_type == "logs:log-group"
        assert resources[0].resource_id == "/aws/lambda/func1"

        # 두 번째 리소스: MAP 태그 없음
        assert resources[1].has_map_tag is False
        assert resources[1].map_tag_value is None

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_handles_no_tags(self, mock_get_client):
        """태그가 없는 로그 그룹"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/no-tags",
                        "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/no-tags",
                    }
                ]
            }
        ]

        mock_client.list_tags_for_resource.return_value = {"tags": {}}

        mock_session = MagicMock()
        resources = collect_log_group_tags(mock_session, "123456789012", "test-account", "us-east-1")

        assert len(resources) == 1
        assert resources[0].has_map_tag is False
        assert resources[0].tags == {}

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_handles_api_error(self, mock_get_client):
        """API 오류 처리"""
        mock_get_client.side_effect = Exception("API 접근 오류")

        mock_session = MagicMock()
        resources = collect_log_group_tags(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert resources == []

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_handles_tag_query_error(self, mock_get_client):
        """태그 조회 오류 처리"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/func1",
                        "arn": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                    }
                ]
            }
        ]

        # 태그 조회 실패
        mock_client.list_tags_for_resource.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "ListTagsForResource",
        )

        mock_session = MagicMock()
        resources = collect_log_group_tags(mock_session, "123456789012", "test-account", "ap-northeast-2")

        # 태그 조회 실패 시 해당 리소스는 스킵
        assert len(resources) == 0

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_strips_wildcard_from_arn(self, mock_get_client):
        """ARN에서 :* 제거"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "logGroups": [
                    {
                        "logGroupName": "/aws/lambda/func",
                        "arn": "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func:*",
                    }
                ]
            }
        ]

        mock_client.list_tags_for_resource.return_value = {"tags": {}}

        mock_session = MagicMock()
        resources = collect_log_group_tags(mock_session, "123456789012", "test-account", "ap-northeast-2")

        # :* 가 제거된 ARN 확인
        assert resources[0].resource_arn == "arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func"


class TestApplyLogGroupTag:
    """apply_log_group_tag 함수 테스트"""

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_dry_run_skips_application(self, mock_get_client):
        """Dry-run 모드에서는 실제 적용하지 않음"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=True
        )

        assert result.total_targeted == 1
        assert result.skipped_count == 1
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.operation_logs[0].result == TagOperationResult.SKIPPED
        mock_client.tag_resource.assert_not_called()

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_applies_tag_successfully(self, mock_get_client):
        """태그 적용 성공"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.total_targeted == 1
        assert result.success_count == 1
        assert result.failed_count == 0
        assert result.operation_logs[0].result == TagOperationResult.SUCCESS

        mock_client.tag_resource.assert_called_once_with(
            resourceArn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
            tags={MAP_TAG_KEY: "mig12345"},
        )

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_handles_apply_error(self, mock_get_client):
        """태그 적용 오류 처리"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.tag_resource.side_effect = Exception("Permission denied")

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.failed_count == 1
        assert result.success_count == 0
        assert result.operation_logs[0].result == TagOperationResult.FAILED
        assert "Permission denied" in result.operation_logs[0].error_message

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_applies_multiple_resources(self, mock_get_client):
        """여러 리소스에 태그 적용"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        resources = [
            ResourceTagInfo(
                resource_arn=f"arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func{i}",
                resource_type="logs:log-group",
                resource_id=f"/aws/lambda/func{i}",
                name=f"/aws/lambda/func{i}",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
            for i in range(3)
        ]

        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.total_targeted == 3
        assert result.success_count == 3
        assert mock_client.tag_resource.call_count == 3

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_handles_api_access_error(self, mock_get_client):
        """API 접근 오류 처리"""
        mock_get_client.side_effect = Exception("API 접근 오류")

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.failed_count == 1
        assert result.operation_logs[0].result == TagOperationResult.FAILED

    @patch("plugins.tag_editor.native_api.cloudwatch_logs.get_client")
    def test_empty_resources(self, mock_get_client):
        """빈 리소스 목록"""
        mock_session = MagicMock()
        result = apply_log_group_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", [], "mig12345", dry_run=False
        )

        assert result.total_targeted == 0
        assert result.success_count == 0
        assert result.failed_count == 0
