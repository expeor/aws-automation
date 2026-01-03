"""
tests/test_plugins_ecr.py - ECR 플러그인 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from plugins.ecr.unused import (
    ECRAnalysisResult,
    ECRRepoFinding,
    ECRRepoInfo,
    ECRRepoStatus,
    analyze_ecr_repos,
)


class TestECRRepoInfo:
    """ECRRepoInfo 데이터클래스 테스트"""

    def test_total_size_gb(self):
        """총 크기 GB 변환"""
        repo = ECRRepoInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="test-repo",
            arn="arn:aws:ecr:ap-northeast-2:123456789012:repository/test-repo",
            uri="123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/test-repo",
            created_at=datetime.now(timezone.utc),
            total_size_bytes=1024**3,  # 1GB
        )
        assert repo.total_size_gb == 1.0

    def test_old_images_size_gb(self):
        """오래된 이미지 크기 GB 변환"""
        repo = ECRRepoInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="test-repo",
            arn="arn:aws:ecr:ap-northeast-2:123456789012:repository/test-repo",
            uri="123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/test-repo",
            created_at=datetime.now(timezone.utc),
            old_images_size_bytes=2 * 1024**3,  # 2GB
        )
        assert repo.old_images_size_gb == 2.0

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_monthly_cost(self, mock_price):
        """월간 비용 계산"""
        mock_price.return_value = 0.10  # $0.10/GB
        repo = ECRRepoInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="test-repo",
            arn="arn",
            uri="uri",
            created_at=datetime.now(timezone.utc),
            total_size_bytes=10 * 1024**3,  # 10GB
        )
        assert repo.monthly_cost == 1.0  # $1.0

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_old_images_monthly_cost(self, mock_price):
        """오래된 이미지 월간 비용"""
        mock_price.return_value = 0.10
        repo = ECRRepoInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="test-repo",
            arn="arn",
            uri="uri",
            created_at=datetime.now(timezone.utc),
            old_images_size_bytes=5 * 1024**3,  # 5GB
        )
        assert repo.old_images_monthly_cost == 0.5


class TestECRRepoStatus:
    """ECRRepoStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert ECRRepoStatus.NORMAL.value == "normal"
        assert ECRRepoStatus.EMPTY.value == "empty"
        assert ECRRepoStatus.OLD_IMAGES.value == "old_images"
        assert ECRRepoStatus.NO_LIFECYCLE.value == "no_lifecycle"


class TestAnalyzeECRRepos:
    """analyze_ecr_repos 테스트"""

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_empty_repo(self, mock_price):
        """빈 리포지토리 분석"""
        mock_price.return_value = 0.10
        repos = [
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="empty-repo",
                arn="arn",
                uri="uri",
                created_at=datetime.now(timezone.utc),
                image_count=0,
            )
        ]

        result = analyze_ecr_repos(repos, "123456789012", "test", "ap-northeast-2")

        assert result.total_repos == 1
        assert result.empty_repos == 1
        assert len(result.findings) == 1
        assert result.findings[0].status == ECRRepoStatus.EMPTY

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_repo_with_old_images(self, mock_price):
        """오래된 이미지가 있는 리포지토리"""
        mock_price.return_value = 0.10
        repos = [
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="old-images-repo",
                arn="arn",
                uri="uri",
                created_at=datetime.now(timezone.utc),
                image_count=10,
                old_image_count=5,
                old_images_size_bytes=1024**3,
                has_lifecycle_policy=True,
            )
        ]

        result = analyze_ecr_repos(repos, "123456789012", "test", "ap-northeast-2")

        assert result.repos_with_old_images == 1
        assert result.old_images == 5
        assert result.findings[0].status == ECRRepoStatus.OLD_IMAGES

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_repo_without_lifecycle(self, mock_price):
        """라이프사이클 정책 없는 리포지토리"""
        mock_price.return_value = 0.10
        repos = [
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="no-lifecycle-repo",
                arn="arn",
                uri="uri",
                created_at=datetime.now(timezone.utc),
                image_count=5,
                old_image_count=0,
                has_lifecycle_policy=False,
            )
        ]

        result = analyze_ecr_repos(repos, "123456789012", "test", "ap-northeast-2")

        assert result.no_lifecycle_repos == 1
        assert result.findings[0].status == ECRRepoStatus.NO_LIFECYCLE

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_normal_repo(self, mock_price):
        """정상 리포지토리"""
        mock_price.return_value = 0.10
        repos = [
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="normal-repo",
                arn="arn",
                uri="uri",
                created_at=datetime.now(timezone.utc),
                image_count=10,
                old_image_count=0,
                has_lifecycle_policy=True,
            )
        ]

        result = analyze_ecr_repos(repos, "123456789012", "test", "ap-northeast-2")

        assert result.findings[0].status == ECRRepoStatus.NORMAL

    @patch("plugins.ecr.unused.get_ecr_storage_price")
    def test_mixed_repos(self, mock_price):
        """혼합 리포지토리 분석"""
        mock_price.return_value = 0.10
        repos = [
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="empty-repo",
                arn="arn1",
                uri="uri1",
                created_at=datetime.now(timezone.utc),
                image_count=0,
            ),
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="old-repo",
                arn="arn2",
                uri="uri2",
                created_at=datetime.now(timezone.utc),
                image_count=10,
                old_image_count=3,
                old_images_size_bytes=1024**3,
                has_lifecycle_policy=True,
            ),
            ECRRepoInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="normal-repo",
                arn="arn3",
                uri="uri3",
                created_at=datetime.now(timezone.utc),
                image_count=5,
                old_image_count=0,
                has_lifecycle_policy=True,
            ),
        ]

        result = analyze_ecr_repos(repos, "123456789012", "test", "ap-northeast-2")

        assert result.total_repos == 3
        assert result.empty_repos == 1
        assert result.repos_with_old_images == 1


class TestECRAnalysisResult:
    """ECRAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = ECRAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_repos == 0
        assert result.empty_repos == 0
        assert result.repos_with_old_images == 0
        assert result.no_lifecycle_repos == 0
        assert result.total_images == 0
        assert result.old_images == 0
        assert result.total_size_gb == 0.0
        assert result.old_images_size_gb == 0.0
        assert result.old_images_monthly_cost == 0.0
        assert result.findings == []
