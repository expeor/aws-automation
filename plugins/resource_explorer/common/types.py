"""
plugins/resource_explorer/common/types.py - 리소스 타입 정의

인벤토리 수집에 사용되는 데이터 클래스 정의.

카테고리:
- Network: VPC, Subnet, RouteTable, InternetGateway, EIP, ENI, NATGateway, VPCEndpoint
- Compute: EC2Instance, EBSVolume, LambdaFunction, ECSCluster, ECSService
- Database/Storage: RDSInstance, S3Bucket, DynamoDBTable, ElastiCacheCluster
- Security: SecurityGroup, KMSKey, Secret
- CDN/DNS: CloudFrontDistribution, Route53HostedZone
- Load Balancing: LoadBalancer, TargetGroup
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EC2Instance:
    """EC2 인스턴스 정보"""

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
    # 추가 상세 정보
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
    """Security Group 정보"""

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
    # 추가 상세 정보
    owner_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    rule_count: int = 0
    has_public_access: bool = False
    attached_resource_ids: list[str] = field(default_factory=list)
    attached_resource_types: list[str] = field(default_factory=list)


@dataclass
class ENI:
    """Elastic Network Interface 정보"""

    account_id: str
    account_name: str
    region: str
    eni_id: str
    name: str
    status: str
    interface_type: str
    private_ip: str
    public_ip: str
    vpc_id: str
    subnet_id: str
    instance_id: str
    # 추가 상세 정보
    availability_zone: str = ""
    security_group_ids: list[str] = field(default_factory=list)
    attachment_time: datetime | None = None
    requester_id: str = ""
    requester_managed: bool = False
    tags: dict[str, str] = field(default_factory=dict)
    connected_resource_type: str = ""
    connected_resource_id: str = ""


@dataclass
class NATGateway:
    """NAT Gateway 정보"""

    account_id: str
    account_name: str
    region: str
    nat_gateway_id: str
    name: str
    state: str
    connectivity_type: str
    public_ip: str
    private_ip: str
    vpc_id: str
    subnet_id: str
    # 추가 상세 정보
    create_time: datetime | None = None
    allocation_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class VPCEndpoint:
    """VPC Endpoint 정보"""

    account_id: str
    account_name: str
    region: str
    endpoint_id: str
    name: str
    endpoint_type: str
    state: str
    service_name: str
    vpc_id: str
    private_dns_enabled: bool = False
    # 추가 상세 정보
    creation_timestamp: datetime | None = None
    route_table_ids: list[str] = field(default_factory=list)
    subnet_ids: list[str] = field(default_factory=list)
    network_interface_ids: list[str] = field(default_factory=list)
    policy_document: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class LoadBalancer:
    """Load Balancer 정보"""

    account_id: str
    account_name: str
    region: str
    name: str
    arn: str
    lb_type: str
    scheme: str
    state: str
    vpc_id: str
    dns_name: str
    target_groups: list = field(default_factory=list)
    total_targets: int = 0
    healthy_targets: int = 0
    # 추가 상세 정보
    created_time: datetime | None = None
    availability_zones: list[str] = field(default_factory=list)
    security_group_ids: list[str] = field(default_factory=list)
    access_logs_enabled: bool = False
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class TargetGroup:
    """Target Group 정보"""

    account_id: str
    account_name: str
    region: str
    name: str
    arn: str
    target_type: str
    protocol: str
    port: int
    vpc_id: str
    total_targets: int = 0
    healthy_targets: int = 0
    unhealthy_targets: int = 0
    load_balancer_arns: list = field(default_factory=list)
    # 추가 상세 정보
    health_check_path: str = ""
    health_check_protocol: str = ""
    health_check_interval: int = 30
    deregistration_delay: int = 300
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Network 카테고리 추가 리소스
# =============================================================================


@dataclass
class VPC:
    """VPC 정보"""

    account_id: str
    account_name: str
    region: str
    vpc_id: str
    name: str
    cidr_block: str
    state: str
    is_default: bool = False
    instance_tenancy: str = "default"
    dhcp_options_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Subnet:
    """Subnet 정보"""

    account_id: str
    account_name: str
    region: str
    subnet_id: str
    name: str
    vpc_id: str
    cidr_block: str
    availability_zone: str
    state: str
    available_ip_count: int = 0
    map_public_ip_on_launch: bool = False
    is_default: bool = False
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class RouteTable:
    """Route Table 정보"""

    account_id: str
    account_name: str
    region: str
    route_table_id: str
    name: str
    vpc_id: str
    is_main: bool = False
    route_count: int = 0
    association_count: int = 0
    subnet_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class InternetGateway:
    """Internet Gateway 정보"""

    account_id: str
    account_name: str
    region: str
    igw_id: str
    name: str
    state: str
    vpc_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ElasticIP:
    """Elastic IP 정보"""

    account_id: str
    account_name: str
    region: str
    allocation_id: str
    public_ip: str
    name: str
    domain: str = "vpc"
    instance_id: str = ""
    network_interface_id: str = ""
    private_ip: str = ""
    association_id: str = ""
    is_attached: bool = False
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Compute 카테고리 추가 리소스
# =============================================================================


@dataclass
class EBSVolume:
    """EBS Volume 정보"""

    account_id: str
    account_name: str
    region: str
    volume_id: str
    name: str
    size_gb: int
    volume_type: str
    state: str
    availability_zone: str
    iops: int = 0
    throughput: int = 0
    encrypted: bool = False
    kms_key_id: str = ""
    snapshot_id: str = ""
    instance_id: str = ""
    device_name: str = ""
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class LambdaFunction:
    """Lambda Function 정보"""

    account_id: str
    account_name: str
    region: str
    function_name: str
    function_arn: str
    runtime: str
    handler: str
    code_size: int
    memory_size: int
    timeout: int
    state: str = ""
    last_modified: str = ""
    description: str = ""
    role: str = ""
    vpc_id: str = ""
    subnet_ids: list[str] = field(default_factory=list)
    security_group_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ECSCluster:
    """ECS Cluster 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_name: str
    cluster_arn: str
    status: str
    running_tasks_count: int = 0
    pending_tasks_count: int = 0
    active_services_count: int = 0
    registered_container_instances_count: int = 0
    capacity_providers: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ECSService:
    """ECS Service 정보"""

    account_id: str
    account_name: str
    region: str
    service_name: str
    service_arn: str
    cluster_arn: str
    status: str
    desired_count: int = 0
    running_count: int = 0
    pending_count: int = 0
    launch_type: str = ""
    task_definition: str = ""
    load_balancer_count: int = 0
    created_at: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Database/Storage 카테고리
# =============================================================================


@dataclass
class RDSInstance:
    """RDS Instance 정보"""

    account_id: str
    account_name: str
    region: str
    db_instance_id: str
    db_instance_arn: str
    db_instance_class: str
    engine: str
    engine_version: str
    status: str
    endpoint: str = ""
    port: int = 0
    allocated_storage: int = 0
    storage_type: str = ""
    multi_az: bool = False
    publicly_accessible: bool = False
    encrypted: bool = False
    vpc_id: str = ""
    availability_zone: str = ""
    db_cluster_id: str = ""
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class S3Bucket:
    """S3 Bucket 정보"""

    account_id: str
    account_name: str
    region: str
    bucket_name: str
    creation_date: datetime | None = None
    versioning_status: str = ""
    encryption_type: str = ""
    public_access_block: bool = True
    logging_enabled: bool = False
    lifecycle_rules_count: int = 0
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class DynamoDBTable:
    """DynamoDB Table 정보"""

    account_id: str
    account_name: str
    region: str
    table_name: str
    table_arn: str
    status: str
    billing_mode: str = ""
    item_count: int = 0
    table_size_bytes: int = 0
    read_capacity: int = 0
    write_capacity: int = 0
    gsi_count: int = 0
    lsi_count: int = 0
    stream_enabled: bool = False
    encryption_type: str = ""
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ElastiCacheCluster:
    """ElastiCache Cluster 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_id: str
    cluster_arn: str
    engine: str
    engine_version: str
    node_type: str
    status: str
    num_nodes: int = 0
    availability_zone: str = ""
    vpc_id: str = ""
    subnet_group: str = ""
    security_groups: list[str] = field(default_factory=list)
    encryption_at_rest: bool = False
    encryption_in_transit: bool = False
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Security 카테고리 추가 리소스
# =============================================================================


@dataclass
class KMSKey:
    """KMS Key 정보"""

    account_id: str
    account_name: str
    region: str
    key_id: str
    key_arn: str
    alias: str
    description: str
    key_state: str
    key_usage: str = ""
    key_spec: str = ""
    origin: str = ""
    key_manager: str = ""
    creation_date: datetime | None = None
    enabled: bool = True
    multi_region: bool = False
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Secret:
    """Secrets Manager Secret 정보"""

    account_id: str
    account_name: str
    region: str
    secret_id: str
    secret_arn: str
    name: str
    description: str = ""
    kms_key_id: str = ""
    rotation_enabled: bool = False
    rotation_lambda_arn: str = ""
    last_rotated_date: datetime | None = None
    last_accessed_date: datetime | None = None
    created_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# CDN/DNS 카테고리
# =============================================================================


@dataclass
class CloudFrontDistribution:
    """CloudFront Distribution 정보"""

    account_id: str
    account_name: str
    region: str  # always "global"
    distribution_id: str
    distribution_arn: str
    domain_name: str
    status: str
    enabled: bool = True
    origin_count: int = 0
    aliases: list[str] = field(default_factory=list)
    price_class: str = ""
    http_version: str = ""
    is_ipv6_enabled: bool = False
    web_acl_id: str = ""
    last_modified_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Route53HostedZone:
    """Route 53 Hosted Zone 정보"""

    account_id: str
    account_name: str
    region: str  # always "global"
    zone_id: str
    name: str
    record_count: int = 0
    is_private: bool = False
    comment: str = ""
    vpc_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Compute 카테고리 추가 리소스 (ASG, Launch Template, EKS, AMI, Snapshot)
# =============================================================================


@dataclass
class AutoScalingGroup:
    """Auto Scaling Group 정보"""

    account_id: str
    account_name: str
    region: str
    asg_name: str
    asg_arn: str
    launch_template_id: str = ""
    launch_template_name: str = ""
    launch_config_name: str = ""
    min_size: int = 0
    max_size: int = 0
    desired_capacity: int = 0
    current_capacity: int = 0
    health_check_type: str = ""
    availability_zones: list[str] = field(default_factory=list)
    target_group_arns: list[str] = field(default_factory=list)
    vpc_zone_identifier: str = ""
    status: str = ""
    created_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class LaunchTemplate:
    """Launch Template 정보"""

    account_id: str
    account_name: str
    region: str
    template_id: str
    template_name: str
    version_number: int = 0
    default_version: int = 0
    latest_version: int = 0
    instance_type: str = ""
    ami_id: str = ""
    key_name: str = ""
    security_group_ids: list[str] = field(default_factory=list)
    created_by: str = ""
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class EKSCluster:
    """EKS Cluster 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_name: str
    cluster_arn: str
    status: str
    version: str = ""
    endpoint: str = ""
    role_arn: str = ""
    vpc_id: str = ""
    subnet_ids: list[str] = field(default_factory=list)
    security_group_ids: list[str] = field(default_factory=list)
    cluster_security_group_id: str = ""
    endpoint_public_access: bool = True
    endpoint_private_access: bool = False
    created_at: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class EKSNodeGroup:
    """EKS Node Group 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_name: str
    nodegroup_name: str
    nodegroup_arn: str
    status: str
    capacity_type: str = ""
    instance_types: list[str] = field(default_factory=list)
    scaling_desired: int = 0
    scaling_min: int = 0
    scaling_max: int = 0
    ami_type: str = ""
    disk_size: int = 0
    subnet_ids: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class AMI:
    """EC2 AMI 정보"""

    account_id: str
    account_name: str
    region: str
    image_id: str
    name: str
    description: str = ""
    state: str = ""
    owner_id: str = ""
    is_public: bool = False
    architecture: str = ""
    platform: str = ""
    root_device_type: str = ""
    virtualization_type: str = ""
    ena_support: bool = False
    creation_date: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Snapshot:
    """EC2 Snapshot 정보"""

    account_id: str
    account_name: str
    region: str
    snapshot_id: str
    name: str
    volume_id: str
    volume_size: int
    state: str
    description: str = ""
    encrypted: bool = False
    kms_key_id: str = ""
    owner_id: str = ""
    progress: str = ""
    start_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Database 카테고리 추가 리소스 (RDS Cluster, Redshift)
# =============================================================================


@dataclass
class RDSCluster:
    """RDS Cluster (Aurora) 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_id: str
    cluster_arn: str
    engine: str
    engine_version: str
    status: str
    endpoint: str = ""
    reader_endpoint: str = ""
    port: int = 0
    db_cluster_members: int = 0
    multi_az: bool = False
    storage_encrypted: bool = False
    kms_key_id: str = ""
    vpc_id: str = ""
    availability_zones: list[str] = field(default_factory=list)
    backup_retention_period: int = 0
    cluster_create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class RedshiftCluster:
    """Redshift Cluster 정보"""

    account_id: str
    account_name: str
    region: str
    cluster_id: str
    cluster_arn: str
    node_type: str
    cluster_status: str
    number_of_nodes: int = 1
    db_name: str = ""
    endpoint: str = ""
    port: int = 5439
    vpc_id: str = ""
    availability_zone: str = ""
    encrypted: bool = False
    kms_key_id: str = ""
    publicly_accessible: bool = False
    cluster_create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Storage 카테고리 추가 리소스 (EFS, FSx)
# =============================================================================


@dataclass
class EFSFileSystem:
    """EFS File System 정보"""

    account_id: str
    account_name: str
    region: str
    file_system_id: str
    file_system_arn: str
    name: str
    life_cycle_state: str
    performance_mode: str = ""
    throughput_mode: str = ""
    provisioned_throughput: float = 0.0
    size_in_bytes: int = 0
    number_of_mount_targets: int = 0
    encrypted: bool = False
    kms_key_id: str = ""
    creation_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class FSxFileSystem:
    """FSx File System 정보"""

    account_id: str
    account_name: str
    region: str
    file_system_id: str
    file_system_arn: str
    file_system_type: str
    lifecycle: str
    storage_capacity: int = 0
    storage_type: str = ""
    vpc_id: str = ""
    subnet_ids: list[str] = field(default_factory=list)
    dns_name: str = ""
    kms_key_id: str = ""
    creation_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Network 카테고리 추가 리소스 (Transit Gateway, VPN, NACL, Peering)
# =============================================================================


@dataclass
class TransitGateway:
    """Transit Gateway 정보"""

    account_id: str
    account_name: str
    region: str
    tgw_id: str
    tgw_arn: str
    name: str
    state: str
    owner_id: str = ""
    description: str = ""
    amazon_side_asn: int = 0
    default_route_table_id: str = ""
    auto_accept_shared_attachments: str = ""
    dns_support: str = ""
    vpn_ecmp_support: str = ""
    creation_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class TransitGatewayAttachment:
    """Transit Gateway Attachment 정보"""

    account_id: str
    account_name: str
    region: str
    attachment_id: str
    tgw_id: str
    resource_id: str
    resource_type: str
    resource_owner_id: str = ""
    state: str = ""
    association_state: str = ""
    creation_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class VPNGateway:
    """VPN Gateway 정보"""

    account_id: str
    account_name: str
    region: str
    vpn_gateway_id: str
    name: str
    state: str
    vpn_type: str = ""
    amazon_side_asn: int = 0
    availability_zone: str = ""
    vpc_attachments: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class VPNConnection:
    """VPN Connection 정보"""

    account_id: str
    account_name: str
    region: str
    vpn_connection_id: str
    name: str
    state: str
    vpn_type: str = ""
    customer_gateway_id: str = ""
    vpn_gateway_id: str = ""
    transit_gateway_id: str = ""
    category: str = ""
    static_routes_only: bool = False
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class NetworkACL:
    """Network ACL 정보"""

    account_id: str
    account_name: str
    region: str
    nacl_id: str
    name: str
    vpc_id: str
    is_default: bool = False
    inbound_rule_count: int = 0
    outbound_rule_count: int = 0
    associated_subnets: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class VPCPeeringConnection:
    """VPC Peering Connection 정보"""

    account_id: str
    account_name: str
    region: str
    peering_id: str
    name: str
    status: str
    requester_vpc_id: str = ""
    requester_owner_id: str = ""
    requester_cidr: str = ""
    accepter_vpc_id: str = ""
    accepter_owner_id: str = ""
    accepter_cidr: str = ""
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Integration/Messaging 카테고리 (SNS, SQS, EventBridge, Step Functions, API Gateway)
# =============================================================================


@dataclass
class SNSTopic:
    """SNS Topic 정보"""

    account_id: str
    account_name: str
    region: str
    topic_arn: str
    name: str
    display_name: str = ""
    subscriptions_confirmed: int = 0
    subscriptions_pending: int = 0
    kms_key_id: str = ""
    fifo_topic: bool = False
    content_based_deduplication: bool = False
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class SQSQueue:
    """SQS Queue 정보"""

    account_id: str
    account_name: str
    region: str
    queue_url: str
    queue_arn: str
    name: str
    fifo_queue: bool = False
    visibility_timeout: int = 30
    message_retention_period: int = 345600
    max_message_size: int = 262144
    delay_seconds: int = 0
    receive_message_wait_time: int = 0
    approximate_number_of_messages: int = 0
    kms_key_id: str = ""
    dead_letter_target_arn: str = ""
    created_timestamp: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class EventBridgeRule:
    """EventBridge Rule 정보"""

    account_id: str
    account_name: str
    region: str
    rule_name: str
    rule_arn: str
    event_bus_name: str = "default"
    state: str = ""
    description: str = ""
    schedule_expression: str = ""
    event_pattern: str = ""
    target_count: int = 0
    managed_by: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class StepFunction:
    """Step Functions State Machine 정보"""

    account_id: str
    account_name: str
    region: str
    state_machine_arn: str
    name: str
    state_machine_type: str = ""
    status: str = ""
    role_arn: str = ""
    logging_level: str = ""
    tracing_enabled: bool = False
    creation_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class APIGatewayAPI:
    """API Gateway REST/HTTP API 정보"""

    account_id: str
    account_name: str
    region: str
    api_id: str
    name: str
    api_type: str  # REST, HTTP, WEBSOCKET
    protocol_type: str = ""
    endpoint_type: str = ""
    description: str = ""
    version: str = ""
    api_endpoint: str = ""
    disable_execute_api_endpoint: bool = False
    created_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Monitoring 카테고리 (CloudWatch Alarm, Log Group)
# =============================================================================


@dataclass
class CloudWatchAlarm:
    """CloudWatch Alarm 정보"""

    account_id: str
    account_name: str
    region: str
    alarm_name: str
    alarm_arn: str
    state_value: str
    metric_name: str = ""
    namespace: str = ""
    statistic: str = ""
    period: int = 0
    threshold: float = 0.0
    comparison_operator: str = ""
    evaluation_periods: int = 0
    datapoints_to_alarm: int = 0
    treat_missing_data: str = ""
    actions_enabled: bool = True
    alarm_actions: list[str] = field(default_factory=list)
    insufficient_data_actions: list[str] = field(default_factory=list)
    ok_actions: list[str] = field(default_factory=list)
    state_updated_timestamp: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CloudWatchLogGroup:
    """CloudWatch Log Group 정보"""

    account_id: str
    account_name: str
    region: str
    log_group_name: str
    log_group_arn: str
    stored_bytes: int = 0
    retention_in_days: int | None = None
    metric_filter_count: int = 0
    kms_key_id: str = ""
    creation_time: int = 0
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Security 카테고리 추가 리소스 (IAM, ACM, WAF)
# =============================================================================


@dataclass
class IAMRole:
    """IAM Role 정보"""

    account_id: str
    account_name: str
    region: str  # always "global"
    role_id: str
    role_name: str
    role_arn: str
    path: str = "/"
    description: str = ""
    max_session_duration: int = 3600
    create_date: datetime | None = None
    last_used_date: datetime | None = None
    last_used_region: str = ""
    attached_policies_count: int = 0
    inline_policies_count: int = 0
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class IAMUser:
    """IAM User 정보"""

    account_id: str
    account_name: str
    region: str  # always "global"
    user_id: str
    user_name: str
    user_arn: str
    path: str = "/"
    create_date: datetime | None = None
    password_last_used: datetime | None = None
    has_console_access: bool = False
    has_access_keys: bool = False
    access_key_count: int = 0
    mfa_enabled: bool = False
    attached_policies_count: int = 0
    inline_policies_count: int = 0
    groups: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class IAMPolicy:
    """IAM Policy 정보"""

    account_id: str
    account_name: str
    region: str  # always "global"
    policy_id: str
    policy_name: str
    policy_arn: str
    path: str = "/"
    description: str = ""
    is_attachable: bool = True
    attachment_count: int = 0
    permissions_boundary_usage_count: int = 0
    default_version_id: str = ""
    create_date: datetime | None = None
    update_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ACMCertificate:
    """ACM Certificate 정보"""

    account_id: str
    account_name: str
    region: str
    certificate_arn: str
    domain_name: str
    status: str
    certificate_type: str = ""
    key_algorithm: str = ""
    issuer: str = ""
    subject_alternative_names: list[str] = field(default_factory=list)
    in_use_by: list[str] = field(default_factory=list)
    not_before: datetime | None = None
    not_after: datetime | None = None
    created_at: datetime | None = None
    renewal_eligibility: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class WAFWebACL:
    """WAF WebACL 정보"""

    account_id: str
    account_name: str
    region: str
    web_acl_id: str
    web_acl_arn: str
    name: str
    scope: str  # REGIONAL, CLOUDFRONT
    description: str = ""
    capacity: int = 0
    rule_count: int = 0
    default_action: str = ""
    visibility_config_metric_name: str = ""
    managed_by_firewall_manager: bool = False
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Analytics 카테고리 (Kinesis, Glue)
# =============================================================================


@dataclass
class KinesisStream:
    """Kinesis Data Stream 정보"""

    account_id: str
    account_name: str
    region: str
    stream_name: str
    stream_arn: str
    status: str
    stream_mode: str = ""
    shard_count: int = 0
    retention_period_hours: int = 24
    encryption_type: str = ""
    kms_key_id: str = ""
    stream_creation_timestamp: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class KinesisFirehose:
    """Kinesis Firehose Delivery Stream 정보"""

    account_id: str
    account_name: str
    region: str
    delivery_stream_name: str
    delivery_stream_arn: str
    delivery_stream_status: str
    delivery_stream_type: str = ""
    source_type: str = ""
    destination_type: str = ""
    has_more_destinations: bool = False
    version_id: str = ""
    create_timestamp: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class GlueDatabase:
    """Glue Database 정보"""

    account_id: str
    account_name: str
    region: str
    database_name: str
    catalog_id: str
    description: str = ""
    location_uri: str = ""
    table_count: int = 0
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# DevOps 카테고리 (CloudFormation, CodePipeline, CodeBuild)
# =============================================================================


@dataclass
class CloudFormationStack:
    """CloudFormation Stack 정보"""

    account_id: str
    account_name: str
    region: str
    stack_id: str
    stack_name: str
    stack_status: str
    description: str = ""
    creation_time: datetime | None = None
    last_updated_time: datetime | None = None
    deletion_time: datetime | None = None
    parent_id: str = ""
    root_id: str = ""
    drift_status: str = ""
    enable_termination_protection: bool = False
    role_arn: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CodePipeline:
    """CodePipeline 정보"""

    account_id: str
    account_name: str
    region: str
    pipeline_name: str
    pipeline_arn: str
    pipeline_version: int = 0
    stage_count: int = 0
    role_arn: str = ""
    execution_mode: str = ""
    pipeline_type: str = ""
    created: datetime | None = None
    updated: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CodeBuildProject:
    """CodeBuild Project 정보"""

    account_id: str
    account_name: str
    region: str
    project_name: str
    project_arn: str
    description: str = ""
    source_type: str = ""
    source_location: str = ""
    environment_type: str = ""
    compute_type: str = ""
    environment_image: str = ""
    service_role: str = ""
    timeout_in_minutes: int = 0
    queued_timeout_in_minutes: int = 0
    encryption_key: str = ""
    badge_enabled: bool = False
    last_modified: datetime | None = None
    created: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Backup 카테고리 (Backup Vault, Backup Plan)
# =============================================================================


@dataclass
class BackupVault:
    """Backup Vault 정보"""

    account_id: str
    account_name: str
    region: str
    vault_name: str
    vault_arn: str
    encryption_key_arn: str = ""
    creator_request_id: str = ""
    number_of_recovery_points: int = 0
    locked: bool = False
    min_retention_days: int = 0
    max_retention_days: int = 0
    creation_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class BackupPlan:
    """Backup Plan 정보"""

    account_id: str
    account_name: str
    region: str
    backup_plan_id: str
    backup_plan_arn: str
    backup_plan_name: str
    version_id: str = ""
    creator_request_id: str = ""
    rule_count: int = 0
    advanced_backup_settings: bool = False
    creation_date: datetime | None = None
    last_execution_date: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)
