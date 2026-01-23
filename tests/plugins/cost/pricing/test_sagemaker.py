"""
tests/plugins/cost/pricing/test_sagemaker.py - SageMaker 가격 조회 테스트
"""

from unittest.mock import patch

import pytest

from plugins.cost.pricing.constants import DEFAULT_PRICES, HOURS_PER_MONTH


class TestSageMakerPricing:
    """SageMaker 가격 조회 테스트"""

    @pytest.fixture
    def mock_pricing_service(self, sample_sagemaker_prices):
        """Mock PricingService"""
        with patch("plugins.cost.pricing.sagemaker.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_sagemaker_prices
            yield mock_service

    def test_get_sagemaker_price(self, mock_pricing_service, sample_sagemaker_prices):
        """SageMaker 인스턴스 가격 조회"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_price

        price = get_sagemaker_price("ml.t3.medium", "ap-northeast-2")

        assert price == sample_sagemaker_prices["ml.t3.medium"]

    def test_get_sagemaker_price_from_defaults(self, mock_pricing_service):
        """API에 없는 경우 기본값에서 조회"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_price

        # mock에서 반환하지 않는 인스턴스 타입
        mock_pricing_service.get_prices.return_value = {}

        # 기본값에 있는 인스턴스 타입
        if "ml.m5.large" in DEFAULT_PRICES.get("sagemaker", {}):
            price = get_sagemaker_price("ml.m5.large", "ap-northeast-2")
            assert price == DEFAULT_PRICES["sagemaker"]["ml.m5.large"]

    def test_get_sagemaker_price_unknown_instance(self, mock_pricing_service):
        """알 수 없는 인스턴스 타입은 기본값 0.50 반환"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_price

        mock_pricing_service.get_prices.return_value = {}

        price = get_sagemaker_price("unknown.instance", "ap-northeast-2")

        assert price == 0.50  # 기본값

    def test_get_sagemaker_monthly_cost(self, mock_pricing_service, sample_sagemaker_prices):
        """SageMaker 월간 비용 계산"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_monthly_cost

        monthly_cost = get_sagemaker_monthly_cost("ml.t3.medium", "ap-northeast-2")

        expected = round(sample_sagemaker_prices["ml.t3.medium"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected

    def test_get_sagemaker_monthly_cost_multiple_instances(self, mock_pricing_service, sample_sagemaker_prices):
        """여러 인스턴스의 SageMaker 월간 비용 계산"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_monthly_cost

        instance_count = 3
        monthly_cost = get_sagemaker_monthly_cost(
            "ml.t3.medium", "ap-northeast-2", instance_count=instance_count
        )

        expected = round(sample_sagemaker_prices["ml.t3.medium"] * HOURS_PER_MONTH * instance_count, 2)
        assert monthly_cost == expected

    def test_get_sagemaker_prices(self, mock_pricing_service, sample_sagemaker_prices):
        """모든 SageMaker 가격 조회"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_prices

        prices = get_sagemaker_prices("ap-northeast-2")

        # 기본값과 병합되므로 sample 가격들을 포함해야 함
        for key, value in sample_sagemaker_prices.items():
            assert key in prices
            assert prices[key] == value

    def test_get_sagemaker_prices_bulk_alias(self):
        """get_sagemaker_prices_bulk가 get_sagemaker_prices의 alias인지 확인"""
        from plugins.cost.pricing.sagemaker import get_sagemaker_prices, get_sagemaker_prices_bulk

        assert get_sagemaker_prices_bulk is get_sagemaker_prices


class TestSageMakerDefaultPrices:
    """SageMaker 기본 가격 테스트"""

    def test_default_prices_exist(self):
        """SageMaker 기본 가격이 존재하는지 확인"""
        assert "sagemaker" in DEFAULT_PRICES
        assert len(DEFAULT_PRICES["sagemaker"]) > 0

    def test_default_prices_include_common_instances(self):
        """일반적인 인스턴스 타입이 기본 가격에 포함되어 있는지 확인"""
        sagemaker_defaults = DEFAULT_PRICES.get("sagemaker", {})
        common_instances = ["ml.t3.medium", "ml.m5.large", "ml.c5.xlarge"]

        for instance in common_instances:
            assert instance in sagemaker_defaults, f"{instance}가 기본값에 없음"

    def test_default_prices_are_positive(self):
        """모든 기본 가격이 양수인지 확인"""
        sagemaker_defaults = DEFAULT_PRICES.get("sagemaker", {})

        for instance_type, price in sagemaker_defaults.items():
            assert price > 0, f"{instance_type} 가격이 0 이하: {price}"
