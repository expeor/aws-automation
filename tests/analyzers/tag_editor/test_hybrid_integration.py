"""
tests/plugins/tag_editor/test_hybrid_integration.py - 하이브리드 수집/적용 통합 테스트

Tagging API + Native API 통합 테스트
"""

from unittest.mock import MagicMock, patch

from analyzers.tag_editor.map_apply import apply_map_tag
from analyzers.tag_editor.map_audit import _aggregate_stats, _collect_and_analyze
from analyzers.tag_editor.native_api import NATIVE_API_RESOURCE_TYPES
from analyzers.tag_editor.types import (
    MAP_TAG_KEY,
    MapTagAnalysisResult,
    ResourceTagInfo,
    TagOperationResult,
)


class TestNativeApiResourceTypes:
    """NATIVE_API_RESOURCE_TYPES 상수 테스트"""

    def test_contains_logs_log_group(self):
        """logs:log-group 포함"""
        assert "logs:log-group" in NATIVE_API_RESOURCE_TYPES

    def test_contains_s3_bucket(self):
        """s3:bucket 포함"""
        assert "s3:bucket" in NATIVE_API_RESOURCE_TYPES


class TestAggregateStats:
    """_aggregate_stats 함수 테스트"""

    def test_aggregates_correctly(self):
        """통계 집계 정확성"""
        result = MapTagAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        # 테스트 리소스 추가
        result.resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:ec2:ap-northeast-2:123456789012:instance/i-1",
                resource_type="ec2:instance",
                resource_id="i-1",
                name="instance-1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={MAP_TAG_KEY: "mig12345"},
                has_map_tag=True,
                map_tag_value="mig12345",
            ),
            ResourceTagInfo(
                resource_arn="arn:aws:ec2:ap-northeast-2:123456789012:instance/i-2",
                resource_type="ec2:instance",
                resource_id="i-2",
                name="instance-2",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={MAP_TAG_KEY: "mig12345"},
                has_map_tag=True,
                map_tag_value="mig12345",
            ),
        ]

        _aggregate_stats(result)

        assert result.total_resources == 3
        assert result.tagged_resources == 2
        assert result.untagged_resources == 1
        assert len(result.type_stats) == 2  # ec2:instance, logs:log-group

    def test_empty_resources(self):
        """빈 리소스 목록"""
        result = MapTagAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        result.resources = []

        _aggregate_stats(result)

        assert result.total_resources == 0
        assert result.tagged_resources == 0
        assert result.untagged_resources == 0
        assert len(result.type_stats) == 0


class TestHybridApplyMapTag:
    """apply_map_tag 하이브리드 테스트"""

    @patch("analyzers.tag_editor.map_apply.apply_log_group_tag")
    @patch("analyzers.tag_editor.map_apply.apply_s3_bucket_tag")
    @patch("analyzers.tag_editor.map_apply.get_client")
    def test_routes_to_correct_api(self, mock_get_client, mock_s3_apply, mock_logs_apply):
        """리소스 타입에 따라 올바른 API 라우팅"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.tag_resources.return_value = {"FailedResourcesMap": {}}

        # 각 Native API 결과 모킹
        from analyzers.tag_editor.types import MapTagApplyResult

        mock_logs_apply.return_value = MapTagApplyResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            tag_value="mig12345",
            total_targeted=1,
            success_count=1,
        )
        mock_s3_apply.return_value = MapTagApplyResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            tag_value="mig12345",
            total_targeted=1,
            success_count=1,
        )

        # 다양한 타입의 리소스
        resources = [
            # Tagging API 대상
            ResourceTagInfo(
                resource_arn="arn:aws:ec2:ap-northeast-2:123456789012:instance/i-1",
                resource_type="ec2:instance",
                resource_id="i-1",
                name="instance-1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
            # CloudWatch Logs (Native API)
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
            # S3 (Native API)
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
        ]

        mock_session = MagicMock()
        result = apply_map_tag(
            mock_session, "123456789012", "test", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        # 각 API가 호출되었는지 확인
        mock_client.tag_resources.assert_called_once()  # EC2용 Tagging API
        mock_logs_apply.assert_called_once()  # CloudWatch Logs
        mock_s3_apply.assert_called_once()  # S3

        # EC2는 Tagging API로 처리
        call_args = mock_client.tag_resources.call_args
        arns = call_args[1]["ResourceARNList"]
        assert len(arns) == 1
        assert "arn:aws:ec2" in arns[0] and "instance" in arns[0]

    @patch("analyzers.tag_editor.map_apply.apply_log_group_tag")
    @patch("analyzers.tag_editor.map_apply.apply_s3_bucket_tag")
    @patch("analyzers.tag_editor.map_apply.get_client")
    def test_dry_run_all_apis(self, mock_get_client, mock_s3_apply, mock_logs_apply):
        """Dry-run 모드에서 모든 API가 dry-run으로 호출"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from analyzers.tag_editor.types import MapTagApplyResult

        mock_logs_apply.return_value = MapTagApplyResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            tag_value="mig12345",
            total_targeted=1,
            skipped_count=1,
        )
        mock_s3_apply.return_value = MapTagApplyResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            tag_value="mig12345",
            total_targeted=1,
            skipped_count=1,
        )

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
        ]

        mock_session = MagicMock()
        result = apply_map_tag(
            mock_session, "123456789012", "test", "ap-northeast-2", resources, "mig12345", dry_run=True
        )

        # dry_run=True로 호출되었는지 확인
        mock_logs_apply.assert_called_once()
        call_kwargs = mock_logs_apply.call_args[1] if mock_logs_apply.call_args[1] else {}
        # dry_run이 positional arg로 전달된 경우도 확인
        call_args = mock_logs_apply.call_args[0]
        # dry_run은 7번째 인자
        assert call_args[6] is True  # dry_run=True

    @patch("analyzers.tag_editor.map_apply.apply_log_group_tag")
    @patch("analyzers.tag_editor.map_apply.apply_s3_bucket_tag")
    @patch("analyzers.tag_editor.map_apply.get_client")
    def test_handles_native_api_error(self, mock_get_client, mock_s3_apply, mock_logs_apply):
        """Native API 오류 처리"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.tag_resources.return_value = {"FailedResourcesMap": {}}

        # CloudWatch Logs에서 예외 발생
        mock_logs_apply.side_effect = Exception("CloudWatch Logs API Error")

        from analyzers.tag_editor.types import MapTagApplyResult

        mock_s3_apply.return_value = MapTagApplyResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            tag_value="mig12345",
            total_targeted=1,
            success_count=1,
        )

        resources = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/aws/lambda/func1",
                resource_type="logs:log-group",
                resource_id="/aws/lambda/func1",
                name="/aws/lambda/func1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
            ResourceTagInfo(
                resource_arn="arn:aws:s3:::my-bucket",
                resource_type="s3:bucket",
                resource_id="my-bucket",
                name="my-bucket",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={},
                has_map_tag=False,
            ),
        ]

        mock_session = MagicMock()
        result = apply_map_tag(
            mock_session, "123456789012", "test", "ap-northeast-2", resources, "mig12345", dry_run=False
        )

        # CloudWatch Logs 실패, S3 성공
        assert result.failed_count == 1  # logs
        assert result.success_count == 1  # s3

        # 실패 로그 확인
        failed_logs = [log for log in result.operation_logs if log.result == TagOperationResult.FAILED]
        assert len(failed_logs) == 1
        assert "logs:log-group" in failed_logs[0].resource_type


class TestHybridCollect:
    """_collect_and_analyze 하이브리드 수집 테스트"""

    @patch("analyzers.tag_editor.map_audit.collect_s3_bucket_tags")
    @patch("analyzers.tag_editor.map_audit.collect_log_group_tags")
    @patch("analyzers.tag_editor.map_audit.collect_resources_with_tags")
    def test_removes_native_api_resources_from_tagging_api(
        self, mock_tagging_collect, mock_logs_collect, mock_s3_collect
    ):
        """Tagging API 결과에서 Native API 리소스 제거"""
        # Tagging API 결과 (logs:log-group 포함)
        mock_tagging_collect.return_value = MapTagAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            resources=[
                ResourceTagInfo(
                    resource_arn="arn:aws:ec2:ap-northeast-2:123456789012:instance/i-1",
                    resource_type="ec2:instance",
                    resource_id="i-1",
                    name="instance-1",
                    account_id="123456789012",
                    account_name="test",
                    region="ap-northeast-2",
                    tags={},
                    has_map_tag=False,
                ),
                # Tagging API가 반환한 logs:log-group (제거되어야 함)
                ResourceTagInfo(
                    resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/old",
                    resource_type="logs:log-group",
                    resource_id="/old",
                    name="/old",
                    account_id="123456789012",
                    account_name="test",
                    region="ap-northeast-2",
                    tags={},
                    has_map_tag=False,
                ),
            ],
        )

        # Native API 결과
        mock_logs_collect.return_value = [
            ResourceTagInfo(
                resource_arn="arn:aws:logs:ap-northeast-2:123456789012:log-group:/new",
                resource_type="logs:log-group",
                resource_id="/new",
                name="/new",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                tags={MAP_TAG_KEY: "mig12345"},
                has_map_tag=True,
                map_tag_value="mig12345",
            ),
        ]

        mock_s3_collect.return_value = []

        mock_session = MagicMock()
        result = _collect_and_analyze(mock_session, "123456789012", "test", "ap-northeast-2")

        # 최종 결과에는 EC2 + Native API logs만 있어야 함
        assert len(result.resources) == 2

        resource_types = [r.resource_type for r in result.resources]
        assert "ec2:instance" in resource_types
        assert "logs:log-group" in resource_types

        # logs:log-group은 Native API 결과 (/new)만 있어야 함
        log_resources = [r for r in result.resources if r.resource_type == "logs:log-group"]
        assert len(log_resources) == 1
        assert log_resources[0].resource_id == "/new"

    @patch("analyzers.tag_editor.map_audit.collect_s3_bucket_tags")
    @patch("analyzers.tag_editor.map_audit.collect_log_group_tags")
    @patch("analyzers.tag_editor.map_audit.collect_resources_with_tags")
    def test_handles_native_api_collection_error(self, mock_tagging_collect, mock_logs_collect, mock_s3_collect):
        """Native API 수집 오류 시에도 Tagging API 결과 유지"""
        mock_tagging_collect.return_value = MapTagAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            resources=[
                ResourceTagInfo(
                    resource_arn="arn:aws:ec2:ap-northeast-2:123456789012:instance/i-1",
                    resource_type="ec2:instance",
                    resource_id="i-1",
                    name="instance-1",
                    account_id="123456789012",
                    account_name="test",
                    region="ap-northeast-2",
                    tags={},
                    has_map_tag=False,
                ),
            ],
        )

        # Native API 예외 발생
        mock_logs_collect.side_effect = Exception("Logs API Error")
        mock_s3_collect.side_effect = Exception("S3 API Error")

        mock_session = MagicMock()
        result = _collect_and_analyze(mock_session, "123456789012", "test", "ap-northeast-2")

        # EC2 리소스는 여전히 반환됨
        assert len(result.resources) == 1
        assert result.resources[0].resource_type == "ec2:instance"
