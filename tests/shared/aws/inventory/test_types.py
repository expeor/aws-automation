"""
tests/shared/aws/inventory/test_types.py - Inventory 타입 테스트
"""

from datetime import datetime

import pytest

from shared.aws.inventory.types import (
    AMI,
    ENI,
    VPC,
    CloudFormationStack,
    CloudWatchAlarm,
    DynamoDBTable,
    EBSVolume,
    EC2Instance,
    ECSCluster,
    ECSService,
    ElastiCacheCluster,
    ElasticIP,
    IAMRole,
    IAMUser,
    KMSKey,
    LambdaFunction,
    LoadBalancer,
    NATGateway,
    RDSCluster,
    RDSInstance,
    Route53HostedZone,
    RouteTable,
    S3Bucket,
    Secret,
    SecurityGroup,
    Snapshot,
    SNSTopic,
    SQSQueue,
    Subnet,
    TargetGroup,
    VPCEndpoint,
)


class TestEC2Instance:
    """EC2Instance 데이터클래스 테스트"""

    def test_required_fields(self):
        """필수 필드"""
        instance = EC2Instance(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            instance_id="i-1234567890abcdef0",
            name="my-instance",
            instance_type="t3.micro",
            state="running",
            private_ip="10.0.1.50",
            public_ip="54.180.1.1",
            vpc_id="vpc-12345678",
            platform="Linux/UNIX",
        )

        assert instance.instance_id == "i-1234567890abcdef0"
        assert instance.state == "running"
        assert instance.instance_type == "t3.micro"

    def test_default_values(self):
        """기본값 확인"""
        instance = EC2Instance(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            instance_id="i-1234567890abcdef0",
            name="",
            instance_type="t3.micro",
            state="running",
            private_ip="",
            public_ip="",
            vpc_id="",
            platform="",
        )

        assert instance.launch_time is None
        assert instance.subnet_id == ""
        assert instance.ebs_volume_ids == []
        assert instance.security_group_ids == []
        assert instance.tags == {}


class TestSecurityGroup:
    """SecurityGroup 데이터클래스 테스트"""

    def test_required_fields(self):
        """필수 필드"""
        sg = SecurityGroup(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            group_id="sg-12345678",
            group_name="my-security-group",
            vpc_id="vpc-12345678",
            description="Test security group",
        )

        assert sg.group_id == "sg-12345678"
        assert sg.group_name == "my-security-group"

    def test_default_values(self):
        """기본값 확인"""
        sg = SecurityGroup(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            group_id="sg-12345678",
            group_name="my-security-group",
            vpc_id="vpc-12345678",
            description="",
        )

        assert sg.inbound_rules == []
        assert sg.outbound_rules == []
        assert sg.rule_count == 0
        assert sg.has_public_access is False


class TestVPC:
    """VPC 데이터클래스 테스트"""

    def test_basic_vpc(self):
        """기본 VPC"""
        vpc = VPC(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            vpc_id="vpc-12345678",
            name="my-vpc",
            cidr_block="10.0.0.0/16",
            state="available",
        )

        assert vpc.vpc_id == "vpc-12345678"
        assert vpc.cidr_block == "10.0.0.0/16"
        assert vpc.is_default is False

    def test_default_vpc(self):
        """기본 VPC 플래그"""
        vpc = VPC(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            vpc_id="vpc-12345678",
            name="default",
            cidr_block="172.31.0.0/16",
            state="available",
            is_default=True,
        )

        assert vpc.is_default is True


class TestSubnet:
    """Subnet 데이터클래스 테스트"""

    def test_basic_subnet(self):
        """기본 서브넷"""
        subnet = Subnet(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            subnet_id="subnet-12345678",
            name="private-subnet-1a",
            vpc_id="vpc-12345678",
            cidr_block="10.0.1.0/24",
            availability_zone="ap-northeast-2a",
            state="available",
        )

        assert subnet.subnet_id == "subnet-12345678"
        assert subnet.cidr_block == "10.0.1.0/24"
        assert subnet.map_public_ip_on_launch is False


class TestRDSInstance:
    """RDSInstance 데이터클래스 테스트"""

    def test_basic_rds(self):
        """기본 RDS 인스턴스"""
        rds = RDSInstance(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            db_instance_id="my-database",
            db_instance_arn="arn:aws:rds:ap-northeast-2:123456789012:db:my-database",
            db_instance_class="db.t3.micro",
            engine="mysql",
            engine_version="8.0.28",
            status="available",
        )

        assert rds.db_instance_id == "my-database"
        assert rds.engine == "mysql"
        assert rds.multi_az is False
        assert rds.publicly_accessible is False


class TestLambdaFunction:
    """LambdaFunction 데이터클래스 테스트"""

    def test_basic_lambda(self):
        """기본 Lambda 함수"""
        fn = LambdaFunction(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            function_name="my-function",
            function_arn="arn:aws:lambda:ap-northeast-2:123456789012:function:my-function",
            runtime="python3.10",
            handler="index.handler",
            code_size=1024,
            memory_size=128,
            timeout=30,
        )

        assert fn.function_name == "my-function"
        assert fn.runtime == "python3.10"
        assert fn.memory_size == 128


class TestLoadBalancer:
    """LoadBalancer 데이터클래스 테스트"""

    def test_basic_alb(self):
        """기본 ALB"""
        alb = LoadBalancer(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            name="my-alb",
            arn="arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb/1234567890abcdef",
            lb_type="application",
            scheme="internet-facing",
            state="active",
            vpc_id="vpc-12345678",
            dns_name="my-alb-123456789.ap-northeast-2.elb.amazonaws.com",
        )

        assert alb.name == "my-alb"
        assert alb.lb_type == "application"
        assert alb.scheme == "internet-facing"


class TestS3Bucket:
    """S3Bucket 데이터클래스 테스트"""

    def test_basic_bucket(self):
        """기본 S3 버킷"""
        bucket = S3Bucket(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            bucket_name="my-bucket",
        )

        assert bucket.bucket_name == "my-bucket"
        assert bucket.public_access_block is True
        assert bucket.versioning_status == ""


class TestDynamoDBTable:
    """DynamoDBTable 데이터클래스 테스트"""

    def test_basic_table(self):
        """기본 DynamoDB 테이블"""
        table = DynamoDBTable(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            table_name="my-table",
            table_arn="arn:aws:dynamodb:ap-northeast-2:123456789012:table/my-table",
            status="ACTIVE",
        )

        assert table.table_name == "my-table"
        assert table.billing_mode == ""
        assert table.item_count == 0


class TestIAMRole:
    """IAMRole 데이터클래스 테스트"""

    def test_basic_role(self):
        """기본 IAM 역할"""
        role = IAMRole(
            account_id="123456789012",
            account_name="test-account",
            region="global",
            role_id="AROAXXXXXXXXXXXXXXXXX",
            role_name="my-role",
            role_arn="arn:aws:iam::123456789012:role/my-role",
        )

        assert role.role_name == "my-role"
        assert role.path == "/"
        assert role.max_session_duration == 3600


class TestKMSKey:
    """KMSKey 데이터클래스 테스트"""

    def test_basic_key(self):
        """기본 KMS 키"""
        key = KMSKey(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            key_id="12345678-1234-1234-1234-123456789012",
            key_arn="arn:aws:kms:ap-northeast-2:123456789012:key/12345678-1234-1234-1234-123456789012",
            alias="alias/my-key",
            description="My encryption key",
            key_state="Enabled",
        )

        assert key.key_id == "12345678-1234-1234-1234-123456789012"
        assert key.enabled is True


class TestNATGateway:
    """NATGateway 데이터클래스 테스트"""

    def test_basic_nat(self):
        """기본 NAT Gateway"""
        nat = NATGateway(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            nat_gateway_id="nat-12345678",
            name="my-nat",
            state="available",
            connectivity_type="public",
            public_ip="54.180.1.1",
            private_ip="10.0.1.50",
            vpc_id="vpc-12345678",
            subnet_id="subnet-12345678",
        )

        assert nat.nat_gateway_id == "nat-12345678"
        assert nat.connectivity_type == "public"


class TestEBSVolume:
    """EBSVolume 데이터클래스 테스트"""

    def test_basic_volume(self):
        """기본 EBS 볼륨"""
        volume = EBSVolume(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            volume_id="vol-12345678",
            name="my-volume",
            size_gb=100,
            volume_type="gp3",
            state="in-use",
            availability_zone="ap-northeast-2a",
        )

        assert volume.volume_id == "vol-12345678"
        assert volume.size_gb == 100
        assert volume.volume_type == "gp3"
        assert volume.encrypted is False


class TestCloudFormationStack:
    """CloudFormationStack 데이터클래스 테스트"""

    def test_basic_stack(self):
        """기본 CloudFormation 스택"""
        stack = CloudFormationStack(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            stack_id="arn:aws:cloudformation:ap-northeast-2:123456789012:stack/my-stack/12345678",
            stack_name="my-stack",
            stack_status="CREATE_COMPLETE",
        )

        assert stack.stack_name == "my-stack"
        assert stack.stack_status == "CREATE_COMPLETE"
        assert stack.enable_termination_protection is False
