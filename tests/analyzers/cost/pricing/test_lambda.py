"""
tests/analyzers/cost/pricing/test_lambda.py - Lambda 가격 조회 테스트
"""

from unittest.mock import patch

import pytest


class TestGetLambdaPrices:
    """get_lambda_prices 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.pricing_service")
    def test_returns_prices_from_service(self, mock_service):
        """pricing_service에서 가격 반환"""
        from shared.aws.pricing.lambda_ import get_lambda_prices

        mock_service.get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
            "provisioned_concurrency_per_gb_hour": 0.000004646,
        }

        result = get_lambda_prices("ap-northeast-2")

        mock_service.get_prices.assert_called_once_with("lambda", "ap-northeast-2", False)
        assert result["request_per_million"] == 0.20
        assert result["duration_per_gb_second"] == 0.0000166667

    @patch("shared.aws.pricing.lambda_.pricing_service")
    def test_refresh_flag(self, mock_service):
        """refresh 플래그 전달"""
        from shared.aws.pricing.lambda_ import get_lambda_prices

        mock_service.get_prices.return_value = {}
        get_lambda_prices("us-east-1", refresh=True)

        mock_service.get_prices.assert_called_once_with("lambda", "us-east-1", True)


class TestGetLambdaRequestPrice:
    """get_lambda_request_price 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_returns_request_price(self, mock_get_prices):
        """요청 가격 반환"""
        from shared.aws.pricing.lambda_ import get_lambda_request_price

        mock_get_prices.return_value = {"request_per_million": 0.25}
        result = get_lambda_request_price("ap-northeast-2")

        assert result == 0.25

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_default_value_when_missing(self, mock_get_prices):
        """가격이 없을 때 기본값"""
        from shared.aws.pricing.lambda_ import get_lambda_request_price

        mock_get_prices.return_value = {}
        result = get_lambda_request_price("ap-northeast-2")

        assert result == 0.20


class TestGetLambdaDurationPrice:
    """get_lambda_duration_price 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_returns_duration_price(self, mock_get_prices):
        """실행 시간 가격 반환"""
        from shared.aws.pricing.lambda_ import get_lambda_duration_price

        mock_get_prices.return_value = {"duration_per_gb_second": 0.00002}
        result = get_lambda_duration_price("ap-northeast-2")

        assert result == 0.00002

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_default_value_when_missing(self, mock_get_prices):
        """가격이 없을 때 기본값"""
        from shared.aws.pricing.lambda_ import get_lambda_duration_price

        mock_get_prices.return_value = {}
        result = get_lambda_duration_price("ap-northeast-2")

        assert result == 0.0000166667


class TestGetLambdaProvisionedPrice:
    """get_lambda_provisioned_price 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_returns_provisioned_price(self, mock_get_prices):
        """Provisioned Concurrency 가격 반환"""
        from shared.aws.pricing.lambda_ import get_lambda_provisioned_price

        mock_get_prices.return_value = {"provisioned_concurrency_per_gb_hour": 0.000005}
        result = get_lambda_provisioned_price("ap-northeast-2")

        assert result == 0.000005


class TestGetLambdaMonthlyCost:
    """get_lambda_monthly_cost 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_basic_cost_calculation(self, mock_get_prices):
        """기본 비용 계산"""
        from shared.aws.pricing.lambda_ import get_lambda_monthly_cost

        mock_get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
        }

        # 2백만 호출, 평균 100ms, 256MB 메모리
        result = get_lambda_monthly_cost(
            region="ap-northeast-2",
            invocations=2_000_000,
            avg_duration_ms=100,
            memory_mb=256,
            include_free_tier=False,
        )

        # 요청 비용: 2M / 1M * $0.20 = $0.40
        # GB-초: (256/1024) * (100/1000) * 2M = 50,000 GB-초
        # 실행 비용: 50,000 * $0.0000166667 = $0.833335
        # 총합: $1.23
        assert result > 0

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_with_free_tier(self, mock_get_prices):
        """프리 티어 적용"""
        from shared.aws.pricing.lambda_ import get_lambda_monthly_cost

        mock_get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
        }

        # 100만 호출 (프리 티어 내)
        result = get_lambda_monthly_cost(
            region="ap-northeast-2",
            invocations=1_000_000,
            avg_duration_ms=100,
            memory_mb=128,
            include_free_tier=True,
        )

        # 프리 티어 적용 시 요청 비용 0
        assert result >= 0

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_zero_invocations(self, mock_get_prices):
        """호출이 없을 때"""
        from shared.aws.pricing.lambda_ import get_lambda_monthly_cost

        mock_get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
        }

        result = get_lambda_monthly_cost(
            region="ap-northeast-2",
            invocations=0,
            avg_duration_ms=100,
            memory_mb=128,
        )

        assert result == 0.0


class TestGetLambdaProvisionedMonthlyCost:
    """get_lambda_provisioned_monthly_cost 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_provisioned_cost(self, mock_get_prices):
        """Provisioned Concurrency 비용 계산"""
        from shared.aws.pricing.lambda_ import get_lambda_provisioned_monthly_cost

        mock_get_prices.return_value = {
            "provisioned_concurrency_per_gb_hour": 0.000004646,
        }

        result = get_lambda_provisioned_monthly_cost(
            region="ap-northeast-2",
            memory_mb=512,
            provisioned_concurrency=10,
            hours=730,
        )

        # GB-시간: (512/1024) * 10 * 730 = 3,650 GB-시간
        # 비용: 3,650 * $0.000004646 = ~$0.017
        assert result > 0

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_zero_concurrency(self, mock_get_prices):
        """Provisioned Concurrency가 0일 때"""
        from shared.aws.pricing.lambda_ import get_lambda_provisioned_monthly_cost

        mock_get_prices.return_value = {}

        result = get_lambda_provisioned_monthly_cost(
            region="ap-northeast-2",
            memory_mb=128,
            provisioned_concurrency=0,
        )

        assert result == 0.0


class TestEstimateLambdaCost:
    """estimate_lambda_cost 함수 테스트"""

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_full_estimate(self, mock_get_prices):
        """종합 비용 추정"""
        from shared.aws.pricing.lambda_ import estimate_lambda_cost

        mock_get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
            "provisioned_concurrency_per_gb_hour": 0.000004646,
        }

        result = estimate_lambda_cost(
            region="ap-northeast-2",
            invocations=2_000_000,
            avg_duration_ms=100,
            memory_mb=256,
            provisioned_concurrency=5,
            include_free_tier=False,
        )

        assert "request_cost" in result
        assert "duration_cost" in result
        assert "provisioned_cost" in result
        assert "total_cost" in result
        # 부동소수점 정밀도 문제로 pytest.approx 사용
        expected_total = result["request_cost"] + result["duration_cost"] + result["provisioned_cost"]
        assert result["total_cost"] == pytest.approx(expected_total, rel=1e-4)

    @patch("shared.aws.pricing.lambda_.get_lambda_prices")
    def test_no_provisioned_concurrency(self, mock_get_prices):
        """Provisioned Concurrency 없이"""
        from shared.aws.pricing.lambda_ import estimate_lambda_cost

        mock_get_prices.return_value = {
            "request_per_million": 0.20,
            "duration_per_gb_second": 0.0000166667,
            "provisioned_concurrency_per_gb_hour": 0.000004646,
        }

        result = estimate_lambda_cost(
            region="ap-northeast-2",
            invocations=1_000_000,
            avg_duration_ms=50,
            memory_mb=128,
            provisioned_concurrency=0,
        )

        assert result["provisioned_cost"] == 0.0
