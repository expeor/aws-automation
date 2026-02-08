"""
tests/plugins/tag_editor/native_api/test_s3_buckets.py - S3 Buckets Native API 테스트

S3 버킷 태그 수집/적용 테스트
중요: 기존 태그 보존 테스트 포함
"""

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from functions.analyzers.tag_editor.native_api.s3_buckets import (
    _get_bucket_arn,
    _get_bucket_region,
    apply_s3_bucket_tag,
    collect_s3_bucket_tags,
)
from functions.analyzers.tag_editor.types import MAP_TAG_KEY, ResourceTagInfo, TagOperationResult


class TestGetBucketArn:
    """_get_bucket_arn 함수 테스트"""

    def test_generates_correct_arn(self):
        """올바른 ARN 생성"""
        arn = _get_bucket_arn("my-bucket")
        assert arn == "arn:aws:s3:::my-bucket"

    def test_handles_special_chars(self):
        """특수 문자가 포함된 버킷 이름"""
        arn = _get_bucket_arn("my-bucket-123.example.com")
        assert arn == "arn:aws:s3:::my-bucket-123.example.com"


class TestGetBucketRegion:
    """_get_bucket_region 함수 테스트"""

    def test_returns_us_east_1_for_none(self):
        """LocationConstraint가 None이면 us-east-1"""
        mock_client = MagicMock()
        mock_client.get_bucket_location.return_value = {"LocationConstraint": None}

        region = _get_bucket_region(mock_client, "my-bucket")
        assert region == "us-east-1"

    def test_returns_actual_region(self):
        """실제 리전 반환"""
        mock_client = MagicMock()
        mock_client.get_bucket_location.return_value = {"LocationConstraint": "ap-northeast-2"}

        region = _get_bucket_region(mock_client, "my-bucket")
        assert region == "ap-northeast-2"

    def test_handles_error(self):
        """오류 시 None 반환"""
        mock_client = MagicMock()
        mock_client.get_bucket_location.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetBucketLocation",
        )

        region = _get_bucket_region(mock_client, "my-bucket")
        assert region is None


class TestCollectS3BucketTags:
    """collect_s3_bucket_tags 함수 테스트"""

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_collects_buckets_with_tags(self, mock_get_client):
        """태그가 있는 버킷 수집"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket-1"},
                {"Name": "bucket-2"},
            ]
        }

        mock_client.get_bucket_location.side_effect = [
            {"LocationConstraint": "ap-northeast-2"},
            {"LocationConstraint": "ap-northeast-2"},
        ]

        mock_client.get_bucket_tagging.side_effect = [
            {"TagSet": [{"Key": MAP_TAG_KEY, "Value": "mig12345"}, {"Key": "Environment", "Value": "prod"}]},
            {"TagSet": [{"Key": "Environment", "Value": "dev"}]},  # MAP 태그 없음
        ]

        mock_session = MagicMock()
        resources = collect_s3_bucket_tags(
            mock_session, "123456789012", "test-account", "us-east-1", target_region="ap-northeast-2"
        )

        assert len(resources) == 2

        # 첫 번째 버킷: MAP 태그 있음
        assert resources[0].has_map_tag is True
        assert resources[0].map_tag_value == "mig12345"
        assert resources[0].resource_type == "s3:bucket"
        assert resources[0].resource_id == "bucket-1"

        # 두 번째 버킷: MAP 태그 없음
        assert resources[1].has_map_tag is False
        assert resources[1].map_tag_value is None

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_filters_by_target_region(self, mock_get_client):
        """target_region으로 필터링"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket-seoul"},
                {"Name": "bucket-virginia"},
                {"Name": "bucket-tokyo"},
            ]
        }

        mock_client.get_bucket_location.side_effect = [
            {"LocationConstraint": "ap-northeast-2"},  # Seoul
            {"LocationConstraint": None},  # us-east-1 (Virginia)
            {"LocationConstraint": "ap-northeast-1"},  # Tokyo
        ]

        # ap-northeast-2 버킷만 태그 조회됨
        mock_client.get_bucket_tagging.return_value = {"TagSet": []}

        mock_session = MagicMock()
        resources = collect_s3_bucket_tags(
            mock_session, "123456789012", "test-account", "us-east-1", target_region="ap-northeast-2"
        )

        # Seoul 버킷만 반환
        assert len(resources) == 1
        assert resources[0].resource_id == "bucket-seoul"
        assert resources[0].region == "ap-northeast-2"

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_handles_no_tags(self, mock_get_client):
        """태그가 없는 버킷"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.list_buckets.return_value = {"Buckets": [{"Name": "no-tags-bucket"}]}
        mock_client.get_bucket_location.return_value = {"LocationConstraint": "ap-northeast-2"}
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "NoSuchTagSet", "Message": "No tags"}},
            "GetBucketTagging",
        )

        mock_session = MagicMock()
        resources = collect_s3_bucket_tags(
            mock_session, "123456789012", "test-account", "us-east-1", target_region="ap-northeast-2"
        )

        assert len(resources) == 1
        assert resources[0].has_map_tag is False
        assert resources[0].tags == {}

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_handles_access_denied(self, mock_get_client):
        """접근 권한 없는 버킷 스킵"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.list_buckets.return_value = {"Buckets": [{"Name": "private-bucket"}]}
        mock_client.get_bucket_location.return_value = {"LocationConstraint": "ap-northeast-2"}
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetBucketTagging",
        )

        mock_session = MagicMock()
        resources = collect_s3_bucket_tags(
            mock_session, "123456789012", "test-account", "us-east-1", target_region="ap-northeast-2"
        )

        # 접근 불가 버킷은 스킵
        assert len(resources) == 0


class TestApplyS3BucketTag:
    """apply_s3_bucket_tag 함수 테스트"""

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_dry_run_skips_application(self, mock_get_client):
        """Dry-run 모드에서는 실제 적용하지 않음"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={"Environment": "prod"},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=True
        )

        assert result.total_targeted == 1
        assert result.skipped_count == 1
        assert result.success_count == 0
        assert result.operation_logs[0].result == TagOperationResult.SKIPPED
        mock_client.put_bucket_tagging.assert_not_called()

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_preserves_existing_tags(self, mock_get_client):
        """기존 태그 보존 확인 (핵심 테스트!)"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 기존 태그가 있는 버킷
        mock_client.get_bucket_tagging.return_value = {
            "TagSet": [
                {"Key": "Environment", "Value": "production"},
                {"Key": "Owner", "Value": "team-a"},
                {"Key": "CostCenter", "Value": "12345"},
            ]
        }

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={"Environment": "production", "Owner": "team-a", "CostCenter": "12345"},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.success_count == 1

        # put_bucket_tagging 호출 확인
        mock_client.put_bucket_tagging.assert_called_once()
        call_args = mock_client.put_bucket_tagging.call_args

        # 태그 세트에서 기존 태그가 보존되었는지 확인
        tag_set = call_args[1]["Tagging"]["TagSet"]
        tag_dict = {t["Key"]: t["Value"] for t in tag_set}

        # 기존 태그 보존 확인
        assert tag_dict["Environment"] == "production"
        assert tag_dict["Owner"] == "team-a"
        assert tag_dict["CostCenter"] == "12345"
        # MAP 태그 추가 확인
        assert tag_dict[MAP_TAG_KEY] == "mig12345"

        # 총 4개 태그 (기존 3개 + MAP 1개)
        assert len(tag_set) == 4

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_applies_tag_to_bucket_without_tags(self, mock_get_client):
        """태그가 없는 버킷에 태그 적용"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 태그가 없는 버킷
        mock_client.get_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "NoSuchTagSet", "Message": "No tags"}},
            "GetBucketTagging",
        )

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::empty-bucket",
                resource_type="s3:bucket",
                resource_id="empty-bucket",
                name="empty-bucket",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.success_count == 1

        # MAP 태그만 적용되어야 함
        call_args = mock_client.put_bucket_tagging.call_args
        tag_set = call_args[1]["Tagging"]["TagSet"]
        assert len(tag_set) == 1
        assert tag_set[0]["Key"] == MAP_TAG_KEY
        assert tag_set[0]["Value"] == "mig12345"

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_updates_existing_map_tag(self, mock_get_client):
        """기존 MAP 태그 값 업데이트"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 이미 MAP 태그가 있는 버킷
        mock_client.get_bucket_tagging.return_value = {
            "TagSet": [
                {"Key": MAP_TAG_KEY, "Value": "mig11111"},  # 기존 MAP 태그
                {"Key": "Environment", "Value": "prod"},
            ]
        }

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={MAP_TAG_KEY: "mig11111", "Environment": "prod"},
                has_map_tag=True,
                map_tag_value="mig11111",
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig99999", dry_run=False
        )

        assert result.success_count == 1

        # MAP 태그 값이 업데이트되었는지 확인
        call_args = mock_client.put_bucket_tagging.call_args
        tag_set = call_args[1]["Tagging"]["TagSet"]
        tag_dict = {t["Key"]: t["Value"] for t in tag_set}

        assert tag_dict[MAP_TAG_KEY] == "mig99999"  # 새 값
        assert tag_dict["Environment"] == "prod"  # 기존 태그 보존

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_handles_apply_error(self, mock_get_client):
        """태그 적용 오류 처리"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.get_bucket_tagging.return_value = {"TagSet": []}
        mock_client.put_bucket_tagging.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutBucketTagging",
        )

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.failed_count == 1
        assert result.success_count == 0
        assert result.operation_logs[0].result == TagOperationResult.FAILED

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_applies_multiple_buckets(self, mock_get_client):
        """여러 버킷에 태그 적용"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 각 버킷마다 다른 기존 태그
        mock_client.get_bucket_tagging.side_effect = [
            {"TagSet": [{"Key": "Env", "Value": "prod"}]},
            {"TagSet": [{"Key": "Env", "Value": "dev"}]},
            {"TagSet": []},  # 태그 없음
        ]

        resources = [
            ResourceTagInfo(
                resource_arn=f"arn:aws:s3:::bucket-{i}",
                resource_type="s3:bucket",
                resource_id=f"bucket-{i}",
                name=f"bucket-{i}",
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            )
            for i in range(3)
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        assert result.total_targeted == 3
        assert result.success_count == 3
        assert mock_client.put_bucket_tagging.call_count == 3

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_empty_resources(self, mock_get_client):
        """빈 리소스 목록"""
        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session, "123456789012", "test-account", "ap-northeast-2", [], "mig12345", dry_run=False
        )

        assert result.total_targeted == 0
        assert result.success_count == 0
        assert result.failed_count == 0


class TestTagPreservationIntegration:
    """태그 보존 통합 테스트"""

    @patch("functions.analyzers.tag_editor.native_api.s3_buckets.get_client")
    def test_complex_tag_preservation_scenario(self, mock_get_client):
        """복잡한 태그 보존 시나리오

        기존에 많은 태그가 있는 버킷에 MAP 태그를 추가할 때
        모든 기존 태그가 보존되어야 함
        """
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 다양한 기존 태그 (실제 환경 시뮬레이션)
        existing_tags = [
            {"Key": "aws:cloudformation:stack-name", "Value": "my-stack"},
            {"Key": "aws:cloudformation:logical-id", "Value": "MyBucket"},
            {"Key": "Environment", "Value": "production"},
            {"Key": "Project", "Value": "migration-project"},
            {"Key": "CostCenter", "Value": "CC-12345"},
            {"Key": "Owner", "Value": "platform-team"},
            {"Key": "DataClassification", "Value": "internal"},
            {"Key": "Compliance", "Value": "SOC2"},
        ]

        mock_client.get_bucket_tagging.return_value = {"TagSet": existing_tags}

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::enterprise-bucket",
                resource_type="s3:bucket",
                resource_id="enterprise-bucket",
                name="enterprise-bucket",
                account_id="123456789012",
                account_name="enterprise-account",
                region="ap-northeast-2",
                tags={t["Key"]: t["Value"] for t in existing_tags},
                has_map_tag=False,
            )
        ]

        mock_session = MagicMock()
        result = apply_s3_bucket_tag(
            mock_session,
            "123456789012",
            "enterprise-account",
            "ap-northeast-2",
            resources,
            "migABCDE12345",
            dry_run=False,
        )

        assert result.success_count == 1

        # 최종 태그 세트 검증
        call_args = mock_client.put_bucket_tagging.call_args
        final_tag_set = call_args[1]["Tagging"]["TagSet"]
        final_tag_dict = {t["Key"]: t["Value"] for t in final_tag_set}

        # 모든 기존 태그 보존 확인
        for existing_tag in existing_tags:
            assert final_tag_dict[existing_tag["Key"]] == existing_tag["Value"]

        # MAP 태그 추가 확인
        assert final_tag_dict[MAP_TAG_KEY] == "migABCDE12345"

        # 총 태그 수 확인 (기존 8개 + MAP 1개 = 9개)
        assert len(final_tag_set) == 9
