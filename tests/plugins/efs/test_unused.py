"""
tests/plugins/efs/test_unused.py - EFS 미사용 파일시스템 분석 테스트
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# moto 사용 가능 여부 확인
try:
    import moto

    HAS_MOTO = True
except ImportError:
    HAS_MOTO = False


# =============================================================================
# 테스트 데이터 팩토리
# =============================================================================


def make_efs_info(
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
    file_system_id: str = "fs-12345678",
    name: str = "test-efs",
    size_bytes: int = 1024 * 1024 * 100,  # 100MB
    mount_target_count: int = 1,
    avg_client_connections: float = 1.0,
    metered_io_bytes: float = 1000.0,
):
    """EFSInfo 테스트 데이터 생성"""
    from plugins.efs.unused import EFSInfo

    return EFSInfo(
        account_id=account_id,
        account_name=account_name,
        region=region,
        file_system_id=file_system_id,
        name=name,
        lifecycle_state="available",
        performance_mode="generalPurpose",
        throughput_mode="bursting",
        size_bytes=size_bytes,
        mount_target_count=mount_target_count,
        created_at=datetime.now(timezone.utc),
        avg_client_connections=avg_client_connections,
        metered_io_bytes=metered_io_bytes,
    )


def make_aws_fs_response(
    file_system_id: str = "fs-12345678",
    name: str = "test-efs",
    size_bytes: int = 1024 * 1024 * 100,
):
    """AWS describe_file_systems 응답 데이터 생성"""
    return {
        "FileSystems": [
            {
                "FileSystemId": file_system_id,
                "LifeCycleState": "available",
                "PerformanceMode": "generalPurpose",
                "ThroughputMode": "bursting",
                "SizeInBytes": {"Value": size_bytes},
                "Tags": [{"Key": "Name", "Value": name}],
                "CreationTime": datetime.now(timezone.utc),
            }
        ]
    }


# =============================================================================
# TestCollectEfsFilesystems
# =============================================================================


class TestCollectEfsFilesystems:
    """collect_efs_filesystems() 함수 테스트"""

    def test_collect_normal(self, mock_boto3_session):
        """정상 수집 케이스"""
        from plugins.efs.unused import collect_efs_filesystems

        # Arrange
        mock_efs = MagicMock()
        mock_cloudwatch = MagicMock()

        def get_client_mock(session, service, region_name=None):
            if service == "efs":
                return mock_efs
            return mock_cloudwatch

        # EFS 응답 설정
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [make_aws_fs_response()]
        mock_efs.get_paginator.return_value = mock_paginator
        mock_efs.describe_mount_targets.return_value = {"MountTargets": [{"MountTargetId": "mt-1"}]}

        # CloudWatch 응답 설정
        mock_cloudwatch.get_metric_statistics.return_value = {"Datapoints": [{"Average": 1.0, "Sum": 1000.0}]}

        # Act
        with patch("plugins.efs.unused.get_client", side_effect=get_client_mock):
            result = collect_efs_filesystems(
                mock_boto3_session,
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
            )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].file_system_id == "fs-12345678"
        assert result[0].mount_target_count == 1

    def test_collect_empty(self, mock_boto3_session):
        """빈 결과 케이스"""
        from plugins.efs.unused import collect_efs_filesystems

        mock_efs = MagicMock()
        mock_cloudwatch = MagicMock()

        def get_client_mock(session, service, region_name=None):
            if service == "efs":
                return mock_efs
            return mock_cloudwatch

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"FileSystems": []}]
        mock_efs.get_paginator.return_value = mock_paginator

        with patch("plugins.efs.unused.get_client", side_effect=get_client_mock):
            result = collect_efs_filesystems(
                mock_boto3_session,
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
            )

        assert result == []

    def test_collect_access_denied(self, mock_boto3_session):
        """권한 없음 에러 케이스"""
        from botocore.exceptions import ClientError

        from plugins.efs.unused import collect_efs_filesystems

        mock_efs = MagicMock()

        def get_client_mock(session, service, region_name=None):
            return mock_efs

        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access Denied"}},
            "DescribeFileSystems",
        )
        mock_efs.get_paginator.return_value = mock_paginator

        with patch("plugins.efs.unused.get_client", side_effect=get_client_mock):
            result = collect_efs_filesystems(
                mock_boto3_session,
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
            )

        assert result == []

    def test_collect_with_no_name_tag(self, mock_boto3_session):
        """Name 태그 없는 경우"""
        from plugins.efs.unused import collect_efs_filesystems

        mock_efs = MagicMock()
        mock_cloudwatch = MagicMock()

        def get_client_mock(session, service, region_name=None):
            if service == "efs":
                return mock_efs
            return mock_cloudwatch

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "FileSystems": [
                    {
                        "FileSystemId": "fs-no-name",
                        "LifeCycleState": "available",
                        "PerformanceMode": "generalPurpose",
                        "ThroughputMode": "bursting",
                        "SizeInBytes": {"Value": 1024},
                        "Tags": [],  # Name 태그 없음
                    }
                ]
            }
        ]
        mock_efs.get_paginator.return_value = mock_paginator
        mock_efs.describe_mount_targets.return_value = {"MountTargets": []}
        mock_cloudwatch.get_metric_statistics.return_value = {"Datapoints": []}

        with patch("plugins.efs.unused.get_client", side_effect=get_client_mock):
            result = collect_efs_filesystems(
                mock_boto3_session,
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
            )

        assert len(result) == 1
        assert result[0].name == ""


# =============================================================================
# TestAnalyzeFilesystems
# =============================================================================


class TestAnalyzeFilesystems:
    """analyze_filesystems() 함수 테스트"""

    def test_analyze_normal(self):
        """정상 파일시스템 분석"""
        from plugins.efs.unused import FileSystemStatus, analyze_filesystems

        filesystems = [make_efs_info()]

        result = analyze_filesystems(
            filesystems,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.total_filesystems == 1
        assert result.normal == 1
        assert result.no_mount_target == 0
        assert result.no_io == 0
        assert result.empty == 0
        assert len(result.findings) == 1
        assert result.findings[0].status == FileSystemStatus.NORMAL

    def test_analyze_no_mount_target(self):
        """마운트 타겟 없는 파일시스템"""
        from plugins.efs.unused import FileSystemStatus, analyze_filesystems

        filesystems = [make_efs_info(mount_target_count=0)]

        result = analyze_filesystems(
            filesystems,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.no_mount_target == 1
        assert result.findings[0].status == FileSystemStatus.NO_MOUNT_TARGET
        assert result.unused_monthly_cost > 0

    def test_analyze_no_io(self):
        """I/O 없는 파일시스템"""
        from plugins.efs.unused import FileSystemStatus, analyze_filesystems

        filesystems = [make_efs_info(avg_client_connections=0, metered_io_bytes=0)]

        result = analyze_filesystems(
            filesystems,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.no_io == 1
        assert result.findings[0].status == FileSystemStatus.NO_IO

    def test_analyze_empty_filesystem(self):
        """빈 파일시스템 (1MB 미만)"""
        from plugins.efs.unused import FileSystemStatus, analyze_filesystems

        filesystems = [make_efs_info(size_bytes=512)]  # 512 bytes

        result = analyze_filesystems(
            filesystems,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.empty == 1
        assert result.findings[0].status == FileSystemStatus.EMPTY

    def test_analyze_empty_input(self):
        """빈 입력 케이스"""
        from plugins.efs.unused import analyze_filesystems

        result = analyze_filesystems(
            [],
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.total_filesystems == 0
        assert result.findings == []

    def test_analyze_multiple_filesystems(self):
        """여러 파일시스템 분석"""
        from plugins.efs.unused import analyze_filesystems

        filesystems = [
            make_efs_info(file_system_id="fs-1"),  # normal
            make_efs_info(file_system_id="fs-2", mount_target_count=0),  # no mount
            make_efs_info(file_system_id="fs-3", avg_client_connections=0, metered_io_bytes=0),  # no I/O
        ]

        result = analyze_filesystems(
            filesystems,
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
        )

        assert result.total_filesystems == 3
        assert result.normal == 1
        assert result.no_mount_target == 1
        assert result.no_io == 1


# =============================================================================
# TestEFSInfo
# =============================================================================


class TestEFSInfo:
    """EFSInfo 데이터클래스 테스트"""

    def test_size_gb_property(self):
        """size_gb 프로퍼티 테스트"""
        efs = make_efs_info(size_bytes=1024**3)  # 1GB
        assert efs.size_gb == 1.0

    def test_estimated_monthly_cost(self):
        """월간 비용 추정 테스트"""
        efs = make_efs_info(size_bytes=1024**3)  # 1GB
        # $0.30/GB
        assert efs.estimated_monthly_cost == pytest.approx(0.30, rel=0.01)


# =============================================================================
# TestRun
# =============================================================================


class TestRun:
    """run() 통합 테스트"""

    @patch("plugins.efs.unused.parallel_collect")
    @patch("plugins.efs.unused.generate_report")
    @patch("plugins.efs.unused.open_in_explorer")
    def test_run_success(self, mock_explorer, mock_report, mock_parallel, mock_context):
        """정상 실행"""
        from plugins.efs.unused import EFSAnalysisResult, run

        # Arrange
        mock_result = MagicMock()
        mock_result.get_data.return_value = [
            EFSAnalysisResult(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                total_filesystems=1,
                no_mount_target=1,
                unused_monthly_cost=10.0,
            )
        ]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result
        mock_report.return_value = "/tmp/test_report.xlsx"

        # Act
        run(mock_context)

        # Assert
        mock_parallel.assert_called_once()
        mock_report.assert_called_once()

    @patch("plugins.efs.unused.parallel_collect")
    def test_run_no_results(self, mock_parallel, mock_context):
        """결과 없음"""
        from plugins.efs.unused import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = []
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # Should complete without error
        run(mock_context)

    @patch("plugins.efs.unused.parallel_collect")
    @patch("plugins.efs.unused.generate_report")
    @patch("plugins.efs.unused.open_in_explorer")
    def test_run_with_errors(self, mock_explorer, mock_report, mock_parallel, mock_context):
        """부분 실패"""
        from plugins.efs.unused import EFSAnalysisResult, run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [
            EFSAnalysisResult(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            )
        ]
        mock_result.error_count = 2
        mock_parallel.return_value = mock_result
        mock_report.return_value = "/tmp/test.xlsx"

        # Should complete even with some errors
        run(mock_context)

    @patch("plugins.efs.unused.parallel_collect")
    @patch("plugins.efs.unused.generate_report")
    @patch("plugins.efs.unused.open_in_explorer")
    def test_run_with_sso_context(self, mock_explorer, mock_report, mock_parallel, mock_context):
        """SSO 세션 컨텍스트"""
        from plugins.efs.unused import EFSAnalysisResult, run

        # SSO 세션 설정
        mock_context.is_sso_session = MagicMock(return_value=True)
        mock_context.accounts = [MagicMock(id="111111111111")]

        mock_result = MagicMock()
        mock_result.get_data.return_value = [
            EFSAnalysisResult(
                account_id="111111111111",
                account_name="sso-account",
                region="ap-northeast-2",
            )
        ]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result
        mock_report.return_value = "/tmp/test.xlsx"

        run(mock_context)

        mock_report.assert_called_once()


# =============================================================================
# TestGenerateReport
# =============================================================================


class TestGenerateReport:
    """generate_report() 함수 테스트"""

    def test_generate_report_creates_file(self, tmp_path):
        """보고서 파일 생성 테스트"""
        from plugins.efs.unused import EFSAnalysisResult, EFSFinding, FileSystemStatus, generate_report

        results = [
            EFSAnalysisResult(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                total_filesystems=2,
                no_mount_target=1,
                normal=1,
                findings=[
                    EFSFinding(
                        efs=make_efs_info(mount_target_count=0),
                        status=FileSystemStatus.NO_MOUNT_TARGET,
                        recommendation="삭제 검토",
                    )
                ],
            )
        ]

        filepath = generate_report(results, str(tmp_path))

        assert filepath.endswith(".xlsx")
        import os

        assert os.path.exists(filepath)

    def test_generate_report_empty_results(self, tmp_path):
        """빈 결과 보고서"""
        from plugins.efs.unused import generate_report

        filepath = generate_report([], str(tmp_path))

        assert filepath.endswith(".xlsx")


# =============================================================================
# TestCollectAndAnalyze
# =============================================================================


class TestCollectAndAnalyze:
    """_collect_and_analyze() 병렬 실행 함수 테스트"""

    @patch("plugins.efs.unused.collect_efs_filesystems")
    @patch("plugins.efs.unused.analyze_filesystems")
    def test_collect_and_analyze_success(self, mock_analyze, mock_collect, mock_boto3_session):
        """정상 수집 및 분석"""
        from plugins.efs.unused import EFSAnalysisResult, _collect_and_analyze

        mock_collect.return_value = [make_efs_info()]
        mock_analyze.return_value = EFSAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        result = _collect_and_analyze(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        assert result is not None
        mock_collect.assert_called_once()
        mock_analyze.assert_called_once()

    @patch("plugins.efs.unused.collect_efs_filesystems")
    def test_collect_and_analyze_no_filesystems(self, mock_collect, mock_boto3_session):
        """파일시스템 없음"""
        from plugins.efs.unused import _collect_and_analyze

        mock_collect.return_value = []

        result = _collect_and_analyze(
            mock_boto3_session,
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        assert result is None


# =============================================================================
# moto 기반 통합 테스트 (선택적)
# =============================================================================


@pytest.mark.skipif(not HAS_MOTO, reason="moto not installed")
class TestWithMoto:
    """moto를 사용한 AWS 모킹 테스트

    Note: moto는 EFS를 지원하지만 일부 기능에 제한이 있을 수 있습니다.
    """

    @pytest.fixture
    def aws_credentials(self):
        """AWS 자격 증명 설정"""
        import os

        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"

    @pytest.fixture
    def moto_efs(self, aws_credentials):
        """moto EFS 모킹"""
        with moto.mock_aws():
            import boto3

            efs_client = boto3.client("efs", region_name="ap-northeast-2")
            yield efs_client

    def test_describe_file_systems_with_moto(self, moto_efs):
        """moto로 EFS API 테스트"""
        # EFS 생성
        response = moto_efs.create_file_system(
            CreationToken="test-token",
            PerformanceMode="generalPurpose",
            ThroughputMode="bursting",
            Tags=[{"Key": "Name", "Value": "test-efs"}],
        )

        fs_id = response["FileSystemId"]

        # 조회 확인
        describe_response = moto_efs.describe_file_systems(FileSystemId=fs_id)

        assert len(describe_response["FileSystems"]) == 1
        assert describe_response["FileSystems"][0]["FileSystemId"] == fs_id
