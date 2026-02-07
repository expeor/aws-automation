"""
tests/analyzers/cost/pricing/test_rds.py - RDS 가격 조회 테스트
"""

from unittest.mock import MagicMock, patch


class TestGetRdsPrices:
    """get_rds_prices 함수 테스트"""

    def test_returns_cached_prices_without_session(self):
        """세션 없이 캐시된 가격 반환"""
        from shared.aws.pricing.rds import get_rds_prices

        result = get_rds_prices("ap-northeast-2", "mysql", session=None)

        assert isinstance(result, dict)
        assert "db.t3.micro" in result
        assert "db.m6g.large" in result

    def test_returns_us_east_1_for_unknown_region(self):
        """알 수 없는 리전은 us-east-1 가격 반환"""
        from shared.aws.pricing.rds import get_rds_prices

        result = get_rds_prices("unknown-region-1", "mysql", session=None)

        # us-east-1 가격이 반환됨
        assert isinstance(result, dict)

    @patch("shared.aws.pricing.rds.get_rds_prices_from_api")
    def test_uses_api_when_session_provided(self, mock_api):
        """세션이 있으면 API 사용"""
        from shared.aws.pricing.rds import get_rds_prices

        mock_session = MagicMock()
        mock_api.return_value = {"db.t3.micro": 0.019}

        result = get_rds_prices("ap-northeast-2", "mysql", session=mock_session)

        mock_api.assert_called_once_with(mock_session, "ap-northeast-2", "mysql")
        assert result == {"db.t3.micro": 0.019}


class TestGetRdsInstancePrice:
    """get_rds_instance_price 함수 테스트"""

    def test_returns_known_instance_price(self):
        """알려진 인스턴스 가격 반환"""
        from shared.aws.pricing.rds import get_rds_instance_price

        result = get_rds_instance_price("ap-northeast-2", "db.t3.micro", "mysql")

        assert result == 0.018

    def test_returns_default_for_unknown_instance(self):
        """알 수 없는 인스턴스는 기본값 반환"""
        from shared.aws.pricing.rds import get_rds_instance_price

        result = get_rds_instance_price("ap-northeast-2", "db.unknown.xlarge", "mysql")

        assert result == 0.20  # DEFAULT_INSTANCE_PRICE


class TestGetRdsStoragePrice:
    """get_rds_storage_price 함수 테스트"""

    def test_returns_gp3_price(self):
        """gp3 스토리지 가격"""
        from shared.aws.pricing.rds import get_rds_storage_price

        result = get_rds_storage_price("ap-northeast-2", "gp3")

        assert result == 0.095

    def test_returns_gp2_price(self):
        """gp2 스토리지 가격"""
        from shared.aws.pricing.rds import get_rds_storage_price

        result = get_rds_storage_price("ap-northeast-2", "gp2")

        assert result == 0.115

    def test_returns_io1_price(self):
        """io1 스토리지 가격"""
        from shared.aws.pricing.rds import get_rds_storage_price

        result = get_rds_storage_price("ap-northeast-2", "io1")

        assert result == 0.125

    def test_default_for_unknown_type(self):
        """알 수 없는 타입은 기본값"""
        from shared.aws.pricing.rds import get_rds_storage_price

        result = get_rds_storage_price("ap-northeast-2", "unknown")

        assert result == 0.095  # gp3 기본값


class TestGetRdsMonthlyCost:
    """get_rds_monthly_cost 함수 테스트"""

    def test_single_az_calculation(self):
        """Single-AZ 비용 계산"""
        from shared.aws.pricing.rds import HOURS_PER_MONTH, get_rds_monthly_cost

        result = get_rds_monthly_cost(
            region="ap-northeast-2",
            instance_class="db.t3.micro",
            engine="mysql",
            storage_gb=100,
            storage_type="gp3",
            multi_az=False,
        )

        # 인스턴스: $0.018 * 730 = $13.14
        # 스토리지: 100 * $0.095 = $9.50
        # 총합: $22.64
        expected_instance = 0.018 * HOURS_PER_MONTH
        expected_storage = 100 * 0.095
        expected_total = round(expected_instance + expected_storage, 2)

        assert result == expected_total

    def test_multi_az_doubles_cost(self):
        """Multi-AZ는 2배 비용"""
        from shared.aws.pricing.rds import get_rds_monthly_cost

        single_az_cost = get_rds_monthly_cost(
            region="ap-northeast-2",
            instance_class="db.t3.micro",
            engine="mysql",
            storage_gb=100,
            storage_type="gp3",
            multi_az=False,
        )

        multi_az_cost = get_rds_monthly_cost(
            region="ap-northeast-2",
            instance_class="db.t3.micro",
            engine="mysql",
            storage_gb=100,
            storage_type="gp3",
            multi_az=True,
        )

        assert multi_az_cost == round(single_az_cost * 2, 2)

    def test_different_instance_classes(self):
        """다양한 인스턴스 클래스 비용"""
        from shared.aws.pricing.rds import get_rds_monthly_cost

        micro_cost = get_rds_monthly_cost(region="ap-northeast-2", instance_class="db.t3.micro", storage_gb=20)
        large_cost = get_rds_monthly_cost(region="ap-northeast-2", instance_class="db.m6g.large", storage_gb=20)

        # larger instance should cost more
        assert large_cost > micro_cost

    def test_storage_size_impact(self):
        """스토리지 크기 영향"""
        from shared.aws.pricing.rds import get_rds_monthly_cost

        small_storage = get_rds_monthly_cost(region="ap-northeast-2", instance_class="db.t3.micro", storage_gb=20)
        large_storage = get_rds_monthly_cost(region="ap-northeast-2", instance_class="db.t3.micro", storage_gb=500)

        assert large_storage > small_storage


class TestGetRdsPricesFromApi:
    """get_rds_prices_from_api 함수 테스트"""

    @patch("shared.aws.pricing.rds.get_client")
    def test_successful_api_call(self, mock_get_client):
        """API 호출 성공"""
        from shared.aws.pricing.rds import get_rds_prices_from_api

        mock_pricing = MagicMock()
        mock_get_client.return_value = mock_pricing
        mock_pricing.get_products.return_value = {
            "PriceList": [
                {
                    "product": {"attributes": {"instanceType": "db.t3.micro"}},
                    "terms": {"OnDemand": {"term1": {"priceDimensions": {"dim1": {"pricePerUnit": {"USD": "0.020"}}}}}},
                }
            ]
        }

        mock_session = MagicMock()
        result = get_rds_prices_from_api(mock_session, "ap-northeast-2", "mysql")

        assert isinstance(result, dict)

    @patch("shared.aws.pricing.rds.get_client")
    def test_handles_api_error(self, mock_get_client):
        """API 오류 처리"""
        from botocore.exceptions import ClientError

        from shared.aws.pricing.rds import get_rds_prices_from_api

        mock_pricing = MagicMock()
        mock_get_client.return_value = mock_pricing
        mock_pricing.get_products.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetProducts",
        )

        mock_session = MagicMock()
        result = get_rds_prices_from_api(mock_session, "ap-northeast-2", "mysql")

        assert result == {}

    @patch("shared.aws.pricing.rds.get_client")
    def test_engine_filter_postgresql(self, mock_get_client):
        """PostgreSQL 엔진 필터"""
        from shared.aws.pricing.rds import get_rds_prices_from_api

        mock_pricing = MagicMock()
        mock_get_client.return_value = mock_pricing
        mock_pricing.get_products.return_value = {"PriceList": []}

        mock_session = MagicMock()
        get_rds_prices_from_api(mock_session, "ap-northeast-2", "postgres")

        # Verify the filter includes PostgreSQL
        call_args = mock_pricing.get_products.call_args
        filters = call_args.kwargs["Filters"]
        engine_filter = next(f for f in filters if f["Field"] == "databaseEngine")
        assert engine_filter["Value"] == "PostgreSQL"
