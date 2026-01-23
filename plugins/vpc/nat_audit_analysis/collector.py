"""
NAT Gateway 데이터 수집기

수집 항목:
- NAT Gateway 목록 (VPC, Subnet, State 등)
- CloudWatch 메트릭: BytesOutToDestination, BytesInFromSource
- 태그 정보

최적화:
- CloudWatch GetMetricData API 사용 (배치 조회)
- 기존: NAT당 6 API 호출 → 최적화: 전체 1 API 호출
- 예: 50개 NAT × 6 메트릭 = 300 API → 1 API
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from plugins.cloudwatch.common import MetricQuery, batch_get_metrics, sanitize_metric_id
from core.parallel import get_client

logger = logging.getLogger(__name__)


@dataclass
class NATGateway:
    """NAT Gateway 정보"""

    nat_gateway_id: str
    vpc_id: str
    subnet_id: str
    state: str
    region: str
    account_id: str
    account_name: str

    # 메타 정보
    public_ip: str = ""
    private_ip: str = ""
    connectivity_type: str = "public"  # public or private
    create_time: datetime | None = None
    age_days: int = 0

    # CloudWatch 메트릭 (14일간)
    bytes_out_total: float = 0.0  # BytesOutToDestination 합계
    bytes_in_total: float = 0.0  # BytesInFromSource 합계
    packets_out_total: float = 0.0
    packets_in_total: float = 0.0
    active_connection_count: float = 0.0
    connection_attempt_count: float = 0.0

    # 일별 데이터 (트렌드 분석용)
    daily_bytes_out: list[float] = field(default_factory=list)
    days_with_traffic: int = 0  # 트래픽이 있었던 날 수

    # 태그
    tags: dict[str, str] = field(default_factory=dict)
    name: str = ""

    # 비용 정보
    monthly_fixed_cost: float = 0.0
    monthly_data_cost: float = 0.0
    total_monthly_cost: float = 0.0


@dataclass
class NATAuditData:
    """NAT Gateway 감사 전체 데이터"""

    account_id: str
    account_name: str
    region: str
    nat_gateways: list[NATGateway] = field(default_factory=list)
    collected_at: datetime | None = None
    metric_period_days: int = 14


class NATCollector:
    """NAT Gateway 데이터 수집기"""

    # 메트릭 수집 기간 (일)
    METRIC_PERIOD_DAYS = 14

    def __init__(self):
        self.errors: list[str] = []

    def collect(
        self,
        session,
        account_id: str,
        account_name: str,
        region: str,
    ) -> NATAuditData:
        """NAT Gateway 데이터 수집

        Args:
            session: boto3 session
            account_id: AWS 계정 ID
            account_name: 계정 이름
            region: AWS 리전

        Returns:
            NATAuditData
        """
        data = NATAuditData(
            account_id=account_id,
            account_name=account_name,
            region=region,
            collected_at=datetime.now(timezone.utc),
            metric_period_days=self.METRIC_PERIOD_DAYS,
        )

        try:
            ec2 = get_client(session, "ec2", region_name=region)
            cloudwatch = get_client(session, "cloudwatch", region_name=region)

            # 1. NAT Gateway 목록 수집
            nat_gateways = self._collect_nat_gateways(ec2, account_id, account_name, region)

            # 2. CloudWatch 메트릭 배치 수집 (최적화)
            if nat_gateways:
                self._collect_metrics_batch(cloudwatch, nat_gateways)

            data.nat_gateways = nat_gateways

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.errors.append(f"{account_name}/{region}: {error_code}")
            logger.warning(f"NAT Gateway 수집 오류 [{account_id}/{region}]: {error_code}")

        except Exception as e:
            self.errors.append(f"{account_name}/{region}: {str(e)}")
            logger.error(f"NAT Gateway 수집 오류 [{account_id}/{region}]: {e}")

        return data

    def _collect_nat_gateways(
        self,
        ec2,
        account_id: str,
        account_name: str,
        region: str,
    ) -> list[NATGateway]:
        """NAT Gateway 목록 수집"""
        nat_gateways = []
        now = datetime.now(timezone.utc)

        try:
            paginator = ec2.get_paginator("describe_nat_gateways")

            for page in paginator.paginate():
                for nat_data in page.get("NatGateways", []):
                    nat_id = nat_data.get("NatGatewayId", "")
                    state = nat_data.get("State", "")

                    # 삭제됨/실패 상태는 건너뜀
                    if state in ("deleted", "deleting", "failed"):
                        continue

                    # 기본 정보
                    nat = NATGateway(
                        nat_gateway_id=nat_id,
                        vpc_id=nat_data.get("VpcId", ""),
                        subnet_id=nat_data.get("SubnetId", ""),
                        state=state,
                        region=region,
                        account_id=account_id,
                        account_name=account_name,
                        connectivity_type=nat_data.get("ConnectivityType", "public"),
                    )

                    # 생성 시간 및 나이
                    create_time = nat_data.get("CreateTime")
                    if create_time:
                        nat.create_time = create_time
                        nat.age_days = (now - create_time.replace(tzinfo=timezone.utc)).days

                    # IP 주소
                    addresses = nat_data.get("NatGatewayAddresses", [])
                    if addresses:
                        nat.public_ip = addresses[0].get("PublicIp", "")
                        nat.private_ip = addresses[0].get("PrivateIp", "")

                    # 태그
                    nat.tags = self._parse_tags(nat_data.get("Tags", []))
                    nat.name = nat.tags.get("Name", "")

                    nat_gateways.append(nat)

        except ClientError as e:
            self.errors.append(f"NAT Gateway 목록 조회 실패: {e}")

        return nat_gateways

    def _parse_tags(self, tags: list[dict[str, str]]) -> dict[str, str]:
        """태그 파싱"""
        return {tag.get("Key", ""): tag.get("Value", "") for tag in tags if not tag.get("Key", "").startswith("aws:")}

    def _collect_metrics_batch(self, cloudwatch, nat_gateways: list[NATGateway]) -> None:
        """CloudWatch 메트릭 배치 수집 (최적화)

        기존: NAT당 6 API 호출 → 최적화: 전체 1-2 API 호출

        수집 메트릭:
        - BytesOutToDestination: NAT를 통해 나간 바이트
        - BytesInFromSource: NAT를 통해 들어온 바이트
        - PacketsOutToDestination: 나간 패킷 수
        - PacketsInFromSource: 들어온 패킷 수
        - ActiveConnectionCount: 활성 연결 수
        - ConnectionAttemptCount: 연결 시도 수
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.METRIC_PERIOD_DAYS)

        # 모든 NAT의 메트릭 쿼리 생성
        metrics_to_fetch = [
            ("BytesOutToDestination", "bytes_out_total"),
            ("BytesInFromSource", "bytes_in_total"),
            ("PacketsOutToDestination", "packets_out_total"),
            ("PacketsInFromSource", "packets_in_total"),
            ("ActiveConnectionCount", "active_connection_count"),
            ("ConnectionAttemptCount", "connection_attempt_count"),
        ]

        queries = []
        for nat in nat_gateways:
            safe_id = sanitize_metric_id(nat.nat_gateway_id)
            for metric_name, _ in metrics_to_fetch:
                metric_key = metric_name.lower()
                queries.append(
                    MetricQuery(
                        id=f"{safe_id}_{metric_key}",
                        namespace="AWS/NATGateway",
                        metric_name=metric_name,
                        dimensions={"NatGatewayId": nat.nat_gateway_id},
                        stat="Sum",
                    )
                )

        # 배치 조회
        try:
            results = batch_get_metrics(cloudwatch, queries, start_time, end_time, period=86400)

            # 결과 매핑
            for nat in nat_gateways:
                safe_id = sanitize_metric_id(nat.nat_gateway_id)

                for metric_name, attr_name in metrics_to_fetch:
                    metric_key = metric_name.lower()
                    value = results.get(f"{safe_id}_{metric_key}", 0.0)
                    setattr(nat, attr_name, value)

                # days_with_traffic는 BytesOut 기반으로 추정
                # (정확한 일별 데이터는 별도 조회 필요)
                if nat.bytes_out_total > 0:
                    # 트래픽이 있으면 일부 날에 트래픽이 있었다고 가정
                    nat.days_with_traffic = min(self.METRIC_PERIOD_DAYS, max(1, int(nat.bytes_out_total / (1024 * 1024))))
                else:
                    nat.days_with_traffic = 0

        except ClientError as e:
            logger.warning(f"NAT 메트릭 배치 조회 실패: {e}")
            # 실패 시 개별 조회로 폴백
            for nat in nat_gateways:
                self._collect_metrics_single(cloudwatch, nat, start_time, end_time, metrics_to_fetch)

        # 비용 계산
        for nat in nat_gateways:
            self._calculate_costs(nat)

    def _collect_metrics_single(
        self,
        cloudwatch,
        nat: NATGateway,
        start_time: datetime,
        end_time: datetime,
        metrics_to_fetch: list[tuple[str, str]],
    ) -> None:
        """단일 NAT의 메트릭 수집 (폴백용)"""
        dimensions = [{"Name": "NatGatewayId", "Value": nat.nat_gateway_id}]

        for metric_name, attr_name in metrics_to_fetch:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace="AWS/NATGateway",
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=["Sum"],
                )

                datapoints = response.get("Datapoints", [])

                if datapoints:
                    total = sum(dp.get("Sum", 0) for dp in datapoints)
                    setattr(nat, attr_name, total)

                    if metric_name == "BytesOutToDestination":
                        sorted_points = sorted(datapoints, key=lambda x: x["Timestamp"])
                        nat.daily_bytes_out = [dp.get("Sum", 0) for dp in sorted_points]
                        nat.days_with_traffic = sum(1 for dp in datapoints if dp.get("Sum", 0) > 0)

            except ClientError as e:
                logger.debug(f"메트릭 조회 실패 [{nat.nat_gateway_id}/{metric_name}]: {e}")

        # 비용 계산
        self._calculate_costs(nat)

    def _calculate_costs(self, nat: NATGateway) -> None:
        """비용 계산"""
        from plugins.cost.pricing import get_nat_data_price, get_nat_monthly_fixed_cost

        # 월간 고정 비용
        nat.monthly_fixed_cost = get_nat_monthly_fixed_cost(nat.region)

        # 데이터 처리 비용 (14일 데이터를 월간으로 환산)
        if nat.bytes_out_total > 0:
            daily_avg_gb = (nat.bytes_out_total / (1024**3)) / self.METRIC_PERIOD_DAYS
            monthly_gb = daily_avg_gb * 30
            data_price = get_nat_data_price(nat.region)
            nat.monthly_data_cost = round(monthly_gb * data_price, 2)

        nat.total_monthly_cost = round(nat.monthly_fixed_cost + nat.monthly_data_cost, 2)
