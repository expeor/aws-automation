# Inventory Collector 패턴

`shared/aws/inventory/collector.py` 모듈의 사용 패턴입니다.

병렬 처리를 통해 multi-account/region에서 AWS 리소스를 수집합니다.

## 권장 패턴

```python
from core.shared.aws.inventory import InventoryCollector
```

---

## InventoryCollector 클래스

```python
class InventoryCollector:
    """AWS 리소스 인벤토리 수집기

    병렬 처리를 통해 multi-account/region에서 리소스를 수집합니다.

    Usage:
        collector = InventoryCollector(ctx)

        # Network
        vpcs = collector.collect_vpcs()
        subnets = collector.collect_subnets()

        # Compute
        instances = collector.collect_ec2()
        volumes = collector.collect_ebs_volumes()

        # Database
        rds_instances = collector.collect_rds_instances()
    """

    def __init__(self, ctx):
        """
        Args:
            ctx: ExecutionContext (provider, regions, accounts 포함)
        """
```

### 기본 사용법

```python
from core.shared.aws.inventory import InventoryCollector

def run(ctx) -> None:
    collector = InventoryCollector(ctx)

    # 필요한 리소스만 수집
    vpcs = collector.collect_vpcs()
    subnets = collector.collect_subnets()
    ec2_instances = collector.collect_ec2()

    # 결과 처리
    print(f"VPCs: {len(vpcs)}, Subnets: {len(subnets)}, EC2: {len(ec2_instances)}")
```

---

## 리소스 카테고리별 메서드

### Network (Basic)

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_vpcs()` | `list[VPC]` | ec2 |
| `collect_subnets()` | `list[Subnet]` | ec2 |
| `collect_route_tables()` | `list[RouteTable]` | ec2 |
| `collect_internet_gateways()` | `list[InternetGateway]` | ec2 |
| `collect_elastic_ips()` | `list[ElasticIP]` | ec2 |
| `collect_enis()` | `list[ENI]` | ec2 |
| `collect_nat_gateways()` | `list[NATGateway]` | ec2 |
| `collect_vpc_endpoints()` | `list[VPCEndpoint]` | ec2 |

### Network (Advanced)

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_transit_gateways()` | `list[TransitGateway]` | ec2 |
| `collect_transit_gateway_attachments()` | `list[TransitGatewayAttachment]` | ec2 |
| `collect_vpn_gateways()` | `list[VPNGateway]` | ec2 |
| `collect_vpn_connections()` | `list[VPNConnection]` | ec2 |
| `collect_network_acls()` | `list[NetworkACL]` | ec2 |
| `collect_vpc_peering_connections()` | `list[VPCPeeringConnection]` | ec2 |

### Compute

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_ec2()` | `list[EC2Instance]` | ec2 |
| `collect_ebs_volumes()` | `list[EBSVolume]` | ec2 |
| `collect_lambda_functions()` | `list[LambdaFunction]` | lambda |
| `collect_ecs_clusters()` | `list[ECSCluster]` | ecs |
| `collect_ecs_services()` | `list[ECSService]` | ecs |
| `collect_auto_scaling_groups()` | `list[AutoScalingGroup]` | autoscaling |
| `collect_launch_templates()` | `list[LaunchTemplate]` | ec2 |
| `collect_eks_clusters()` | `list[EKSCluster]` | eks |
| `collect_eks_node_groups()` | `list[EKSNodeGroup]` | eks |
| `collect_amis()` | `list[AMI]` | ec2 |
| `collect_snapshots()` | `list[Snapshot]` | ec2 |

### Database/Storage

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_rds_instances()` | `list[RDSInstance]` | rds |
| `collect_rds_clusters()` | `list[RDSCluster]` | rds |
| `collect_s3_buckets()` | `list[S3Bucket]` | s3 |
| `collect_dynamodb_tables()` | `list[DynamoDBTable]` | dynamodb |
| `collect_elasticache_clusters()` | `list[ElastiCacheCluster]` | elasticache |
| `collect_redshift_clusters()` | `list[RedshiftCluster]` | redshift |
| `collect_efs_file_systems()` | `list[EFSFileSystem]` | efs |
| `collect_fsx_file_systems()` | `list[FSxFileSystem]` | fsx |

### Security

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_security_groups()` | `list[SecurityGroup]` | ec2 |
| `collect_kms_keys()` | `list[KMSKey]` | kms |
| `collect_secrets()` | `list[Secret]` | secretsmanager |
| `collect_iam_roles()` | `list[IAMRole]` | iam |
| `collect_iam_users()` | `list[IAMUser]` | iam |
| `collect_iam_policies()` | `list[IAMPolicy]` | iam |
| `collect_acm_certificates()` | `list[ACMCertificate]` | acm |
| `collect_waf_web_acls()` | `list[WAFWebACL]` | wafv2 |

### CDN/DNS

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_cloudfront_distributions()` | `list[CloudFrontDistribution]` | cloudfront |
| `collect_route53_hosted_zones()` | `list[Route53HostedZone]` | route53 |

### Load Balancing

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_load_balancers(include_classic=False)` | `list[LoadBalancer]` | elbv2/elb |
| `collect_target_groups()` | `list[TargetGroup]` | elbv2 |

### Integration/Messaging

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_sns_topics()` | `list[SNSTopic]` | sns |
| `collect_sqs_queues()` | `list[SQSQueue]` | sqs |
| `collect_eventbridge_rules()` | `list[EventBridgeRule]` | events |
| `collect_step_functions()` | `list[StepFunction]` | stepfunctions |
| `collect_api_gateway_apis()` | `list[APIGatewayAPI]` | apigateway |

### Monitoring

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_cloudwatch_alarms()` | `list[CloudWatchAlarm]` | cloudwatch |
| `collect_cloudwatch_log_groups()` | `list[CloudWatchLogGroup]` | logs |

### Analytics

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_kinesis_streams()` | `list[KinesisStream]` | kinesis |
| `collect_kinesis_firehoses()` | `list[KinesisFirehose]` | firehose |
| `collect_glue_databases()` | `list[GlueDatabase]` | glue |

### DevOps

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_cloudformation_stacks()` | `list[CloudFormationStack]` | cloudformation |
| `collect_codepipelines()` | `list[CodePipeline]` | codepipeline |
| `collect_codebuild_projects()` | `list[CodeBuildProject]` | codebuild |

### Backup

| 메서드 | 반환 타입 | AWS 서비스 |
|--------|----------|-----------|
| `collect_backup_vaults()` | `list[BackupVault]` | backup |
| `collect_backup_plans()` | `list[BackupPlan]` | backup |

---

## 리소스 타입 (dataclass)

모든 리소스 타입은 `shared/aws/inventory/types.py`에 정의되어 있습니다.

### 공통 필드

모든 리소스 타입은 다음 필드를 포함:

```python
@dataclass
class AnyResource:
    account_id: str       # AWS 계정 ID
    account_name: str     # 계정 이름 (alias)
    region: str           # 리전 코드 (글로벌 서비스는 "global")
    # ... 리소스별 필드
    tags: dict[str, str] = field(default_factory=dict)  # 태그
```

### 주요 타입 예시

```python
@dataclass
class EC2Instance:
    account_id: str
    account_name: str
    region: str
    instance_id: str
    name: str
    instance_type: str
    state: str
    private_ip: str
    public_ip: str
    vpc_id: str
    platform: str
    launch_time: datetime | None = None
    subnet_id: str = ""
    availability_zone: str = ""
    iam_role: str = ""
    key_name: str = ""
    ebs_volume_ids: list[str] = field(default_factory=list)
    security_group_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class SecurityGroup:
    account_id: str
    account_name: str
    region: str
    group_id: str
    group_name: str
    vpc_id: str
    description: str
    inbound_rules: list = field(default_factory=list)
    outbound_rules: list = field(default_factory=list)
    attached_enis: list = field(default_factory=list)
    rule_count: int = 0
    has_public_access: bool = False
    tags: dict[str, str] = field(default_factory=dict)
```

---

## parallel_collect 연동 패턴

InventoryCollector 내부에서 `parallel_collect`를 사용합니다.
직접 수집 로직이 필요한 경우:

```python
from core.parallel import parallel_collect

def _collect_custom_resources(session, account_id: str, account_name: str, region: str):
    """커스텀 리소스 수집"""
    client = get_client(session, "custom-service", region_name=region)
    # ... 수집 로직
    return resources

def run(ctx) -> None:
    # InventoryCollector로 기본 리소스 수집
    collector = InventoryCollector(ctx)
    ec2_instances = collector.collect_ec2()

    # 커스텀 수집 로직 추가
    result = parallel_collect(ctx, _collect_custom_resources, service="custom-service")
    custom_resources = result.get_flat_data()
```

---

## 글로벌 서비스 처리

일부 서비스는 리전이 없거나 특정 리전에서만 조회:

| 서비스 | 조회 리전 | `region` 필드 |
|--------|----------|---------------|
| S3 | us-east-1 (API 호출) | 버킷 실제 리전 |
| CloudFront | us-east-1 | `"global"` |
| Route 53 | us-east-1 | `"global"` |
| IAM | us-east-1 | `"global"` |

---

## 전체 예시 (네트워크 인벤토리)

```python
from core.shared.aws.inventory import InventoryCollector
from core.shared.io.compat import generate_reports
from core.shared.io.output import OutputPath

def run(ctx) -> None:
    """VPC 네트워크 인벤토리 수집"""
    collector = InventoryCollector(ctx)

    # 네트워크 리소스 수집
    vpcs = collector.collect_vpcs()
    subnets = collector.collect_subnets()
    route_tables = collector.collect_route_tables()
    security_groups = collector.collect_security_groups()
    nat_gateways = collector.collect_nat_gateways()

    # VPC별 리소스 매핑
    vpc_map = {}
    for vpc in vpcs:
        vpc_id = vpc.vpc_id
        vpc_map[vpc_id] = {
            "vpc": vpc,
            "subnets": [s for s in subnets if s.vpc_id == vpc_id],
            "route_tables": [r for r in route_tables if r.vpc_id == vpc_id],
            "security_groups": [sg for sg in security_groups if sg.vpc_id == vpc_id],
            "nat_gateways": [n for n in nat_gateways if n.vpc_id == vpc_id],
        }

    # 분석 결과
    for vpc_id, resources in vpc_map.items():
        vpc = resources["vpc"]
        print(f"VPC: {vpc.name or vpc_id}")
        print(f"  Subnets: {len(resources['subnets'])}")
        print(f"  Route Tables: {len(resources['route_tables'])}")
        print(f"  Security Groups: {len(resources['security_groups'])}")
        print(f"  NAT Gateways: {len(resources['nat_gateways'])}")

    # 보고서 생성
    flat_data = [
        {
            "account_id": vpc.account_id,
            "account_name": vpc.account_name,
            "region": vpc.region,
            "resource_id": vpc.vpc_id,
            "resource_name": vpc.name,
            "cidr_block": vpc.cidr_block,
            "is_default": vpc.is_default,
        }
        for vpc in vpcs
    ]

    identifier = ctx.accounts[0].id if ctx.accounts else ctx.profile_name or "default"
    output_path = OutputPath(identifier).sub("vpc", "inventory").with_date().build()

    generate_reports(
        ctx,
        data=flat_data,
        html_config={
            "title": "VPC 인벤토리",
            "service": "VPC",
            "tool_name": "inventory",
            "total": len(vpcs),
        },
        output_dir=output_path,
    )
```

---

## 참조

- `shared/aws/inventory/collector.py` - InventoryCollector 클래스
- `shared/aws/inventory/types.py` - 리소스 타입 정의
- `shared/aws/inventory/services/` - 서비스별 수집기
- `.claude/skills/parallel-execution-patterns.md` - 병렬 처리 패턴
