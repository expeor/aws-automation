"""
tests/plugins/cost/pricing/test_constants.py - 상수 및 기본값 테스트
"""

from analyzers.cost.pricing.constants import (
    DEFAULT_PRICES,
    HOURS_PER_MONTH,
    LAMBDA_FREE_TIER_GB_SECONDS,
    LAMBDA_FREE_TIER_REQUESTS,
    get_default_prices,
)


class TestConstants:
    """상수 테스트"""

    def test_hours_per_month(self):
        """월간 시간 상수가 730인지 확인"""
        assert HOURS_PER_MONTH == 730

    def test_lambda_free_tier_requests(self):
        """Lambda 프리티어 요청 수가 100만인지 확인"""
        assert LAMBDA_FREE_TIER_REQUESTS == 1_000_000

    def test_lambda_free_tier_gb_seconds(self):
        """Lambda 프리티어 GB-초가 40만인지 확인"""
        assert LAMBDA_FREE_TIER_GB_SECONDS == 400_000


class TestDefaultPrices:
    """기본값 테스트"""

    def test_default_prices_has_ec2(self):
        """EC2 기본값이 존재하는지 확인"""
        assert "ec2" in DEFAULT_PRICES
        assert len(DEFAULT_PRICES["ec2"]) > 0

    def test_default_prices_has_ebs(self):
        """EBS 기본값이 존재하는지 확인"""
        assert "ebs" in DEFAULT_PRICES
        assert "gp3" in DEFAULT_PRICES["ebs"]
        assert "gp2" in DEFAULT_PRICES["ebs"]

    def test_default_prices_has_sagemaker(self):
        """SageMaker 기본값이 존재하는지 확인"""
        assert "sagemaker" in DEFAULT_PRICES
        assert len(DEFAULT_PRICES["sagemaker"]) > 0

    def test_default_prices_has_lambda(self):
        """Lambda 기본값이 존재하는지 확인"""
        assert "lambda" in DEFAULT_PRICES
        assert "request_per_million" in DEFAULT_PRICES["lambda"]
        assert "duration_per_gb_second" in DEFAULT_PRICES["lambda"]

    def test_default_prices_has_dynamodb(self):
        """DynamoDB 기본값이 존재하는지 확인"""
        assert "dynamodb" in DEFAULT_PRICES
        assert "storage_per_gb" in DEFAULT_PRICES["dynamodb"]

    def test_ec2_price_values_are_positive(self):
        """EC2 가격이 양수인지 확인"""
        for instance_type, price in DEFAULT_PRICES["ec2"].items():
            assert price > 0, f"{instance_type} 가격이 0 이하: {price}"

    def test_ebs_price_values_are_positive(self):
        """EBS 가격이 양수인지 확인"""
        for volume_type, price in DEFAULT_PRICES["ebs"].items():
            assert price > 0, f"{volume_type} 가격이 0 이하: {price}"


class TestGetDefaultPrices:
    """get_default_prices 함수 테스트"""

    def test_get_default_prices_ec2(self):
        """EC2 기본값 조회"""
        prices = get_default_prices("ec2")
        assert isinstance(prices, dict)
        assert len(prices) > 0
        assert "t3.micro" in prices

    def test_get_default_prices_unknown_service(self):
        """알 수 없는 서비스 조회 시 빈 딕셔너리 반환"""
        prices = get_default_prices("unknown_service")
        assert isinstance(prices, dict)
        assert len(prices) == 0

    def test_get_default_prices_returns_copy(self):
        """반환값이 원본의 복사본인지 확인"""
        prices1 = get_default_prices("ec2")
        prices2 = get_default_prices("ec2")
        assert prices1 is not prices2  # 다른 객체
        assert prices1 == prices2  # 같은 내용
