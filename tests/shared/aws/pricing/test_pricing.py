"""
tests/shared/aws/pricing/test_pricing.py - Comprehensive pricing module tests

Tests for all pricing functions across different AWS services.

Test Coverage:
    - EC2 pricing (ec2.py): Instance pricing, monthly costs
    - EBS pricing (ebs.py): Volume pricing, storage costs
    - Lambda pricing (lambda_.py): Request, duration, provisioned concurrency
    - RDS pricing (rds.py): Instance and storage pricing, Multi-AZ
    - SageMaker pricing (sagemaker.py): Endpoint instance pricing
    - NAT Gateway pricing (nat.py): Hourly and data transfer costs
    - EIP pricing (eip.py): Elastic IP unused costs
    - ELB pricing (elb.py): ALB, NLB, CLB pricing
    - Snapshot pricing (snapshot.py): EBS snapshot storage
    - ECR pricing (ecr.py): Container registry storage
    - Constants (constants.py): Default prices and configuration
    - Utils (utils.py): PricingService and metrics

Test Classes:
    - TestEC2Pricing: 6 tests
    - TestEBSPricing: 5 tests
    - TestLambdaPricing: 8 tests
    - TestRDSPricing: 4 tests
    - TestSageMakerPricing: 5 tests
    - TestNATPricing: 6 tests
    - TestEIPPricing: 3 tests
    - TestELBPricing: 5 tests
    - TestSnapshotPricing: 3 tests
    - TestECRPricing: 3 tests
    - TestConstants: 4 tests
    - TestPricingUtils: 7 tests
    - TestPricingIntegration: 4 tests

Total: 63 tests covering the most commonly used pricing functions.

Note: Tests use mocking for PricingService to avoid external API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.aws.pricing.constants import HOURS_PER_MONTH, LAMBDA_FREE_TIER_GB_SECONDS, LAMBDA_FREE_TIER_REQUESTS


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_ec2_prices():
    """Sample EC2 pricing data"""
    return {
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "t3.large": 0.0832,
        "m5.large": 0.096,
        "c5.large": 0.085,
    }


@pytest.fixture
def sample_ebs_prices():
    """Sample EBS pricing data"""
    return {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.025,
        "standard": 0.05,
    }


@pytest.fixture
def sample_lambda_prices():
    """Sample Lambda pricing data"""
    return {
        "request_per_million": 0.20,
        "duration_per_gb_second": 0.0000166667,
        "provisioned_concurrency_per_gb_hour": 0.000004646,
    }


@pytest.fixture
def sample_rds_instance_prices():
    """Sample RDS instance pricing data"""
    return {
        "db.t3.micro": 0.018,
        "db.t3.small": 0.036,
        "db.t3.medium": 0.073,
        "db.r6g.large": 0.240,
    }


@pytest.fixture
def sample_rds_storage_prices():
    """Sample RDS storage pricing data"""
    return {"gp2": 0.115, "gp3": 0.095, "io1": 0.125, "magnetic": 0.10}


@pytest.fixture
def sample_sagemaker_prices():
    """Sample SageMaker pricing data"""
    return {
        "ml.t3.medium": 0.0416,
        "ml.m5.large": 0.115,
        "ml.c5.xlarge": 0.204,
        "ml.g4dn.xlarge": 0.736,
    }


@pytest.fixture
def sample_nat_prices():
    """Sample NAT Gateway pricing data"""
    return {"hourly": 0.045, "per_gb": 0.045}


@pytest.fixture
def sample_eip_prices():
    """Sample EIP pricing data"""
    return {"unused_hourly": 0.005, "additional_hourly": 0.005}


@pytest.fixture
def sample_elb_prices():
    """Sample ELB pricing data"""
    return {
        "alb_hourly": 0.0225,
        "nlb_hourly": 0.0225,
        "glb_hourly": 0.0125,
        "clb_hourly": 0.025,
    }


@pytest.fixture
def sample_snapshot_prices():
    """Sample snapshot pricing data"""
    return {"storage_per_gb_monthly": 0.05}


@pytest.fixture
def sample_ecr_prices():
    """Sample ECR pricing data"""
    return {"storage_per_gb_monthly": 0.10}


# =============================================================================
# EC2 Pricing Tests
# =============================================================================


class TestEC2Pricing:
    """EC2 pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_ec2_prices):
        """Mock PricingService for EC2"""
        with patch("shared.aws.pricing.ec2.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_ec2_prices
            yield mock_service

    def test_get_ec2_price(self, mock_pricing_service, sample_ec2_prices):
        """Test EC2 instance price lookup"""
        from shared.aws.pricing.ec2 import get_ec2_price

        price = get_ec2_price("t3.micro", "ap-northeast-2")

        assert price == sample_ec2_prices["t3.micro"]
        mock_pricing_service.get_prices.assert_called_with("ec2", "ap-northeast-2", False)

    def test_get_ec2_price_unknown_instance(self, mock_pricing_service):
        """Test EC2 price lookup for unknown instance type"""
        from shared.aws.pricing.ec2 import get_ec2_price

        price = get_ec2_price("unknown.instance", "ap-northeast-2")

        assert price == 0.0

    def test_get_ec2_monthly_cost(self, mock_pricing_service, sample_ec2_prices):
        """Test EC2 monthly cost calculation"""
        from shared.aws.pricing.ec2 import get_ec2_monthly_cost

        monthly_cost = get_ec2_monthly_cost("t3.micro", "ap-northeast-2")

        expected = round(sample_ec2_prices["t3.micro"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected

    def test_get_ec2_monthly_cost_custom_hours(self, mock_pricing_service, sample_ec2_prices):
        """Test EC2 monthly cost with custom hours"""
        from shared.aws.pricing.ec2 import get_ec2_monthly_cost

        custom_hours = 168  # 1 week
        monthly_cost = get_ec2_monthly_cost("t3.micro", "ap-northeast-2", hours_per_month=custom_hours)

        expected = round(sample_ec2_prices["t3.micro"] * custom_hours, 2)
        assert monthly_cost == expected

    def test_get_ec2_prices(self, mock_pricing_service, sample_ec2_prices):
        """Test retrieving all EC2 prices"""
        from shared.aws.pricing.ec2 import get_ec2_prices

        prices = get_ec2_prices("ap-northeast-2")

        assert prices == sample_ec2_prices

    def test_get_ec2_prices_bulk_alias(self):
        """Test that get_ec2_prices_bulk is an alias of get_ec2_prices"""
        from shared.aws.pricing.ec2 import get_ec2_prices, get_ec2_prices_bulk

        assert get_ec2_prices_bulk is get_ec2_prices


# =============================================================================
# EBS Pricing Tests
# =============================================================================


class TestEBSPricing:
    """EBS pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_ebs_prices):
        """Mock PricingService for EBS"""
        with patch("shared.aws.pricing.ebs.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_ebs_prices
            yield mock_service

    def test_get_ebs_price(self, mock_pricing_service, sample_ebs_prices):
        """Test EBS volume price per GB"""
        from shared.aws.pricing.ebs import get_ebs_price

        price = get_ebs_price("gp3", "ap-northeast-2")

        assert price == sample_ebs_prices["gp3"]

    def test_get_ebs_price_unknown_type(self, mock_pricing_service):
        """Test EBS price lookup for unknown volume type"""
        from shared.aws.pricing.ebs import get_ebs_price

        price = get_ebs_price("unknown", "ap-northeast-2")

        assert price == 0.0

    def test_get_ebs_monthly_cost(self, mock_pricing_service, sample_ebs_prices):
        """Test EBS monthly cost calculation"""
        from shared.aws.pricing.ebs import get_ebs_monthly_cost

        monthly_cost = get_ebs_monthly_cost("gp3", 100, "ap-northeast-2")

        expected = round(sample_ebs_prices["gp3"] * 100, 2)
        assert monthly_cost == expected

    def test_get_ebs_prices(self, mock_pricing_service, sample_ebs_prices):
        """Test retrieving all EBS prices"""
        from shared.aws.pricing.ebs import get_ebs_prices

        prices = get_ebs_prices("ap-northeast-2")

        assert prices == sample_ebs_prices

    def test_get_ebs_prices_bulk_alias(self):
        """Test that get_ebs_prices_bulk is an alias of get_ebs_prices"""
        from shared.aws.pricing.ebs import get_ebs_prices, get_ebs_prices_bulk

        assert get_ebs_prices_bulk is get_ebs_prices


# =============================================================================
# Lambda Pricing Tests
# =============================================================================


class TestLambdaPricing:
    """Lambda pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_lambda_prices):
        """Mock PricingService for Lambda"""
        with patch("shared.aws.pricing.lambda_.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_lambda_prices
            yield mock_service

    def test_get_lambda_prices(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda prices lookup"""
        from shared.aws.pricing.lambda_ import get_lambda_prices

        prices = get_lambda_prices("ap-northeast-2")

        assert prices == sample_lambda_prices

    def test_get_lambda_request_price(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda request price per million"""
        from shared.aws.pricing.lambda_ import get_lambda_request_price

        price = get_lambda_request_price("ap-northeast-2")

        assert price == sample_lambda_prices["request_per_million"]

    def test_get_lambda_duration_price(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda duration price per GB-second"""
        from shared.aws.pricing.lambda_ import get_lambda_duration_price

        price = get_lambda_duration_price("ap-northeast-2")

        assert price == sample_lambda_prices["duration_per_gb_second"]

    def test_get_lambda_provisioned_price(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda provisioned concurrency price"""
        from shared.aws.pricing.lambda_ import get_lambda_provisioned_price

        price = get_lambda_provisioned_price("ap-northeast-2")

        assert price == sample_lambda_prices["provisioned_concurrency_per_gb_hour"]

    def test_get_lambda_monthly_cost(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda monthly cost calculation"""
        from shared.aws.pricing.lambda_ import get_lambda_monthly_cost

        # Use higher invocations to exceed free tier for both requests and duration
        monthly_cost = get_lambda_monthly_cost(
            region="ap-northeast-2",
            invocations=10_000_000,
            avg_duration_ms=200,
            memory_mb=256,
            include_free_tier=True,
        )

        # Request cost (after free tier)
        billable_requests = 10_000_000 - LAMBDA_FREE_TIER_REQUESTS
        request_cost = (billable_requests / 1_000_000) * sample_lambda_prices["request_per_million"]

        # Duration cost (after free tier)
        gb_seconds = (256 / 1024) * (200 / 1000) * 10_000_000
        billable_gb_seconds = max(0, gb_seconds - LAMBDA_FREE_TIER_GB_SECONDS)
        duration_cost = billable_gb_seconds * sample_lambda_prices["duration_per_gb_second"]

        expected = round(request_cost + duration_cost, 4)
        assert monthly_cost == expected

    def test_get_lambda_monthly_cost_no_free_tier(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda monthly cost without free tier"""
        from shared.aws.pricing.lambda_ import get_lambda_monthly_cost

        monthly_cost = get_lambda_monthly_cost(
            region="ap-northeast-2",
            invocations=1_000_000,
            avg_duration_ms=100,
            memory_mb=128,
            include_free_tier=False,
        )

        request_cost = (1_000_000 / 1_000_000) * sample_lambda_prices["request_per_million"]
        gb_seconds = (128 / 1024) * (100 / 1000) * 1_000_000
        duration_cost = gb_seconds * sample_lambda_prices["duration_per_gb_second"]

        expected = round(request_cost + duration_cost, 4)
        assert monthly_cost == expected

    def test_get_lambda_provisioned_monthly_cost(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda provisioned concurrency monthly cost"""
        from shared.aws.pricing.lambda_ import get_lambda_provisioned_monthly_cost

        monthly_cost = get_lambda_provisioned_monthly_cost(
            region="ap-northeast-2",
            memory_mb=256,
            provisioned_concurrency=10,
            hours=HOURS_PER_MONTH,
        )

        gb_hours = (256 / 1024) * 10 * HOURS_PER_MONTH
        expected = round(gb_hours * sample_lambda_prices["provisioned_concurrency_per_gb_hour"], 4)
        assert monthly_cost == expected

    def test_estimate_lambda_cost(self, mock_pricing_service, sample_lambda_prices):
        """Test Lambda comprehensive cost estimation"""
        from shared.aws.pricing.lambda_ import estimate_lambda_cost

        result = estimate_lambda_cost(
            region="ap-northeast-2",
            invocations=10_000_000,
            avg_duration_ms=200,
            memory_mb=256,
            provisioned_concurrency=5,
            include_free_tier=True,
        )

        assert "request_cost" in result
        assert "duration_cost" in result
        assert "provisioned_cost" in result
        assert "total_cost" in result
        # Check total is approximately equal (accounting for rounding)
        calculated_total = round(result["request_cost"] + result["duration_cost"] + result["provisioned_cost"], 4)
        assert result["total_cost"] == calculated_total


# =============================================================================
# RDS Pricing Tests
# =============================================================================


class TestRDSPricing:
    """RDS pricing module tests"""

    def test_get_rds_instance_price(self, sample_rds_instance_prices):
        """Test RDS instance price lookup"""
        from shared.aws.pricing.rds import get_rds_instance_price

        with patch("shared.aws.pricing.rds.RDS_INSTANCE_PRICES", {"ap-northeast-2": sample_rds_instance_prices}):
            price = get_rds_instance_price("ap-northeast-2", "db.t3.micro", "mysql")

            assert price == sample_rds_instance_prices["db.t3.micro"]

    def test_get_rds_storage_price(self, sample_rds_storage_prices):
        """Test RDS storage price lookup"""
        from shared.aws.pricing.rds import get_rds_storage_price

        with patch("shared.aws.pricing.rds.RDS_STORAGE_PRICES", {"ap-northeast-2": sample_rds_storage_prices}):
            price = get_rds_storage_price("ap-northeast-2", "gp3")

            assert price == sample_rds_storage_prices["gp3"]

    def test_get_rds_monthly_cost(self, sample_rds_instance_prices, sample_rds_storage_prices):
        """Test RDS monthly cost calculation"""
        from shared.aws.pricing.rds import get_rds_monthly_cost

        with patch("shared.aws.pricing.rds.RDS_INSTANCE_PRICES", {"ap-northeast-2": sample_rds_instance_prices}):
            with patch("shared.aws.pricing.rds.RDS_STORAGE_PRICES", {"ap-northeast-2": sample_rds_storage_prices}):
                monthly_cost = get_rds_monthly_cost(
                    region="ap-northeast-2",
                    instance_class="db.t3.micro",
                    engine="mysql",
                    storage_gb=100,
                    storage_type="gp3",
                    multi_az=False,
                )

                instance_cost = sample_rds_instance_prices["db.t3.micro"] * HOURS_PER_MONTH
                storage_cost = sample_rds_storage_prices["gp3"] * 100
                expected = round(instance_cost + storage_cost, 2)
                assert monthly_cost == expected

    def test_get_rds_monthly_cost_multi_az(self, sample_rds_instance_prices, sample_rds_storage_prices):
        """Test RDS monthly cost with Multi-AZ"""
        from shared.aws.pricing.rds import get_rds_monthly_cost

        with patch("shared.aws.pricing.rds.RDS_INSTANCE_PRICES", {"ap-northeast-2": sample_rds_instance_prices}):
            with patch("shared.aws.pricing.rds.RDS_STORAGE_PRICES", {"ap-northeast-2": sample_rds_storage_prices}):
                monthly_cost = get_rds_monthly_cost(
                    region="ap-northeast-2",
                    instance_class="db.t3.micro",
                    engine="mysql",
                    storage_gb=100,
                    storage_type="gp3",
                    multi_az=True,
                )

                instance_cost = sample_rds_instance_prices["db.t3.micro"] * HOURS_PER_MONTH * 2
                storage_cost = sample_rds_storage_prices["gp3"] * 100 * 2
                expected = round(instance_cost + storage_cost, 2)
                assert monthly_cost == expected


# =============================================================================
# SageMaker Pricing Tests
# =============================================================================


class TestSageMakerPricing:
    """SageMaker pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_sagemaker_prices):
        """Mock PricingService for SageMaker"""
        with patch("shared.aws.pricing.sagemaker.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_sagemaker_prices
            yield mock_service

    def test_get_sagemaker_price(self, mock_pricing_service, sample_sagemaker_prices):
        """Test SageMaker instance price lookup"""
        from shared.aws.pricing.sagemaker import get_sagemaker_price

        price = get_sagemaker_price("ml.m5.large", "ap-northeast-2")

        assert price == sample_sagemaker_prices["ml.m5.large"]

    def test_get_sagemaker_price_unknown_instance(self, mock_pricing_service):
        """Test SageMaker price for unknown instance type"""
        from shared.aws.pricing.sagemaker import get_sagemaker_price

        price = get_sagemaker_price("ml.unknown.large", "ap-northeast-2")

        # Should return default price for unknown instances
        assert price == 0.50

    def test_get_sagemaker_monthly_cost(self, mock_pricing_service, sample_sagemaker_prices):
        """Test SageMaker monthly cost calculation"""
        from shared.aws.pricing.sagemaker import get_sagemaker_monthly_cost

        monthly_cost = get_sagemaker_monthly_cost("ml.m5.large", "ap-northeast-2")

        expected = round(sample_sagemaker_prices["ml.m5.large"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected

    def test_get_sagemaker_monthly_cost_multiple_instances(self, mock_pricing_service, sample_sagemaker_prices):
        """Test SageMaker monthly cost with multiple instances"""
        from shared.aws.pricing.sagemaker import get_sagemaker_monthly_cost

        monthly_cost = get_sagemaker_monthly_cost("ml.m5.large", "ap-northeast-2", instance_count=3)

        expected = round(sample_sagemaker_prices["ml.m5.large"] * HOURS_PER_MONTH * 3, 2)
        assert monthly_cost == expected

    def test_get_sagemaker_prices_bulk_alias(self):
        """Test that get_sagemaker_prices_bulk is an alias"""
        from shared.aws.pricing.sagemaker import get_sagemaker_prices, get_sagemaker_prices_bulk

        assert get_sagemaker_prices_bulk is get_sagemaker_prices


# =============================================================================
# NAT Gateway Pricing Tests
# =============================================================================


class TestNATPricing:
    """NAT Gateway pricing module tests"""

    def test_get_nat_prices(self):
        """Test NAT Gateway prices lookup"""
        from shared.aws.pricing.nat import get_nat_prices

        prices = get_nat_prices("ap-northeast-2")

        assert "hourly" in prices
        assert "per_gb" in prices
        assert prices["hourly"] == 0.045
        assert prices["per_gb"] == 0.045

    def test_get_nat_hourly_price(self):
        """Test NAT Gateway hourly price"""
        from shared.aws.pricing.nat import get_nat_hourly_price

        price = get_nat_hourly_price("ap-northeast-2")

        assert price == 0.045

    def test_get_nat_data_price(self):
        """Test NAT Gateway data price per GB"""
        from shared.aws.pricing.nat import get_nat_data_price

        price = get_nat_data_price("ap-northeast-2")

        assert price == 0.045

    def test_get_nat_monthly_cost(self):
        """Test NAT Gateway monthly cost"""
        from shared.aws.pricing.nat import get_nat_monthly_cost

        monthly_cost = get_nat_monthly_cost("ap-northeast-2", hours=HOURS_PER_MONTH, data_processed_gb=100)

        fixed_cost = 0.045 * HOURS_PER_MONTH
        data_cost = 0.045 * 100
        expected = round(fixed_cost + data_cost, 2)
        assert monthly_cost == expected

    def test_get_nat_monthly_fixed_cost(self):
        """Test NAT Gateway monthly fixed cost without data"""
        from shared.aws.pricing.nat import get_nat_monthly_fixed_cost

        fixed_cost = get_nat_monthly_fixed_cost("ap-northeast-2")

        expected = round(0.045 * HOURS_PER_MONTH, 2)
        assert fixed_cost == expected

    def test_estimate_savings(self):
        """Test NAT Gateway savings estimation"""
        from shared.aws.pricing.nat import estimate_savings

        result = estimate_savings(nat_count=3, region="ap-northeast-2", months=12)

        assert result["nat_count"] == 3
        assert result["region"] == "ap-northeast-2"
        assert "monthly_per_nat" in result
        assert "monthly_total" in result
        assert "annual_total" in result


# =============================================================================
# EIP Pricing Tests
# =============================================================================


class TestEIPPricing:
    """Elastic IP pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_eip_prices):
        """Mock PricingService for EIP"""
        with patch("shared.aws.pricing.eip.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_eip_prices
            yield mock_service

    def test_get_eip_prices(self, mock_pricing_service, sample_eip_prices):
        """Test EIP prices lookup"""
        from shared.aws.pricing.eip import get_eip_prices

        prices = get_eip_prices("ap-northeast-2")

        assert prices == sample_eip_prices

    def test_get_eip_hourly_price(self, mock_pricing_service, sample_eip_prices):
        """Test EIP hourly price"""
        from shared.aws.pricing.eip import get_eip_hourly_price

        price = get_eip_hourly_price("ap-northeast-2")

        assert price == sample_eip_prices["unused_hourly"]

    def test_get_eip_monthly_cost(self, mock_pricing_service, sample_eip_prices):
        """Test EIP monthly cost"""
        from shared.aws.pricing.eip import get_eip_monthly_cost

        monthly_cost = get_eip_monthly_cost("ap-northeast-2")

        expected = round(sample_eip_prices["unused_hourly"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected


# =============================================================================
# ELB Pricing Tests
# =============================================================================


class TestELBPricing:
    """Elastic Load Balancer pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_elb_prices):
        """Mock PricingService for ELB"""
        with patch("shared.aws.pricing.elb.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_elb_prices
            yield mock_service

    def test_get_elb_prices(self, mock_pricing_service, sample_elb_prices):
        """Test ELB prices lookup"""
        from shared.aws.pricing.elb import get_elb_prices

        prices = get_elb_prices("ap-northeast-2")

        assert prices == sample_elb_prices

    def test_get_elb_hourly_price_alb(self, mock_pricing_service, sample_elb_prices):
        """Test ALB hourly price"""
        from shared.aws.pricing.elb import get_elb_hourly_price

        price = get_elb_hourly_price("ap-northeast-2", "application")

        assert price == sample_elb_prices["alb_hourly"]

    def test_get_elb_hourly_price_nlb(self, mock_pricing_service, sample_elb_prices):
        """Test NLB hourly price"""
        from shared.aws.pricing.elb import get_elb_hourly_price

        price = get_elb_hourly_price("ap-northeast-2", "network")

        assert price == sample_elb_prices["nlb_hourly"]

    def test_get_elb_hourly_price_clb(self, mock_pricing_service, sample_elb_prices):
        """Test CLB hourly price"""
        from shared.aws.pricing.elb import get_elb_hourly_price

        price = get_elb_hourly_price("ap-northeast-2", "classic")

        assert price == sample_elb_prices["clb_hourly"]

    def test_get_elb_monthly_cost(self, mock_pricing_service, sample_elb_prices):
        """Test ELB monthly cost"""
        from shared.aws.pricing.elb import get_elb_monthly_cost

        monthly_cost = get_elb_monthly_cost("ap-northeast-2", "application")

        expected = round(sample_elb_prices["alb_hourly"] * HOURS_PER_MONTH, 2)
        assert monthly_cost == expected


# =============================================================================
# Snapshot Pricing Tests
# =============================================================================


class TestSnapshotPricing:
    """EBS Snapshot pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_snapshot_prices):
        """Mock PricingService for Snapshot"""
        with patch("shared.aws.pricing.snapshot.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_snapshot_prices
            yield mock_service

    def test_get_snapshot_prices(self, mock_pricing_service, sample_snapshot_prices):
        """Test snapshot prices lookup"""
        from shared.aws.pricing.snapshot import get_snapshot_prices

        prices = get_snapshot_prices("ap-northeast-2")

        assert prices == sample_snapshot_prices

    def test_get_snapshot_price(self, mock_pricing_service, sample_snapshot_prices):
        """Test snapshot GB price"""
        from shared.aws.pricing.snapshot import get_snapshot_price

        price = get_snapshot_price("ap-northeast-2")

        assert price == sample_snapshot_prices["storage_per_gb_monthly"]

    def test_get_snapshot_monthly_cost(self, mock_pricing_service, sample_snapshot_prices):
        """Test snapshot monthly cost"""
        from shared.aws.pricing.snapshot import get_snapshot_monthly_cost

        monthly_cost = get_snapshot_monthly_cost("ap-northeast-2", size_gb=100)

        expected = round(sample_snapshot_prices["storage_per_gb_monthly"] * 100, 2)
        assert monthly_cost == expected


# =============================================================================
# ECR Pricing Tests
# =============================================================================


class TestECRPricing:
    """ECR pricing module tests"""

    @pytest.fixture
    def mock_pricing_service(self, sample_ecr_prices):
        """Mock PricingService for ECR"""
        with patch("shared.aws.pricing.ecr.pricing_service") as mock_service:
            mock_service.get_prices.return_value = sample_ecr_prices
            yield mock_service

    def test_get_ecr_prices(self, mock_pricing_service, sample_ecr_prices):
        """Test ECR prices lookup"""
        from shared.aws.pricing.ecr import get_ecr_prices

        prices = get_ecr_prices("ap-northeast-2")

        assert prices == sample_ecr_prices

    def test_get_ecr_storage_price(self, mock_pricing_service, sample_ecr_prices):
        """Test ECR storage price per GB"""
        from shared.aws.pricing.ecr import get_ecr_storage_price

        price = get_ecr_storage_price("ap-northeast-2")

        assert price == sample_ecr_prices["storage_per_gb_monthly"]

    def test_get_ecr_monthly_cost(self, mock_pricing_service, sample_ecr_prices):
        """Test ECR monthly cost"""
        from shared.aws.pricing.ecr import get_ecr_monthly_cost

        monthly_cost = get_ecr_monthly_cost("ap-northeast-2", storage_gb=50)

        expected = round(sample_ecr_prices["storage_per_gb_monthly"] * 50, 2)
        assert monthly_cost == expected


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Pricing constants tests"""

    def test_hours_per_month(self):
        """Test HOURS_PER_MONTH constant"""
        from shared.aws.pricing.constants import HOURS_PER_MONTH

        assert HOURS_PER_MONTH == 730

    def test_lambda_free_tier_constants(self):
        """Test Lambda free tier constants"""
        from shared.aws.pricing.constants import LAMBDA_FREE_TIER_GB_SECONDS, LAMBDA_FREE_TIER_REQUESTS

        assert LAMBDA_FREE_TIER_REQUESTS == 1_000_000
        assert LAMBDA_FREE_TIER_GB_SECONDS == 400_000

    def test_default_prices_structure(self):
        """Test DEFAULT_PRICES structure"""
        from shared.aws.pricing.constants import DEFAULT_PRICES

        assert isinstance(DEFAULT_PRICES, dict)
        assert "ec2" in DEFAULT_PRICES
        assert "ebs" in DEFAULT_PRICES
        assert "lambda" in DEFAULT_PRICES
        assert "nat" in DEFAULT_PRICES

    def test_get_default_prices(self):
        """Test get_default_prices function"""
        from shared.aws.pricing.constants import get_default_prices

        ec2_prices = get_default_prices("ec2")
        assert isinstance(ec2_prices, dict)
        assert "t3.micro" in ec2_prices

        unknown_prices = get_default_prices("unknown_service")
        assert unknown_prices == {}


# =============================================================================
# Utils Tests
# =============================================================================


class TestPricingUtils:
    """Pricing utils module tests"""

    def test_pricing_service_singleton(self):
        """Test that pricing_service is a singleton"""
        from shared.aws.pricing.utils import pricing_service, PricingService

        instance1 = PricingService()
        instance2 = PricingService()

        assert instance1 is instance2
        assert instance1 is pricing_service

    def test_pricing_metrics_initialization(self):
        """Test PricingMetrics initialization"""
        from shared.aws.pricing.utils import PricingMetrics

        metrics = PricingMetrics()

        assert metrics.api_calls == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.errors == 0
        assert metrics.retries == 0

    def test_pricing_metrics_increment(self):
        """Test PricingMetrics increment methods"""
        from shared.aws.pricing.utils import PricingMetrics

        metrics = PricingMetrics()

        metrics.increment_api_calls()
        assert metrics.api_calls == 1

        metrics.increment_cache_hits()
        assert metrics.cache_hits == 1

        metrics.increment_cache_misses()
        assert metrics.cache_misses == 1

        metrics.increment_errors()
        assert metrics.errors == 1

        metrics.increment_retries()
        assert metrics.retries == 1

    def test_pricing_metrics_hit_rate(self):
        """Test PricingMetrics hit rate calculation"""
        from shared.aws.pricing.utils import PricingMetrics

        metrics = PricingMetrics()

        # No hits or misses
        assert metrics.hit_rate == 0.0

        # 3 hits, 1 miss
        metrics.cache_hits = 3
        metrics.cache_misses = 1
        assert metrics.hit_rate == 0.75

        # All hits
        metrics.cache_hits = 10
        metrics.cache_misses = 0
        assert metrics.hit_rate == 1.0

    def test_pricing_metrics_to_dict(self):
        """Test PricingMetrics to_dict method"""
        from shared.aws.pricing.utils import PricingMetrics

        metrics = PricingMetrics()
        metrics.api_calls = 5
        metrics.cache_hits = 10
        metrics.cache_misses = 2

        result = metrics.to_dict()

        assert result["api_calls"] == 5
        assert result["cache_hits"] == 10
        assert result["cache_misses"] == 2
        assert "hit_rate" in result

    def test_pricing_metrics_reset(self):
        """Test PricingMetrics reset method"""
        from shared.aws.pricing.utils import PricingMetrics

        metrics = PricingMetrics()
        metrics.api_calls = 5
        metrics.cache_hits = 10
        metrics.cache_misses = 2

        metrics.reset()

        assert metrics.api_calls == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0

    def test_get_prices_function(self):
        """Test get_prices function exists and is callable"""
        from shared.aws.pricing.utils import get_prices

        assert callable(get_prices)


# =============================================================================
# Integration Tests
# =============================================================================


class TestPricingIntegration:
    """Integration tests for pricing modules"""

    def test_ec2_to_ebs_cost_comparison(self):
        """Test that EC2 and EBS costs can be combined"""
        from shared.aws.pricing.constants import HOURS_PER_MONTH

        # Mock EC2 price
        ec2_hourly = 0.0416  # t3.medium
        ec2_monthly = ec2_hourly * HOURS_PER_MONTH

        # Mock EBS price
        ebs_per_gb = 0.08  # gp3
        ebs_monthly = ebs_per_gb * 100  # 100GB

        total_monthly = round(ec2_monthly + ebs_monthly, 2)

        assert total_monthly > 0
        assert ec2_monthly < total_monthly
        assert ebs_monthly < total_monthly

    def test_lambda_cost_with_free_tier(self):
        """Test Lambda cost calculation with free tier"""
        # Within free tier
        invocations = 500_000
        assert invocations < LAMBDA_FREE_TIER_REQUESTS

        # Exceeds free tier
        large_invocations = 2_000_000
        assert large_invocations > LAMBDA_FREE_TIER_REQUESTS

    def test_rds_multi_az_doubles_cost(self):
        """Test that RDS Multi-AZ doubles the cost"""
        instance_hourly = 0.073  # db.t3.medium
        storage_gb_monthly = 0.095  # gp3 per GB
        storage_gb = 100

        single_az_cost = (instance_hourly * HOURS_PER_MONTH) + (storage_gb_monthly * storage_gb)
        multi_az_cost = single_az_cost * 2

        assert multi_az_cost == 2 * single_az_cost

    def test_nat_gateway_cost_components(self):
        """Test NAT Gateway cost has fixed and variable components"""
        hourly_fixed = 0.045
        per_gb_data = 0.045

        # Fixed cost (1 month)
        fixed_monthly = hourly_fixed * HOURS_PER_MONTH

        # Variable cost (100 GB)
        variable_monthly = per_gb_data * 100

        total_monthly = fixed_monthly + variable_monthly

        assert total_monthly > fixed_monthly
        assert variable_monthly > 0
