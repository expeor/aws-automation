"""
tests/analyzers/vpc/test_vpc_tools.py - VPC Analyzer Tools 테스트

VPC 관련 도구의 유틸리티 함수 및 데이터 변환 로직 테스트
"""

from datetime import datetime, timezone
from unittest.mock import patch

from analyzers.vpc.endpoint_audit import (
    EndpointStatus,
    VPCEndpointInfo,
    analyze_endpoints,
)
from analyzers.vpc.eni_audit import (
    ENIInfo,
    Severity,
    UsageStatus,
    _analyze_single_eni,
    analyze_enis,
)


class TestENIAnalysis:
    """ENI (Elastic Network Interface) 분석 테스트"""

    def test_eni_info_is_attached(self):
        """ENI 연결 여부 테스트"""
        # 연결됨
        eni_attached = ENIInfo(
            id="eni-123",
            description="test-eni",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="i-123",
            attachment_status="attached",
            security_groups=["sg-123"],
            tags={},
            name="test-eni",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni_attached.is_attached is True

        # 미연결
        eni_available = ENIInfo(
            id="eni-456",
            description="unused-eni",
            status="available",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.2",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=["sg-123"],
            tags={},
            name="unused-eni",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni_available.is_attached is False

    def test_eni_info_is_aws_managed_by_requester(self):
        """AWS 관리형 ENI 식별 - requester_id 기반"""
        # 다른 requester_id = AWS 관리형
        eni = ENIInfo(
            id="eni-nat",
            description="NAT Gateway ENI",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="",
            interface_type="interface",
            requester_id="amazon-nat",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=[],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni.is_aws_managed is True

    def test_eni_info_is_aws_managed_by_type(self):
        """AWS 관리형 ENI 식별 - interface_type 기반"""
        # NAT Gateway ENI
        eni_nat = ENIInfo(
            id="eni-nat",
            description="NAT Gateway",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="",
            interface_type="nat_gateway",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=[],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni_nat.is_aws_managed is True

        # Lambda ENI
        eni_lambda = ENIInfo(
            id="eni-lambda",
            description="Lambda ENI",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.2",
            public_ip="",
            interface_type="lambda",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=[],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni_lambda.is_aws_managed is True

        # VPC Endpoint ENI
        eni_endpoint = ENIInfo(
            id="eni-endpoint",
            description="VPC Endpoint",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.3",
            public_ip="",
            interface_type="vpc_endpoint",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=[],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eni_endpoint.is_aws_managed is True

    def test_analyze_single_eni_aws_managed(self):
        """AWS 관리형 ENI 분석"""
        eni = ENIInfo(
            id="eni-nat",
            description="NAT Gateway ENI",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="",
            interface_type="nat_gateway",
            requester_id="amazon-nat",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=[],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eni(eni)

        assert finding.usage_status == UsageStatus.AWS_MANAGED
        assert finding.severity == Severity.INFO
        assert "AWS 관리형" in finding.description
        assert "삭제하지 마세요" in finding.recommendation

    def test_analyze_single_eni_normal(self):
        """정상 사용 ENI 분석"""
        eni = ENIInfo(
            id="eni-123",
            description="Instance ENI",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="1.2.3.4",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="i-123",
            attachment_status="attached",
            security_groups=["sg-123"],
            tags={},
            name="web-server-eni",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eni(eni)

        assert finding.usage_status == UsageStatus.NORMAL
        assert finding.severity == Severity.INFO
        assert "사용 중" in finding.description

    def test_analyze_single_eni_unused(self):
        """미사용 ENI 분석"""
        eni = ENIInfo(
            id="eni-unused",
            description="Unused ENI",
            status="available",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.5",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=["sg-123"],
            tags={},
            name="unused",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eni(eni)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.HIGH
        assert "미사용" in finding.description
        assert "삭제 검토" in finding.recommendation

    def test_analyze_single_eni_efs_related(self):
        """EFS 관련 ENI 분석 (주의 필요)"""
        eni = ENIInfo(
            id="eni-efs",
            description="EFS mount target for fs-123",
            status="available",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.10",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=["sg-123"],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eni(eni)

        assert finding.usage_status == UsageStatus.PENDING
        assert finding.severity == Severity.LOW
        assert "EFS" in finding.description

    def test_analyze_single_eni_elb_related(self):
        """Load Balancer 관련 ENI 분석 (주의 필요)"""
        eni = ENIInfo(
            id="eni-elb",
            description="ELB app/my-alb/123456789",
            status="available",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.20",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="",
            attachment_status="",
            security_groups=["sg-123"],
            tags={},
            name="",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eni(eni)

        assert finding.usage_status == UsageStatus.PENDING
        assert finding.severity == Severity.LOW
        assert "Load Balancer" in finding.description

    def test_analyze_enis_summary(self):
        """ENI 분석 종합 테스트"""
        enis = [
            ENIInfo(
                id="eni-1",
                description="Normal",
                status="in-use",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                availability_zone="ap-northeast-2a",
                private_ip="10.0.0.1",
                public_ip="",
                interface_type="interface",
                requester_id="123456789012",
                owner_id="123456789012",
                instance_id="i-123",
                attachment_status="attached",
                security_groups=["sg-123"],
                tags={},
                name="",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            ),
            ENIInfo(
                id="eni-2",
                description="Unused",
                status="available",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                availability_zone="ap-northeast-2a",
                private_ip="10.0.0.2",
                public_ip="",
                interface_type="interface",
                requester_id="123456789012",
                owner_id="123456789012",
                instance_id="",
                attachment_status="",
                security_groups=["sg-123"],
                tags={},
                name="",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            ),
            ENIInfo(
                id="eni-3",
                description="NAT Gateway",
                status="in-use",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                availability_zone="ap-northeast-2a",
                private_ip="10.0.0.3",
                public_ip="",
                interface_type="nat_gateway",
                requester_id="amazon-nat",
                owner_id="123456789012",
                instance_id="",
                attachment_status="",
                security_groups=[],
                tags={},
                name="",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            ),
            ENIInfo(
                id="eni-4",
                description="EFS mount target",
                status="available",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                availability_zone="ap-northeast-2a",
                private_ip="10.0.0.4",
                public_ip="",
                interface_type="interface",
                requester_id="123456789012",
                owner_id="123456789012",
                instance_id="",
                attachment_status="",
                security_groups=["sg-123"],
                tags={},
                name="",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            ),
        ]

        result = analyze_enis(enis, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 4
        assert result.normal_count == 1
        assert result.unused_count == 1
        assert result.aws_managed_count == 1
        assert result.pending_count == 1


class TestVPCEndpointAnalysis:
    """VPC Endpoint 분석 테스트"""

    def test_vpc_endpoint_is_interface(self):
        """VPC Endpoint 타입 확인 - Interface"""
        endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-123",
            endpoint_type="Interface",
            service_name="com.amazonaws.ap-northeast-2.s3",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="s3-endpoint",
        )
        assert endpoint.is_interface is True

        # Gateway Endpoint
        gateway_endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-456",
            endpoint_type="Gateway",
            service_name="com.amazonaws.ap-northeast-2.s3",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="s3-gateway",
        )
        assert gateway_endpoint.is_interface is False

    def test_vpc_endpoint_monthly_cost(self):
        """VPC Endpoint 비용 계산"""
        with patch("analyzers.vpc.endpoint_audit.get_endpoint_monthly_cost", return_value=7.2):
            # Interface Endpoint (유료)
            interface_endpoint = VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-123",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.ec2",
                vpc_id="vpc-123",
                state="available",
                creation_time=datetime.now(timezone.utc),
                name="ec2-endpoint",
            )
            assert interface_endpoint.monthly_cost == 7.2

        # Gateway Endpoint (무료)
        gateway_endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-456",
            endpoint_type="Gateway",
            service_name="com.amazonaws.ap-northeast-2.s3",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="s3-gateway",
        )
        assert gateway_endpoint.monthly_cost == 0.0

    def test_analyze_endpoints_gateway(self):
        """Gateway Endpoint 분석 (무료)"""
        endpoints = [
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-gateway",
                endpoint_type="Gateway",
                service_name="com.amazonaws.ap-northeast-2.s3",
                vpc_id="vpc-123",
                state="available",
                creation_time=datetime.now(timezone.utc),
                name="s3-gateway",
            )
        ]

        from unittest.mock import MagicMock

        mock_session = MagicMock()
        result = analyze_endpoints(endpoints, mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 1
        assert result.gateway_count == 1
        assert result.interface_count == 0
        assert result.normal_count == 1
        assert result.unused_count == 0
        assert result.unused_monthly_cost == 0.0

    def test_analyze_endpoints_interface_normal(self):
        """Interface Endpoint 정상 분석"""
        endpoints = [
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-interface",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.ec2",
                vpc_id="vpc-123",
                state="available",
                creation_time=datetime.now(timezone.utc),
                name="ec2-endpoint",
            )
        ]

        from unittest.mock import MagicMock

        mock_session = MagicMock()
        result = analyze_endpoints(endpoints, mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 1
        assert result.interface_count == 1
        assert result.normal_count == 1
        assert result.unused_count == 0

    def test_analyze_endpoints_pending(self):
        """Pending 상태 Endpoint 분석"""
        endpoints = [
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-pending",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.ec2",
                vpc_id="vpc-123",
                state="pending",
                creation_time=datetime.now(timezone.utc),
                name="pending-endpoint",
            )
        ]

        from unittest.mock import MagicMock

        mock_session = MagicMock()
        result = analyze_endpoints(endpoints, mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 1
        assert result.interface_count == 1
        assert len(result.findings) == 1
        assert result.findings[0].status == EndpointStatus.PENDING

    def test_analyze_endpoints_failed(self):
        """Failed 상태 Endpoint 분석"""
        endpoints = [
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-failed",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.ec2",
                vpc_id="vpc-123",
                state="failed",
                creation_time=datetime.now(timezone.utc),
                name="failed-endpoint",
            )
        ]

        from unittest.mock import MagicMock

        mock_session = MagicMock()

        with patch("analyzers.vpc.endpoint_audit.get_endpoint_monthly_cost", return_value=7.2):
            result = analyze_endpoints(endpoints, mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 1
        assert result.interface_count == 1
        assert result.unused_count == 1
        assert result.unused_monthly_cost == 7.2
        assert len(result.findings) == 1
        assert result.findings[0].status == EndpointStatus.UNUSED

    def test_analyze_endpoints_mixed(self):
        """혼합 Endpoint 분석"""
        endpoints = [
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-gateway",
                endpoint_type="Gateway",
                service_name="com.amazonaws.ap-northeast-2.s3",
                vpc_id="vpc-123",
                state="available",
                creation_time=datetime.now(timezone.utc),
                name="s3-gateway",
            ),
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-normal",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.ec2",
                vpc_id="vpc-123",
                state="available",
                creation_time=datetime.now(timezone.utc),
                name="ec2-endpoint",
            ),
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-pending",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.s3",
                vpc_id="vpc-123",
                state="pending",
                creation_time=datetime.now(timezone.utc),
                name="s3-pending",
            ),
            VPCEndpointInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                endpoint_id="vpce-failed",
                endpoint_type="Interface",
                service_name="com.amazonaws.ap-northeast-2.lambda",
                vpc_id="vpc-123",
                state="failed",
                creation_time=datetime.now(timezone.utc),
                name="lambda-failed",
            ),
        ]

        from unittest.mock import MagicMock

        mock_session = MagicMock()

        with patch("analyzers.vpc.endpoint_audit.get_endpoint_monthly_cost", return_value=7.2):
            result = analyze_endpoints(endpoints, mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 4
        assert result.gateway_count == 1
        assert result.interface_count == 3
        assert result.normal_count == 2  # gateway + 1 available interface
        assert result.unused_count == 1  # failed
        assert result.unused_monthly_cost == 7.2


class TestVPCUtilityFunctions:
    """VPC 유틸리티 함수 테스트"""

    def test_eni_security_groups_parsing(self):
        """ENI 보안 그룹 파싱 테스트"""
        eni = ENIInfo(
            id="eni-123",
            description="test",
            status="in-use",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            availability_zone="ap-northeast-2a",
            private_ip="10.0.0.1",
            public_ip="",
            interface_type="interface",
            requester_id="123456789012",
            owner_id="123456789012",
            instance_id="i-123",
            attachment_status="attached",
            security_groups=["sg-123", "sg-456", "sg-789"],
            tags={"Name": "web-server", "Environment": "prod"},
            name="web-server",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        assert len(eni.security_groups) == 3
        assert "sg-123" in eni.security_groups
        assert eni.tags["Environment"] == "prod"

    def test_endpoint_service_name_parsing(self):
        """Endpoint 서비스 이름 파싱 테스트"""
        # S3 Endpoint
        s3_endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-s3",
            endpoint_type="Gateway",
            service_name="com.amazonaws.ap-northeast-2.s3",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="s3",
        )
        assert "s3" in s3_endpoint.service_name

        # EC2 Endpoint
        ec2_endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-ec2",
            endpoint_type="Interface",
            service_name="com.amazonaws.ap-northeast-2.ec2",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="ec2",
        )
        assert "ec2" in ec2_endpoint.service_name

        # Lambda Endpoint
        lambda_endpoint = VPCEndpointInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            endpoint_id="vpce-lambda",
            endpoint_type="Interface",
            service_name="com.amazonaws.ap-northeast-2.lambda",
            vpc_id="vpc-123",
            state="available",
            creation_time=datetime.now(timezone.utc),
            name="lambda",
        )
        assert "lambda" in lambda_endpoint.service_name
