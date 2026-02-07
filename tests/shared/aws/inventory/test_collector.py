"""
tests/shared/aws/inventory/test_collector.py - InventoryCollector 테스트

InventoryCollector 클래스의 초기화, 리소스 수집, 캐싱, 에러 처리를 검증합니다.
"""

from unittest.mock import Mock, patch

from shared.aws.inventory.collector import InventoryCollector
from shared.aws.inventory.types import (
    VPC,
    EBSVolume,
    EC2Instance,
    LambdaFunction,
    LoadBalancer,
    RDSInstance,
    S3Bucket,
    SecurityGroup,
)


class TestInventoryCollectorInit:
    """InventoryCollector 초기화 테스트"""

    def test_init_with_context(self, mock_context):
        """ExecutionContext로 초기화"""
        collector = InventoryCollector(mock_context)

        assert collector._ctx == mock_context

    def test_init_stores_context(self, mock_static_context):
        """컨텍스트가 올바르게 저장됨"""
        collector = InventoryCollector(mock_static_context)

        assert collector._ctx is not None
        assert collector._ctx.profile_name == "test-static"


class TestCollectVPCs:
    """VPC 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    @patch("shared.aws.inventory.services.vpc.collect_vpcs")
    def test_collect_vpcs_success(self, mock_collect, mock_parallel, mock_context):
        """VPC 수집 성공"""
        # Mock 데이터 준비
        mock_vpcs = [
            VPC(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                vpc_id="vpc-12345678",
                name="test-vpc",
                cidr_block="10.0.0.0/16",
                state="available",
                is_default=False,
            )
        ]

        # parallel_collect 결과 모킹
        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_vpcs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        # 검증
        assert len(vpcs) == 1
        assert vpcs[0].vpc_id == "vpc-12345678"
        assert vpcs[0].cidr_block == "10.0.0.0/16"
        mock_parallel.assert_called_once()

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_vpcs_empty_result(self, mock_parallel, mock_context):
        """VPC가 없는 경우"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        assert vpcs == []

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_vpcs_multiple_regions(self, mock_parallel, mock_context):
        """다중 리전 VPC 수집"""
        mock_vpcs = [
            VPC(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                vpc_id="vpc-ap",
                name="ap-vpc",
                cidr_block="10.0.0.0/16",
                state="available",
            ),
            VPC(
                account_id="123456789012",
                account_name="test-account",
                region="us-east-1",
                vpc_id="vpc-us",
                name="us-vpc",
                cidr_block="10.1.0.0/16",
                state="available",
            ),
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_vpcs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        assert len(vpcs) == 2
        assert vpcs[0].region == "ap-northeast-2"
        assert vpcs[1].region == "us-east-1"


class TestCollectEC2:
    """EC2 인스턴스 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_ec2_success(self, mock_parallel, mock_context):
        """EC2 인스턴스 수집 성공"""
        mock_instances = [
            EC2Instance(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                instance_id="i-1234567890abcdef0",
                name="test-instance",
                instance_type="t3.micro",
                state="running",
                private_ip="10.0.0.1",
                public_ip="",
                vpc_id="vpc-12345678",
                platform="Linux/UNIX",
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_instances
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        instances = collector.collect_ec2()

        assert len(instances) == 1
        assert instances[0].instance_id == "i-1234567890abcdef0"
        assert instances[0].state == "running"

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_ec2_with_tags(self, mock_parallel, mock_context):
        """태그가 있는 EC2 인스턴스 수집"""
        mock_instances = [
            EC2Instance(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                instance_id="i-1234567890abcdef0",
                name="web-server",
                instance_type="t3.micro",
                state="running",
                private_ip="10.0.0.1",
                public_ip="",
                vpc_id="vpc-12345678",
                platform="Linux/UNIX",
                tags={"Name": "web-server", "Environment": "production"},
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_instances
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        instances = collector.collect_ec2()

        assert instances[0].tags["Environment"] == "production"


class TestCollectEBSVolumes:
    """EBS Volume 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_ebs_volumes_success(self, mock_parallel, mock_context):
        """EBS Volume 수집 성공"""
        mock_volumes = [
            EBSVolume(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                volume_id="vol-1234567890abcdef0",
                name="test-volume",
                size_gb=100,
                volume_type="gp3",
                state="available",
                availability_zone="ap-northeast-2a",
                encrypted=True,
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_volumes
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        volumes = collector.collect_ebs_volumes()

        assert len(volumes) == 1
        assert volumes[0].volume_id == "vol-1234567890abcdef0"
        assert volumes[0].encrypted is True
        assert volumes[0].size_gb == 100


class TestCollectSecurityGroups:
    """Security Group 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_security_groups_success(self, mock_parallel, mock_context):
        """Security Group 수집 성공"""
        mock_sgs = [
            SecurityGroup(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                group_id="sg-12345678",
                group_name="test-sg",
                vpc_id="vpc-12345678",
                description="Test security group",
                rule_count=5,
                has_public_access=False,
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_sgs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        sgs = collector.collect_security_groups()

        assert len(sgs) == 1
        assert sgs[0].group_id == "sg-12345678"
        assert sgs[0].has_public_access is False


class TestCollectLambdaFunctions:
    """Lambda Function 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_lambda_functions_success(self, mock_parallel, mock_context):
        """Lambda Function 수집 성공"""
        mock_functions = [
            LambdaFunction(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                function_name="test-function",
                function_arn="arn:aws:lambda:ap-northeast-2:123456789012:function:test-function",
                runtime="python3.11",
                handler="lambda_function.lambda_handler",
                code_size=1024,
                memory_size=128,
                timeout=3,
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_functions
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        functions = collector.collect_lambda_functions()

        assert len(functions) == 1
        assert functions[0].function_name == "test-function"
        assert functions[0].runtime == "python3.11"


class TestCollectS3Buckets:
    """S3 Bucket 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_s3_buckets_success(self, mock_parallel, mock_context):
        """S3 Bucket 수집 성공"""
        mock_buckets = [
            S3Bucket(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                bucket_name="test-bucket",
                versioning_status="Enabled",
                encryption_type="AES256",
                public_access_block=True,
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_buckets
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        buckets = collector.collect_s3_buckets()

        assert len(buckets) == 1
        assert buckets[0].bucket_name == "test-bucket"
        assert buckets[0].public_access_block is True


class TestCollectRDSInstances:
    """RDS Instance 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_rds_instances_success(self, mock_parallel, mock_context):
        """RDS Instance 수집 성공"""
        mock_instances = [
            RDSInstance(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                db_instance_id="test-db",
                db_instance_arn="arn:aws:rds:ap-northeast-2:123456789012:db:test-db",
                db_instance_class="db.t3.micro",
                engine="postgres",
                engine_version="14.7",
                status="available",
                multi_az=False,
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_instances
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        instances = collector.collect_rds_instances()

        assert len(instances) == 1
        assert instances[0].db_instance_id == "test-db"
        assert instances[0].engine == "postgres"


class TestCollectLoadBalancers:
    """Load Balancer 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_load_balancers_success(self, mock_parallel, mock_context):
        """Load Balancer 수집 성공"""
        mock_lbs = [
            LoadBalancer(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                name="test-alb",
                arn="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/test-alb/1234567890",
                lb_type="application",
                scheme="internet-facing",
                state="active",
                vpc_id="vpc-12345678",
                dns_name="test-alb-1234567890.ap-northeast-2.elb.amazonaws.com",
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_lbs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        lbs = collector.collect_load_balancers()

        assert len(lbs) == 1
        assert lbs[0].name == "test-alb"
        assert lbs[0].lb_type == "application"

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_load_balancers_include_classic(self, mock_parallel, mock_context):
        """Classic Load Balancer 포함 수집"""
        mock_lbs = [
            LoadBalancer(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                name="test-clb",
                arn="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/test-clb",
                lb_type="classic",
                scheme="internet-facing",
                state="active",
                vpc_id="vpc-12345678",
                dns_name="test-clb-1234567890.ap-northeast-2.elb.amazonaws.com",
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_lbs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        lbs = collector.collect_load_balancers(include_classic=True)

        assert len(lbs) == 1
        assert lbs[0].lb_type == "classic"


class TestErrorHandling:
    """에러 처리 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_handles_access_denied(self, mock_parallel, mock_context):
        """AccessDenied 에러 처리"""
        # parallel_collect가 에러를 포함한 결과 반환
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_result.error_count = 1
        mock_result.success_count = 0
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        # 빈 리스트 반환 확인
        assert vpcs == []

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_handles_throttling(self, mock_parallel, mock_context):
        """Throttling 에러 처리"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_result.error_count = 1
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        instances = collector.collect_ec2()

        assert instances == []

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_handles_partial_success(self, mock_parallel, mock_context):
        """일부 성공 시 처리"""
        # 일부 리전은 성공, 일부는 실패
        mock_vpcs = [
            VPC(
                account_id="123456789012",
                account_name="test-account",
                region="ap-northeast-2",
                vpc_id="vpc-12345678",
                name="test-vpc",
                cidr_block="10.0.0.0/16",
                state="available",
            )
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_vpcs
        mock_result.error_count = 1
        mock_result.success_count = 1
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        # 성공한 데이터는 반환됨
        assert len(vpcs) == 1
        assert vpcs[0].vpc_id == "vpc-12345678"


class TestMultiAccountCollection:
    """멀티 계정 수집 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_from_multiple_accounts(self, mock_parallel, mock_context):
        """다중 계정에서 VPC 수집"""
        mock_vpcs = [
            VPC(
                account_id="111111111111",
                account_name="account-1",
                region="ap-northeast-2",
                vpc_id="vpc-account1",
                name="vpc-1",
                cidr_block="10.0.0.0/16",
                state="available",
            ),
            VPC(
                account_id="222222222222",
                account_name="account-2",
                region="ap-northeast-2",
                vpc_id="vpc-account2",
                name="vpc-2",
                cidr_block="10.1.0.0/16",
                state="available",
            ),
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_vpcs
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        vpcs = collector.collect_vpcs()

        assert len(vpcs) == 2
        assert vpcs[0].account_id == "111111111111"
        assert vpcs[1].account_id == "222222222222"

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_collect_from_multiple_accounts_and_regions(self, mock_parallel, mock_context):
        """다중 계정 및 리전에서 EC2 수집"""
        mock_instances = [
            EC2Instance(
                account_id="111111111111",
                account_name="account-1",
                region="ap-northeast-2",
                instance_id="i-account1-ap",
                name="instance-1",
                instance_type="t3.micro",
                state="running",
                private_ip="10.0.0.1",
                public_ip="",
                vpc_id="vpc-12345678",
                platform="Linux/UNIX",
            ),
            EC2Instance(
                account_id="111111111111",
                account_name="account-1",
                region="us-east-1",
                instance_id="i-account1-us",
                name="instance-2",
                instance_type="t3.small",
                state="running",
                private_ip="10.1.0.1",
                public_ip="",
                vpc_id="vpc-87654321",
                platform="Linux/UNIX",
            ),
            EC2Instance(
                account_id="222222222222",
                account_name="account-2",
                region="ap-northeast-2",
                instance_id="i-account2-ap",
                name="instance-3",
                instance_type="t3.medium",
                state="stopped",
                private_ip="10.2.0.1",
                public_ip="",
                vpc_id="vpc-abcdef12",
                platform="Windows",
            ),
        ]

        mock_result = Mock()
        mock_result.get_flat_data.return_value = mock_instances
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        instances = collector.collect_ec2()

        # 3개 인스턴스 (2개 계정 × 2개 리전 중 3개)
        assert len(instances) == 3
        assert instances[0].region == "ap-northeast-2"
        assert instances[1].region == "us-east-1"
        assert instances[2].account_id == "222222222222"


class TestParallelCollectIntegration:
    """parallel_collect 통합 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_parallel_collect_called_with_correct_service(self, mock_parallel, mock_context):
        """parallel_collect이 올바른 서비스로 호출됨"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)

        # EC2 수집
        collector.collect_ec2()
        assert mock_parallel.call_args[1]["service"] == "ec2"

        # Lambda 수집
        collector.collect_lambda_functions()
        assert mock_parallel.call_args[1]["service"] == "lambda"

        # RDS 수집
        collector.collect_rds_instances()
        assert mock_parallel.call_args[1]["service"] == "rds"

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_parallel_collect_uses_context(self, mock_parallel, mock_context):
        """parallel_collect이 컨텍스트를 사용함"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)
        collector.collect_vpcs()

        # 첫 번째 인자가 ctx인지 확인
        assert mock_parallel.call_args[0][0] == mock_context


class TestCollectorCompleteness:
    """모든 수집 메서드 테스트"""

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_all_network_collectors(self, mock_parallel, mock_context):
        """모든 네트워크 리소스 수집 메서드 존재 확인"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)

        # Network 카테고리
        assert hasattr(collector, "collect_vpcs")
        assert hasattr(collector, "collect_subnets")
        assert hasattr(collector, "collect_route_tables")
        assert hasattr(collector, "collect_internet_gateways")
        assert hasattr(collector, "collect_elastic_ips")
        assert hasattr(collector, "collect_enis")
        assert hasattr(collector, "collect_nat_gateways")
        assert hasattr(collector, "collect_vpc_endpoints")

        # 메서드 호출 가능 확인
        collector.collect_vpcs()
        collector.collect_subnets()

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_all_compute_collectors(self, mock_parallel, mock_context):
        """모든 컴퓨팅 리소스 수집 메서드 존재 확인"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)

        # Compute 카테고리
        assert hasattr(collector, "collect_ec2")
        assert hasattr(collector, "collect_ebs_volumes")
        assert hasattr(collector, "collect_lambda_functions")
        assert hasattr(collector, "collect_ecs_clusters")
        assert hasattr(collector, "collect_ecs_services")

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_all_database_collectors(self, mock_parallel, mock_context):
        """모든 데이터베이스 리소스 수집 메서드 존재 확인"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)

        # Database/Storage 카테고리
        assert hasattr(collector, "collect_rds_instances")
        assert hasattr(collector, "collect_rds_clusters")
        assert hasattr(collector, "collect_s3_buckets")
        assert hasattr(collector, "collect_dynamodb_tables")

    @patch("shared.aws.inventory.collector.parallel_collect")
    def test_all_security_collectors(self, mock_parallel, mock_context):
        """모든 보안 리소스 수집 메서드 존재 확인"""
        mock_result = Mock()
        mock_result.get_flat_data.return_value = []
        mock_parallel.return_value = mock_result

        collector = InventoryCollector(mock_context)

        # Security 카테고리
        assert hasattr(collector, "collect_security_groups")
        assert hasattr(collector, "collect_kms_keys")
        assert hasattr(collector, "collect_secrets")
        assert hasattr(collector, "collect_iam_roles")
        assert hasattr(collector, "collect_iam_users")
        assert hasattr(collector, "collect_iam_policies")
