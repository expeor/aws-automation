"""
tests/plugins/cost/pricing/test_ec2.py - EC2 가격 조회 테스트
"""

from unittest.mock import patch

import pytest

from core.shared.aws.pricing.constants import HOURS_PER_MONTH


class TestEC2Pricing:
    """EC2 가격 조회 테스트"""

    @pytest.fixture
    def mock_pricing_service(self, sample_ec2_prices):
        """Mock PricingService"""
        with patch("core.shared.aws.pricing.ec2.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_ec2_prices
            yield mock_service

    def test_get_ec2_price(self, mock_pricing_service, sample_ec2_prices):
        """EC2 인스턴스 가격 조회"""
        from core.shared.aws.pricing.ec2 import get_ec2_price

        price = get_ec2_price("t3.micro", "ap-northeast-2")

        assert price == sample_ec2_prices["t3.micro"]
        mock_pricing_service.get_prices.assert_called_with("ec2", "ap-northeast-2", False)

    def test_get_ec2_price_unknown_instance(self, mock_pricing_service):
        """알 수 없는 인스턴스 타입 가격 조회"""
        from core.shared.aws.pricing.ec2 import get_ec2_price

        price = get_ec2_price("unknown.instance", "ap-northeast-2")

        assert price == 0.0

    def test_get_ec2_monthly_cost(self, mock_pricing_service, sample_ec2_prices):
        """EC2 월간 비용 계산"""
        from core.shared.aws.pricing.ec2 import get_ec2_monthly_cost

        monthly_cost = get_ec2_monthly_cost("t3.micro", "ap-northeast-2")

        expected = round(sample_ec2_prices["t3.micro"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected

    def test_get_ec2_monthly_cost_custom_hours(self, mock_pricing_service, sample_ec2_prices):
        """커스텀 시간으로 EC2 월간 비용 계산"""
        from core.shared.aws.pricing.ec2 import get_ec2_monthly_cost

        custom_hours = 168  # 1주일
        monthly_cost = get_ec2_monthly_cost("t3.micro", "ap-northeast-2", hours_per_month=custom_hours)

        expected = round(sample_ec2_prices["t3.micro"] * custom_hours, 2)
        assert monthly_cost == expected

    def test_get_ec2_prices(self, mock_pricing_service, sample_ec2_prices):
        """모든 EC2 가격 조회"""
        from core.shared.aws.pricing.ec2 import get_ec2_prices

        prices = get_ec2_prices("ap-northeast-2")

        assert prices == sample_ec2_prices

    def test_get_ec2_prices_bulk_alias(self, mock_pricing_service, sample_ec2_prices):
        """get_ec2_prices_bulk가 get_ec2_prices의 alias인지 확인"""
        from core.shared.aws.pricing.ec2 import get_ec2_prices, get_ec2_prices_bulk

        assert get_ec2_prices_bulk is get_ec2_prices

    def test_get_ec2_price_with_refresh(self, mock_pricing_service, sample_ec2_prices):
        """refresh=True로 EC2 가격 조회"""
        from core.shared.aws.pricing.ec2 import get_ec2_price

        _ = get_ec2_price("t3.micro", "ap-northeast-2", refresh=True)

        mock_pricing_service.get_prices.assert_called_with("ec2", "ap-northeast-2", True)


class TestEC2PricingCalculation:
    """EC2 가격 계산 테스트"""

    def test_monthly_cost_calculation_accuracy(self):
        """월간 비용 계산 정확성"""
        hourly_price = 0.0104  # t3.micro
        expected_monthly = round(hourly_price * 730, 2)  # 7.59

        assert expected_monthly == 7.59

    def test_various_instance_types(self, sample_ec2_prices):
        """다양한 인스턴스 타입 가격 확인"""
        assert sample_ec2_prices["t3.micro"] < sample_ec2_prices["t3.small"]
        assert sample_ec2_prices["t3.small"] < sample_ec2_prices["t3.medium"]
        assert sample_ec2_prices["t3.medium"] < sample_ec2_prices["t3.large"]
