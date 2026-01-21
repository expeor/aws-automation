"""
tests/plugins/cost/pricing/conftest.py - Pricing 테스트 공통 fixtures
"""

import pytest


@pytest.fixture
def sample_ec2_prices():
    """샘플 EC2 가격 데이터"""
    return {
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "t3.large": 0.0832,
        "m5.large": 0.096,
    }


@pytest.fixture
def sample_ebs_prices():
    """샘플 EBS 가격 데이터"""
    return {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.025,
    }


@pytest.fixture
def sample_sagemaker_prices():
    """샘플 SageMaker 가격 데이터"""
    return {
        "ml.t3.medium": 0.0416,
        "ml.m5.large": 0.115,
        "ml.c5.xlarge": 0.204,
        "ml.g4dn.xlarge": 0.736,
    }


@pytest.fixture
def sample_lambda_prices():
    """샘플 Lambda 가격 데이터"""
    return {
        "request_per_million": 0.20,
        "duration_per_gb_second": 0.0000166667,
        "provisioned_concurrency_per_gb_hour": 0.000004646,
    }


@pytest.fixture
def sample_dynamodb_prices():
    """샘플 DynamoDB 가격 데이터"""
    return {
        "rcu_per_hour": 0.00013,
        "wcu_per_hour": 0.00065,
        "read_per_million": 0.25,
        "write_per_million": 1.25,
        "storage_per_gb": 0.25,
    }
