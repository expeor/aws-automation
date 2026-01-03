"""
plugins/cost/pricing/fetcher.py - AWS 가격 정보 가져오기

AWS Pricing API (get_products)를 사용하여 리전별 가격을 조회합니다.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Dict, Optional

from botocore.exceptions import BotoCoreError, ClientError

from core.parallel import get_client

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)

# Pricing API는 us-east-1에서만 사용 가능
PRICING_API_REGION = "us-east-1"


class PricingFetcher:
    """AWS 가격 정보 가져오기 (Pricing API)

    get_products API로 리전별 가격을 조회합니다.
    """

    def __init__(self, session: Optional["boto3.Session"] = None):
        """
        Args:
            session: boto3 세션 (None이면 기본 세션 사용)
        """
        import boto3 as _boto3
        from botocore.exceptions import BotoCoreError, ClientError

        self._BotoCoreError = BotoCoreError
        self._ClientError = ClientError
        self.session = session or _boto3.Session()
        self._pricing_client = None

    @property
    def pricing_client(self):
        """Pricing API 클라이언트 (지연 생성)"""
        if self._pricing_client is None:
            self._pricing_client = get_client(
                self.session, "pricing", region_name=PRICING_API_REGION
            )
        return self._pricing_client

    def get_ec2_prices(self, region: str) -> Dict[str, float]:
        """EC2 인스턴스 가격 조회 (get_products API 사용)

        Args:
            region: AWS 리전 코드 (예: ap-northeast-2)

        Returns:
            {instance_type: hourly_price} 딕셔너리
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "operatingSystem",
                        "Value": "Linux",
                    },
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                    {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                ],
                MaxResults=100,
            )

            prices = {}
            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                instance_type = attrs.get("instanceType", "")
                if not instance_type:
                    continue

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            prices[instance_type] = price
                            break

            logger.info(f"EC2 가격 조회 완료: {region} ({len(prices)} types)")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"EC2 가격 조회 실패 [{region}]: {e}")
            return {}

    def get_ebs_prices(self, region: str) -> Dict[str, float]:
        """EBS 볼륨 가격 조회 (get_products API 사용)

        Args:
            region: AWS 리전 코드

        Returns:
            {volume_type: gb_monthly_price} 딕셔너리
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "productFamily",
                        "Value": "Storage",
                    },
                ],
                MaxResults=100,
            )

            prices = {}
            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                volume_type = attrs.get("volumeApiName", "")
                if not volume_type:
                    continue

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            prices[volume_type] = price
                            break

            logger.info(f"EBS 가격 조회 완료: {region} ({len(prices)} types)")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"EBS 가격 조회 실패 [{region}]: {e}")
            return {
                "gp3": 0.08,
                "gp2": 0.10,
                "io1": 0.125,
                "io2": 0.125,
                "st1": 0.045,
                "sc1": 0.025,
                "standard": 0.05,
            }

    def get_vpc_endpoint_prices(self, region: str) -> Dict[str, float]:
        """VPC Endpoint 가격 조회 (Pricing API 사용)

        Args:
            region: AWS 리전 코드

        Returns:
            {"interface_hourly": float, "gateway_hourly": float, "data_per_gb": float}
        """
        try:
            # Interface Endpoint 시간당 가격
            interface_response = self.pricing_client.get_products(
                ServiceCode="AmazonVPC",
                Filters=[
                    {
                        "Type": "TERM_MATCH",
                        "Field": "productFamily",
                        "Value": "VpcEndpoint",
                    },
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "endpointType",
                        "Value": "Interface",
                    },
                ],
                MaxResults=10,
            )

            prices = {
                "interface_hourly": 0.0,
                "gateway_hourly": 0.0,
                "data_per_gb": 0.0,
            }

            for price_item in interface_response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                terms = data.get("terms", {}).get("OnDemand", {})
                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        unit = dim.get("unit", "").lower()
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if "hr" in unit or "hour" in unit:
                            prices["interface_hourly"] = price
                        elif "gb" in unit:
                            prices["data_per_gb"] = price

            # Gateway Endpoint는 무료
            prices["gateway_hourly"] = 0.0

            logger.info(f"VPC Endpoint 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"VPC Endpoint 가격 조회 실패 [{region}]: {e}")
            return {
                "interface_hourly": 0.01,
                "gateway_hourly": 0.0,
                "data_per_gb": 0.01,
            }

    def get_secrets_manager_prices(self, region: str) -> Dict[str, float]:
        """Secrets Manager 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"per_secret_monthly": float, "per_10k_api_calls": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AWSSecretsManager",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=10,
            )

            prices = {"per_secret_monthly": 0.0, "per_10k_api_calls": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "secret" in usage_type:
                                prices["per_secret_monthly"] = price
                            elif "api" in usage_type:
                                prices["per_10k_api_calls"] = price

            logger.info(f"Secrets Manager 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Secrets Manager 가격 조회 실패 [{region}]: {e}")
            return {"per_secret_monthly": 0.40, "per_10k_api_calls": 0.05}

    def get_kms_prices(self, region: str) -> Dict[str, float]:
        """KMS 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"customer_key_monthly": float, "per_10k_requests": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="awskms",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=20,
            )

            prices = {"customer_key_monthly": 0.0, "per_10k_requests": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()
                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "keys" in group or "key" in usage_type:
                                prices["customer_key_monthly"] = price
                            elif "request" in usage_type:
                                prices["per_10k_requests"] = price

            logger.info(f"KMS 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"KMS 가격 조회 실패 [{region}]: {e}")
            return {"customer_key_monthly": 1.0, "per_10k_requests": 0.03}

    def get_ecr_prices(self, region: str) -> Dict[str, float]:
        """ECR 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"storage_per_gb_monthly": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonECR",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=10,
            )

            prices = {"storage_per_gb_monthly": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0 and "storage" in usage_type:
                            prices["storage_per_gb_monthly"] = price

            logger.info(f"ECR 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"ECR 가격 조회 실패 [{region}]: {e}")
            return {"storage_per_gb_monthly": 0.10}

    def get_route53_prices(self) -> Dict[str, float]:
        """Route53 가격 조회 (글로벌 서비스)

        Returns:
            {"hosted_zone_monthly": float, "additional_zone_monthly": float, "query_per_million": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonRoute53",
                Filters=[],
                MaxResults=20,
            )

            prices = {
                "hosted_zone_monthly": 0.0,
                "additional_zone_monthly": 0.0,
                "query_per_million": 0.0,
            }

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                group = attrs.get("group", "").lower()
                group_desc = attrs.get("groupDescription", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        desc = dim.get("description", "").lower()
                        if price > 0:
                            if "hosted zone" in desc or "zone" in group:
                                if (
                                    "first 25" in desc
                                    or prices["hosted_zone_monthly"] == 0
                                ):
                                    prices["hosted_zone_monthly"] = price
                                else:
                                    prices["additional_zone_monthly"] = price
                            elif "query" in desc or "queries" in group:
                                prices["query_per_million"] = price

            logger.info("Route53 가격 조회 완료")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Route53 가격 조회 실패: {e}")
            return {
                "hosted_zone_monthly": 0.50,
                "additional_zone_monthly": 0.10,
                "query_per_million": 0.40,
            }

    def get_snapshot_prices(self, region: str) -> Dict[str, float]:
        """EBS Snapshot 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"storage_per_gb_monthly": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "productFamily",
                        "Value": "Storage Snapshot",
                    },
                ],
                MaxResults=10,
            )

            prices = {"storage_per_gb_monthly": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                terms = data.get("terms", {}).get("OnDemand", {})

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            prices["storage_per_gb_monthly"] = price
                            break

            logger.info(f"EBS Snapshot 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"EBS Snapshot 가격 조회 실패 [{region}]: {e}")
            return {"storage_per_gb_monthly": 0.05}

    def get_eip_prices(self, region: str) -> Dict[str, float]:
        """Elastic IP 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"unused_hourly": float, "additional_hourly": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "productFamily",
                        "Value": "IP Address",
                    },
                ],
                MaxResults=10,
            )

            prices = {"unused_hourly": 0.0, "additional_hourly": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "not attached" in group or "idle" in group:
                                prices["unused_hourly"] = price
                            else:
                                prices["additional_hourly"] = price

            logger.info(f"EIP 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"EIP 가격 조회 실패 [{region}]: {e}")
            return {"unused_hourly": 0.005, "additional_hourly": 0.005}

    def get_elb_prices(self, region: str) -> Dict[str, float]:
        """ELB 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"alb_hourly": float, "nlb_hourly": float, "glb_hourly": float, "clb_hourly": float}
        """
        try:
            prices = {
                "alb_hourly": 0.0,
                "nlb_hourly": 0.0,
                "glb_hourly": 0.0,
                "clb_hourly": 0.0,
            }

            # ELBv2 (ALB, NLB, GLB)
            response = self.pricing_client.get_products(
                ServiceCode="AWSELB",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=50,
            )

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()
                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        unit = dim.get("unit", "").lower()
                        if "hr" not in unit and "hour" not in unit:
                            continue
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "application" in usage_type or "alb" in group:
                                prices["alb_hourly"] = price
                            elif "network" in usage_type or "nlb" in group:
                                prices["nlb_hourly"] = price
                            elif "gateway" in usage_type or "glb" in group:
                                prices["glb_hourly"] = price
                            elif "classic" in usage_type or "elb-" in usage_type:
                                prices["clb_hourly"] = price

            logger.info(f"ELB 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"ELB 가격 조회 실패 [{region}]: {e}")
            return {
                "alb_hourly": 0.0225,
                "nlb_hourly": 0.0225,
                "glb_hourly": 0.0125,
                "clb_hourly": 0.025,
            }

    def get_rds_snapshot_prices(self, region: str) -> Dict[str, float]:
        """RDS Snapshot 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"rds_per_gb_monthly": float, "aurora_per_gb_monthly": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonRDS",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {
                        "Type": "TERM_MATCH",
                        "Field": "productFamily",
                        "Value": "Storage Snapshot",
                    },
                ],
                MaxResults=20,
            )

            prices = {"rds_per_gb_monthly": 0.0, "aurora_per_gb_monthly": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                db_engine = attrs.get("databaseEngine", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "aurora" in db_engine:
                                prices["aurora_per_gb_monthly"] = price
                            else:
                                prices["rds_per_gb_monthly"] = price

            logger.info(f"RDS Snapshot 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"RDS Snapshot 가격 조회 실패 [{region}]: {e}")
            return {"rds_per_gb_monthly": 0.02, "aurora_per_gb_monthly": 0.021}

    def get_cloudwatch_prices(self, region: str) -> Dict[str, float]:
        """CloudWatch Logs 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {"storage_per_gb_monthly": float, "ingestion_per_gb": float}
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonCloudWatch",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=30,
            )

            prices = {"storage_per_gb_monthly": 0.0, "ingestion_per_gb": 0.0}

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()
                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            if "storage" in usage_type or "archive" in group:
                                prices["storage_per_gb_monthly"] = price
                            elif "dataprocessing" in usage_type or "ingestion" in group:
                                prices["ingestion_per_gb"] = price

            logger.info(f"CloudWatch 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"CloudWatch 가격 조회 실패 [{region}]: {e}")
            return {"storage_per_gb_monthly": 0.03, "ingestion_per_gb": 0.50}

    def get_lambda_prices(self, region: str) -> Dict[str, float]:
        """Lambda 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {
                "request_per_million": float,      # 100만 요청당 가격
                "duration_per_gb_second": float,   # GB-초당 가격
                "provisioned_concurrency_per_gb_hour": float,  # Provisioned Concurrency GB-시간당
            }
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AWSLambda",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=50,
            )

            prices = {
                "request_per_million": 0.0,
                "duration_per_gb_second": 0.0,
                "provisioned_concurrency_per_gb_hour": 0.0,
            }

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()
                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        desc = dim.get("description", "").lower()
                        if price > 0:
                            if "request" in usage_type or "request" in desc:
                                prices["request_per_million"] = price
                            elif "provisioned" in usage_type or "provisioned" in group:
                                prices["provisioned_concurrency_per_gb_hour"] = price
                            elif "duration" in usage_type or "gb-second" in desc:
                                prices["duration_per_gb_second"] = price

            logger.info(f"Lambda 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Lambda 가격 조회 실패 [{region}]: {e}")
            # 기본값 (ap-northeast-2 기준)
            return {
                "request_per_million": 0.20,
                "duration_per_gb_second": 0.0000166667,
                "provisioned_concurrency_per_gb_hour": 0.000004646,
            }

    def get_dynamodb_prices(self, region: str) -> Dict[str, float]:
        """DynamoDB 가격 조회

        Args:
            region: AWS 리전 코드

        Returns:
            {
                "rcu_per_hour": float,          # RCU 시간당 가격 (Provisioned)
                "wcu_per_hour": float,          # WCU 시간당 가격 (Provisioned)
                "read_per_million": float,      # 읽기 100만 요청당 가격 (On-Demand)
                "write_per_million": float,     # 쓰기 100만 요청당 가격 (On-Demand)
                "storage_per_gb": float,        # 스토리지 GB당 월간 가격
            }
        """
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonDynamoDB",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
                MaxResults=100,
            )

            prices = {
                "rcu_per_hour": 0.0,
                "wcu_per_hour": 0.0,
                "read_per_million": 0.0,
                "write_per_million": 0.0,
                "storage_per_gb": 0.0,
            }

            for price_item in response.get("PriceList", []):
                data = (
                    json.loads(price_item)
                    if isinstance(price_item, str)
                    else price_item
                )
                attrs = data.get("product", {}).get("attributes", {})
                terms = data.get("terms", {}).get("OnDemand", {})

                usage_type = attrs.get("usagetype", "").lower()
                group = attrs.get("group", "").lower()

                for term in terms.values():
                    for dim in term.get("priceDimensions", {}).values():
                        price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                        if price > 0:
                            # Provisioned Capacity
                            if "readcapacityunit" in usage_type:
                                prices["rcu_per_hour"] = price
                            elif "writecapacityunit" in usage_type:
                                prices["wcu_per_hour"] = price
                            # On-Demand
                            elif "readrequestunits" in usage_type:
                                prices["read_per_million"] = price * 1_000_000
                            elif "writerequestunits" in usage_type:
                                prices["write_per_million"] = price * 1_000_000
                            # Storage
                            elif "timeddatasize" in usage_type or "storage" in group:
                                prices["storage_per_gb"] = price

            logger.info(f"DynamoDB 가격 조회 완료: {region}")
            return prices

        except (ClientError, BotoCoreError) as e:
            logger.warning(f"DynamoDB 가격 조회 실패 [{region}]: {e}")
            # 기본값 (ap-northeast-2 기준)
            return {
                "rcu_per_hour": 0.00013,
                "wcu_per_hour": 0.00065,
                "read_per_million": 0.25,
                "write_per_million": 1.25,
                "storage_per_gb": 0.25,
            }
