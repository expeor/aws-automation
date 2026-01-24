"""
tests/core/region/test_region_availability.py - 리전 가용성 테스트
"""

from unittest.mock import MagicMock, patch

from core.region.availability import (
    RegionAvailabilityChecker,
    RegionInfo,
    filter_available_regions,
    get_available_regions,
    get_region_checker,
    reset_region_checkers,
    validate_regions,
)


class TestRegionInfo:
    """RegionInfo 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        info = RegionInfo(
            region_name="ap-northeast-2",
            endpoint="ec2.ap-northeast-2.amazonaws.com",
            opt_in_status="opt-in-not-required",
        )

        assert info.region_name == "ap-northeast-2"
        assert info.is_opted_in is True
        assert info.requires_opt_in is False

    def test_opt_in_required(self):
        """옵트인 필요 리전"""
        info = RegionInfo(
            region_name="me-south-1",
            opt_in_status="not-opted-in",
        )

        assert info.is_opted_in is False
        assert info.requires_opt_in is True

    def test_opted_in(self):
        """옵트인 활성화된 리전"""
        info = RegionInfo(
            region_name="af-south-1",
            opt_in_status="opted-in",
        )

        assert info.is_opted_in is True
        assert info.requires_opt_in is True

    def test_to_dict(self):
        """딕셔너리 변환"""
        info = RegionInfo(
            region_name="ap-northeast-2",
            endpoint="ec2.ap-northeast-2.amazonaws.com",
            opt_in_status="opt-in-not-required",
        )

        d = info.to_dict()

        assert d["region_name"] == "ap-northeast-2"
        assert d["endpoint"] == "ec2.ap-northeast-2.amazonaws.com"
        assert d["opt_in_status"] == "opt-in-not-required"
        assert d["is_opted_in"] is True


class TestRegionAvailabilityChecker:
    """RegionAvailabilityChecker 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_creation(self):
        """생성 테스트"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        assert checker.session == session

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_available_regions(self, mock_get_all):
        """사용 가능한 리전 조회"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("ap-northeast-2", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
            RegionInfo("af-south-1", opt_in_status="opted-in"),
        ]

        available = checker.get_available_regions()

        assert "us-east-1" in available
        assert "ap-northeast-2" in available
        assert "me-south-1" not in available  # 옵트인 안됨
        assert "af-south-1" in available  # 옵트인 완료

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_is_region_available(self, mock_get_all):
        """특정 리전 확인"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
        ]

        assert checker.is_region_available("us-east-1") is True
        assert checker.is_region_available("me-south-1") is False
        assert checker.is_region_available("invalid-region") is False

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_filter_available_regions(self, mock_get_all):
        """리전 필터링"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("ap-northeast-2", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
        ]

        requested = ["us-east-1", "ap-northeast-2", "me-south-1"]
        available = checker.filter_available_regions(requested)

        assert available == ["us-east-1", "ap-northeast-2"]

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_unavailable_regions(self, mock_get_all):
        """사용 불가능한 리전 조회"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
        ]

        requested = ["us-east-1", "me-south-1", "invalid-region"]
        unavailable = checker.get_unavailable_regions(requested)

        assert len(unavailable) == 2
        region_names = [r[0] for r in unavailable]
        assert "me-south-1" in region_names
        assert "invalid-region" in region_names

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_opt_in_regions(self, mock_get_all):
        """옵트인 리전 조회"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
            RegionInfo("af-south-1", opt_in_status="opted-in"),
        ]

        opt_in_regions = checker.get_opt_in_regions()

        assert len(opt_in_regions) == 2
        region_names = [r.region_name for r in opt_in_regions]
        assert "me-south-1" in region_names
        assert "af-south-1" in region_names

    def test_cache(self):
        """캐시 기능"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session, cache_ttl=60.0)

        # 캐시에 데이터 추가
        checker._set_cached("test_key", "test_value")

        # 캐시에서 조회
        assert checker._get_cached("test_key") == "test_value"

        # 캐시 초기화
        checker.clear_cache()
        assert checker._get_cached("test_key") is None


class TestGetRegionChecker:
    """get_region_checker 싱글톤 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_returns_same_instance(self):
        """동일 세션에 대해 같은 인스턴스 반환"""
        session = MagicMock()
        checker1 = get_region_checker(session)
        checker2 = get_region_checker(session)

        assert checker1 is checker2

    def test_different_sessions_different_instances(self):
        """다른 세션은 다른 인스턴스"""
        session1 = MagicMock()
        session2 = MagicMock()
        checker1 = get_region_checker(session1)
        checker2 = get_region_checker(session2)

        assert checker1 is not checker2


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    @patch("core.region.availability.RegionAvailabilityChecker.get_available_regions")
    def test_get_available_regions_func(self, mock_get):
        """get_available_regions 함수"""
        session = MagicMock()
        mock_get.return_value = ["us-east-1", "ap-northeast-2"]

        result = get_available_regions(session)

        assert result == ["us-east-1", "ap-northeast-2"]

    @patch("core.region.availability.RegionAvailabilityChecker.filter_available_regions")
    def test_filter_available_regions_func(self, mock_filter):
        """filter_available_regions 함수"""
        session = MagicMock()
        mock_filter.return_value = ["us-east-1"]

        result = filter_available_regions(session, ["us-east-1", "me-south-1"])

        assert result == ["us-east-1"]

    @patch("core.region.availability.RegionAvailabilityChecker.filter_available_regions")
    @patch("core.region.availability.RegionAvailabilityChecker.get_unavailable_regions")
    def test_validate_regions_func(self, mock_unavailable, mock_available):
        """validate_regions 함수"""
        session = MagicMock()
        mock_available.return_value = ["us-east-1"]
        mock_unavailable.return_value = [("me-south-1", "옵트인 필요")]

        available, unavailable = validate_regions(session, ["us-east-1", "me-south-1"])

        assert available == ["us-east-1"]
        assert len(unavailable) == 1
        assert unavailable[0][0] == "me-south-1"
