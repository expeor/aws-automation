"""
tests/core/region/test_region_availability.py - 리전 가용성 테스트
"""

import time
from unittest.mock import MagicMock, patch

from core.region.availability import (
    DEFAULT_CACHE_TTL,
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


class TestRegionInfoEdgeCases:
    """RegionInfo 경계 조건 테스트"""

    def test_default_endpoint_empty_string(self):
        """기본 엔드포인트는 빈 문자열"""
        info = RegionInfo(region_name="test-region")
        assert info.endpoint == ""

    def test_default_opt_in_status(self):
        """기본 옵트인 상태는 opt-in-not-required"""
        info = RegionInfo(region_name="test-region")
        assert info.opt_in_status == "opt-in-not-required"
        assert info.is_opted_in is True

    def test_all_opt_in_statuses(self):
        """모든 옵트인 상태 테스트"""
        statuses = [
            ("opt-in-not-required", True, False),
            ("opted-in", True, True),
            ("not-opted-in", False, True),
        ]

        for status, should_be_opted_in, should_require_opt_in in statuses:
            info = RegionInfo(region_name="test-region", opt_in_status=status)
            assert info.is_opted_in == should_be_opted_in, f"Failed for status: {status}"
            assert info.requires_opt_in == should_require_opt_in, f"Failed for status: {status}"

    def test_to_dict_complete(self):
        """to_dict가 모든 필드를 포함하는지 확인"""
        info = RegionInfo(
            region_name="ap-northeast-2",
            endpoint="ec2.ap-northeast-2.amazonaws.com",
            opt_in_status="opt-in-not-required",
        )

        d = info.to_dict()

        required_keys = ["region_name", "endpoint", "opt_in_status", "is_opted_in"]
        for key in required_keys:
            assert key in d, f"Missing key in to_dict: {key}"


class TestRegionAvailabilityCheckerEdgeCases:
    """RegionAvailabilityChecker 경계 조건 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_custom_cache_ttl(self):
        """커스텀 캐시 TTL"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session, cache_ttl=120.0)

        assert checker.cache_ttl == 120.0

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_available_regions_empty_list(self, mock_get_all):
        """리전이 없을 때"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = []

        available = checker.get_available_regions()

        assert available == []

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_region_info_not_found(self, mock_get_all):
        """존재하지 않는 리전 조회"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
        ]

        info = checker.get_region_info("invalid-region")

        assert info is None

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_region_info_found(self, mock_get_all):
        """리전 정보 조회 성공"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        expected_info = RegionInfo(
            "ap-northeast-2", endpoint="ec2.ap-northeast-2.amazonaws.com", opt_in_status="opt-in-not-required"
        )
        mock_get_all.return_value = [expected_info]

        info = checker.get_region_info("ap-northeast-2")

        assert info is not None
        assert info.region_name == "ap-northeast-2"
        assert info.endpoint == "ec2.ap-northeast-2.amazonaws.com"

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_filter_available_regions_empty_input(self, mock_get_all):
        """빈 리전 리스트 필터링"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
        ]

        available = checker.filter_available_regions([])

        assert available == []

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_filter_available_regions_all_unavailable(self, mock_get_all):
        """모든 리전이 사용 불가능"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
        ]

        requested = ["me-south-1", "invalid-region"]
        available = checker.filter_available_regions(requested)

        assert available == []

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_unavailable_regions_all_available(self, mock_get_all):
        """모든 리전이 사용 가능"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("ap-northeast-2", opt_in_status="opt-in-not-required"),
        ]

        requested = ["us-east-1", "ap-northeast-2"]
        unavailable = checker.get_unavailable_regions(requested)

        assert unavailable == []

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_unavailable_regions_with_reasons(self, mock_get_all):
        """사용 불가능 리전의 이유 확인"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
        ]

        requested = ["invalid-region", "me-south-1"]
        unavailable = checker.get_unavailable_regions(requested)

        assert len(unavailable) == 2

        # 리전별 이유 확인
        reasons_dict = {r[0]: r[1] for r in unavailable}
        assert "invalid-region" in reasons_dict
        assert "존재하지 않는 리전" in reasons_dict["invalid-region"]
        assert "me-south-1" in reasons_dict
        assert "옵트인 필요" in reasons_dict["me-south-1"]

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_enabled_opt_in_regions(self, mock_get_all):
        """활성화된 옵트인 리전만 조회"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
            RegionInfo("me-south-1", opt_in_status="not-opted-in"),
            RegionInfo("af-south-1", opt_in_status="opted-in"),
            RegionInfo("ap-east-1", opt_in_status="opted-in"),
        ]

        enabled = checker.get_enabled_opt_in_regions()

        assert len(enabled) == 2
        region_names = [r.region_name for r in enabled]
        assert "af-south-1" in region_names
        assert "ap-east-1" in region_names
        assert "me-south-1" not in region_names  # not-opted-in은 제외
        assert "us-east-1" not in region_names  # opt-in-not-required는 제외


class TestRegionAvailabilityCheckerCaching:
    """RegionAvailabilityChecker 캐싱 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_cache_expiration(self):
        """캐시 만료 테스트"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session, cache_ttl=0.1)  # 0.1초 TTL

        # 캐시에 데이터 추가
        checker._set_cached("test_key", "test_value")

        # 즉시 조회하면 캐시된 값
        assert checker._get_cached("test_key") == "test_value"

        # 0.2초 대기 (TTL 초과)
        time.sleep(0.2)

        # 캐시 만료로 None 반환
        assert checker._get_cached("test_key") is None

    def test_cache_multiple_keys(self):
        """여러 키 캐싱"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        # 여러 키 저장
        checker._set_cached("key1", "value1")
        checker._set_cached("key2", "value2")
        checker._set_cached("key3", "value3")

        # 모두 조회 가능
        assert checker._get_cached("key1") == "value1"
        assert checker._get_cached("key2") == "value2"
        assert checker._get_cached("key3") == "value3"

    def test_clear_cache_removes_all(self):
        """캐시 초기화는 모든 키를 제거"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        # 여러 키 저장
        checker._set_cached("key1", "value1")
        checker._set_cached("key2", "value2")

        # 캐시 초기화
        checker.clear_cache()

        # 모든 키가 없어짐
        assert checker._get_cached("key1") is None
        assert checker._get_cached("key2") is None

    @patch.object(RegionAvailabilityChecker, "get_all_regions_info")
    def test_get_available_regions_uses_cache(self, mock_get_all):
        """get_available_regions가 캐시를 사용하는지 확인"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        mock_get_all.return_value = [
            RegionInfo("us-east-1", opt_in_status="opt-in-not-required"),
        ]

        # 첫 호출
        result1 = checker.get_available_regions()

        # 두 번째 호출 (캐시 사용)
        result2 = checker.get_available_regions()

        # 같은 결과
        assert result1 == result2

        # get_all_regions_info는 한 번만 호출됨
        assert mock_get_all.call_count == 1


class TestRegionAvailabilityCheckerWithAWSMocking:
    """실제 AWS API 모킹 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_get_all_regions_info_success(self):
        """describe_regions API 성공"""
        session = MagicMock()
        ec2_client = MagicMock()

        # describe_regions 응답 모킹
        ec2_client.describe_regions.return_value = {
            "Regions": [
                {
                    "RegionName": "us-east-1",
                    "Endpoint": "ec2.us-east-1.amazonaws.com",
                    "OptInStatus": "opt-in-not-required",
                },
                {
                    "RegionName": "me-south-1",
                    "Endpoint": "ec2.me-south-1.amazonaws.com",
                    "OptInStatus": "not-opted-in",
                },
            ]
        }

        session.client.return_value = ec2_client

        checker = RegionAvailabilityChecker(session=session)
        regions = checker.get_all_regions_info()

        assert len(regions) == 2
        assert regions[0].region_name == "us-east-1"
        assert regions[0].endpoint == "ec2.us-east-1.amazonaws.com"
        assert regions[0].opt_in_status == "opt-in-not-required"

        # EC2 클라이언트가 us-east-1로 생성되었는지 확인
        session.client.assert_called_once_with("ec2", region_name="us-east-1")

        # AllRegions=True로 호출되었는지 확인
        ec2_client.describe_regions.assert_called_once_with(AllRegions=True)

    def test_get_all_regions_info_api_failure_fallback(self):
        """API 실패 시 폴백"""
        session = MagicMock()
        ec2_client = MagicMock()

        # API 실패 시뮬레이션
        ec2_client.describe_regions.side_effect = Exception("API Error")
        session.client.return_value = ec2_client

        checker = RegionAvailabilityChecker(session=session)
        regions = checker.get_all_regions_info()

        # 폴백으로 ALL_REGIONS 사용
        assert len(regions) > 0

        # 모든 리전이 RegionInfo 객체인지 확인
        for region in regions:
            assert isinstance(region, RegionInfo)

    def test_get_all_regions_info_uses_cache(self):
        """get_all_regions_info가 캐시를 사용하는지 확인"""
        session = MagicMock()
        ec2_client = MagicMock()

        ec2_client.describe_regions.return_value = {
            "Regions": [
                {
                    "RegionName": "us-east-1",
                    "Endpoint": "ec2.us-east-1.amazonaws.com",
                    "OptInStatus": "opt-in-not-required",
                }
            ]
        }

        session.client.return_value = ec2_client

        checker = RegionAvailabilityChecker(session=session)

        # 첫 호출
        regions1 = checker.get_all_regions_info()

        # 두 번째 호출 (캐시에서)
        regions2 = checker.get_all_regions_info()

        # 같은 결과
        assert regions1 == regions2

        # API는 한 번만 호출됨
        assert ec2_client.describe_regions.call_count == 1


class TestRegionCheckerSingleton:
    """싱글톤 팩토리 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    def test_reset_clears_all_checkers(self):
        """reset이 모든 체커를 제거하는지 확인"""
        session1 = MagicMock()
        session2 = MagicMock()

        checker1 = get_region_checker(session1)
        checker2 = get_region_checker(session2)

        # 리셋
        reset_region_checkers()

        # 새로 생성되는 체커는 이전과 다름
        checker3 = get_region_checker(session1)
        assert checker3 is not checker1

    def test_custom_cache_ttl_preserved(self):
        """커스텀 TTL이 유지되는지 확인"""
        session = MagicMock()

        checker = get_region_checker(session, cache_ttl=300.0)

        assert checker.cache_ttl == 300.0

        # 같은 세션으로 다시 조회하면 같은 인스턴스 (TTL 유지)
        checker2 = get_region_checker(session, cache_ttl=300.0)
        assert checker is checker2


class TestConvenienceFunctionsEdgeCases:
    """편의 함수 경계 조건 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_region_checkers()

    @patch("core.region.availability.RegionAvailabilityChecker.get_available_regions")
    def test_get_available_regions_empty(self, mock_get):
        """빈 리전 목록"""
        session = MagicMock()
        mock_get.return_value = []

        result = get_available_regions(session)

        assert result == []

    @patch("core.region.availability.RegionAvailabilityChecker.filter_available_regions")
    def test_filter_available_regions_empty_input(self, mock_filter):
        """빈 입력 리스트"""
        session = MagicMock()
        mock_filter.return_value = []

        result = filter_available_regions(session, [])

        assert result == []

    @patch("core.region.availability.RegionAvailabilityChecker.filter_available_regions")
    @patch("core.region.availability.RegionAvailabilityChecker.get_unavailable_regions")
    def test_validate_regions_all_valid(self, mock_unavailable, mock_available):
        """모든 리전이 유효"""
        session = MagicMock()
        mock_available.return_value = ["us-east-1", "ap-northeast-2"]
        mock_unavailable.return_value = []

        available, unavailable = validate_regions(session, ["us-east-1", "ap-northeast-2"])

        assert len(available) == 2
        assert len(unavailable) == 0

    @patch("core.region.availability.RegionAvailabilityChecker.filter_available_regions")
    @patch("core.region.availability.RegionAvailabilityChecker.get_unavailable_regions")
    def test_validate_regions_all_invalid(self, mock_unavailable, mock_available):
        """모든 리전이 무효"""
        session = MagicMock()
        mock_available.return_value = []
        mock_unavailable.return_value = [
            ("invalid-1", "존재하지 않는 리전"),
            ("invalid-2", "존재하지 않는 리전"),
        ]

        available, unavailable = validate_regions(session, ["invalid-1", "invalid-2"])

        assert len(available) == 0
        assert len(unavailable) == 2


class TestDefaultCacheTTL:
    """DEFAULT_CACHE_TTL 상수 테스트"""

    def test_default_cache_ttl_value(self):
        """기본 TTL 값 확인"""
        assert DEFAULT_CACHE_TTL == 3600  # 1시간

    def test_default_cache_ttl_used(self):
        """RegionAvailabilityChecker가 기본 TTL을 사용하는지 확인"""
        session = MagicMock()
        checker = RegionAvailabilityChecker(session=session)

        assert checker.cache_ttl == DEFAULT_CACHE_TTL
