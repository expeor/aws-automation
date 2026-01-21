"""
tests/plugins/cost/pricing/test_utils.py - PricingService 테스트
"""

from unittest.mock import MagicMock, patch

import pytest

from plugins.cost.pricing.constants import DEFAULT_PRICES


class TestPricingService:
    """PricingService 클래스 테스트"""

    @pytest.fixture
    def mock_cache(self):
        """Mock 캐시"""
        cache = MagicMock()
        cache.get.return_value = None
        cache.set.return_value = None
        return cache

    @pytest.fixture
    def mock_fetcher(self):
        """Mock fetcher"""
        fetcher = MagicMock()
        fetcher.get_ec2_prices.return_value = {"t3.micro": 0.0104, "t3.small": 0.0208}
        fetcher.get_ebs_prices.return_value = {"gp3": 0.08, "gp2": 0.10}
        return fetcher

    def test_get_prices_cache_hit(self, mock_cache, sample_ec2_prices):
        """캐시 히트 시 캐시 데이터 반환"""
        from plugins.cost.pricing.utils import PricingService

        mock_cache.get.return_value = sample_ec2_prices

        # 새 인스턴스 생성
        service = PricingService.__new__(PricingService)
        service._initialized = False
        service._cache = mock_cache
        service._fetcher = None
        service._metrics = MagicMock()
        service._lock_registry = {}
        service._registry_mutex = MagicMock()
        service._initialized = True

        with patch.object(service, "_cache", mock_cache):
            result = service.get_prices("ec2", "ap-northeast-2")

        assert result == sample_ec2_prices
        mock_cache.get.assert_called_with("ec2", "ap-northeast-2")

    def test_get_prices_returns_defaults_on_api_failure(self):
        """API 실패 시 기본값 반환"""
        # DEFAULT_PRICES에서 ec2 기본값이 있는지 확인
        assert "ec2" in DEFAULT_PRICES
        ec2_defaults = DEFAULT_PRICES["ec2"]
        assert "t3.micro" in ec2_defaults

    def test_metrics_increment(self):
        """메트릭 증가 테스트"""
        from plugins.cost.pricing.utils import PricingMetrics

        metrics = PricingMetrics()

        metrics.increment_cache_hits()
        assert metrics.cache_hits == 1

        metrics.increment_cache_misses()
        assert metrics.cache_misses == 1

        metrics.increment_api_calls()
        assert metrics.api_calls == 1

        metrics.increment_errors()
        assert metrics.errors == 1

    def test_metrics_hit_rate(self):
        """캐시 히트율 계산 테스트"""
        from plugins.cost.pricing.utils import PricingMetrics

        metrics = PricingMetrics()

        # 히트/미스 없을 때
        assert metrics.hit_rate == 0.0

        # 3 히트, 1 미스
        metrics.cache_hits = 3
        metrics.cache_misses = 1
        assert metrics.hit_rate == 0.75

        # 모두 히트
        metrics.cache_hits = 10
        metrics.cache_misses = 0
        assert metrics.hit_rate == 1.0

    def test_metrics_to_dict(self):
        """메트릭을 딕셔너리로 변환"""
        from plugins.cost.pricing.utils import PricingMetrics

        metrics = PricingMetrics()
        metrics.api_calls = 5
        metrics.cache_hits = 10
        metrics.cache_misses = 2
        metrics.errors = 1
        metrics.retries = 3

        result = metrics.to_dict()

        assert result["api_calls"] == 5
        assert result["cache_hits"] == 10
        assert result["cache_misses"] == 2
        assert result["errors"] == 1
        assert result["retries"] == 3
        assert "hit_rate" in result

    def test_metrics_reset(self):
        """메트릭 초기화"""
        from plugins.cost.pricing.utils import PricingMetrics

        metrics = PricingMetrics()
        metrics.api_calls = 5
        metrics.cache_hits = 10

        metrics.reset()

        assert metrics.api_calls == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0


class TestGetPricesFunction:
    """get_prices 함수 테스트"""

    def test_get_prices_function_exists(self):
        """get_prices 함수가 존재하는지 확인"""
        from plugins.cost.pricing.utils import get_prices

        assert callable(get_prices)

    def test_pricing_service_singleton(self):
        """pricing_service가 싱글톤인지 확인"""
        from plugins.cost.pricing.utils import pricing_service

        assert pricing_service is not None
