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

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from core.parallel import get_client
from core.shared.aws.metrics import MetricQuery, batch_get_metrics, sanitize_metric_id

logger = logging.getLogger(__name__)


@dataclass
class NATGateway:
    """NAT Gateway 리소스의 상세 정보를 담는 데이터 클래스.

    EC2 API에서 조회한 기본 정보와 CloudWatch 메트릭, 비용 정보를 통합하여
    미사용/저사용 분석에 필요한 데이터를 제공한다.

    Attributes:
        nat_gateway_id: NAT Gateway 식별자 (예: ``nat-0123456789abcdef0``).
        vpc_id: NAT Gateway가 속한 VPC ID.
        subnet_id: NAT Gateway가 배치된 서브넷 ID.
        state: NAT Gateway 상태 (``available``, ``pending``, ``deleting`` 등).
        region: AWS 리전 코드.
        account_id: AWS 계정 ID.
        account_name: 계정 표시 이름.
        public_ip: 퍼블릭 Elastic IP 주소.
        private_ip: 프라이빗 IP 주소.
        connectivity_type: 연결 유형 (``public`` 또는 ``private``).
        create_time: 생성 시각 (UTC).
        age_days: 생성 후 경과 일수.
        bytes_out_total: 분석 기간 동안 BytesOutToDestination 합계.
        bytes_in_total: 분석 기간 동안 BytesInFromSource 합계.
        packets_out_total: 분석 기간 동안 PacketsOutToDestination 합계.
        packets_in_total: 분석 기간 동안 PacketsInFromSource 합계.
        active_connection_count: 분석 기간 동안 ActiveConnectionCount 합계.
        connection_attempt_count: 분석 기간 동안 ConnectionAttemptCount 합계.
        daily_bytes_out: 일별 아웃바운드 바이트 리스트 (트렌드 분석용).
        days_with_traffic: 분석 기간 중 트래픽이 발생한 날 수.
        tags: AWS 태그 딕셔너리 (``aws:`` 접두사 태그 제외).
        name: Name 태그 값.
        monthly_fixed_cost: NAT Gateway 월간 고정 비용 (USD).
        monthly_data_cost: 데이터 처리 기반 월간 비용 추정 (USD).
        total_monthly_cost: 월간 총 비용 추정 (고정 + 데이터, USD).
    """

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
    """단일 계정/리전에서 수집한 NAT Gateway 감사 데이터 컨테이너.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: 계정 표시 이름.
        region: AWS 리전 코드.
        nat_gateways: 수집된 NAT Gateway 목록.
        collected_at: 데이터 수집 시각 (UTC).
        metric_period_days: CloudWatch 메트릭 수집 기간 (일).
    """

    account_id: str
    account_name: str
    region: str
    nat_gateways: list[NATGateway] = field(default_factory=list)
    collected_at: datetime | None = None
    metric_period_days: int = 14


class NATCollector:
    """NAT Gateway 데이터 수집기.

    EC2 API로 NAT Gateway 목록을 조회하고, CloudWatch GetMetricData API를
    배치 호출하여 트래픽 메트릭을 수집한다. 배치 조회로 API 호출을 최소화한다.
    """

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
        """EC2 API로 NAT Gateway 목록을 수집한다.

        ``deleted``, ``deleting``, ``failed`` 상태의 NAT Gateway는 제외한다.

        Args:
            ec2: boto3 EC2 client (rate limiting 적용).
            account_id: AWS 계정 ID.
            account_name: 계정 표시 이름.
            region: AWS 리전 코드.

        Returns:
            수집된 NATGateway 목록.
        """
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
        """AWS 태그 리스트를 딕셔너리로 변환한다. ``aws:`` 접두사 태그는 제외."""
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
                    nat.days_with_traffic = min(
                        self.METRIC_PERIOD_DAYS, max(1, int(nat.bytes_out_total / (1024 * 1024)))
                    )
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
        """단일 NAT Gateway의 메트릭을 개별 API 호출로 수집한다 (배치 실패 시 폴백)."""
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
        """NAT Gateway의 월간 고정 비용과 데이터 처리 비용을 계산한다."""
        from core.shared.aws.pricing import get_nat_data_price, get_nat_monthly_fixed_cost

        # 월간 고정 비용
        nat.monthly_fixed_cost = get_nat_monthly_fixed_cost(nat.region)

        # 데이터 처리 비용 (14일 데이터를 월간으로 환산)
        if nat.bytes_out_total > 0:
            daily_avg_gb = (nat.bytes_out_total / (1024**3)) / self.METRIC_PERIOD_DAYS
            monthly_gb = daily_avg_gb * 30
            data_price = get_nat_data_price(nat.region)
            nat.monthly_data_cost = round(monthly_gb * data_price, 2)

        nat.total_monthly_cost = round(nat.monthly_fixed_cost + nat.monthly_data_cost, 2)
