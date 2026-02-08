"""
core/shared/aws/inventory/types.py - 리소스 타입 정의

인벤토리 수집에 사용되는 데이터 클래스 정의.

카테고리:
- Network: VPC, Subnet, RouteTable, InternetGateway, EIP, ENI, NATGateway, VPCEndpoint
- Compute: EC2Instance, EBSVolume, LambdaFunction, ECSCluster, ECSService
- Database/Storage: RDSInstance, S3Bucket, DynamoDBTable, ElastiCacheCluster
- Security: SecurityGroup, KMSKey, Secret
- CDN/DNS: CloudFrontDistribution, Route53HostedZone
- Load Balancing: LoadBalancer, TargetGroup
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EC2Instance:
    """EC2 인스턴스 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        instance_id: EC2 인스턴스 ID
        name: 인스턴스 Name 태그 값
        instance_type: 인스턴스 유형 (예: t3.micro)
        state: 인스턴스 상태 (running, stopped 등)
        private_ip: 프라이빗 IP 주소
        public_ip: 퍼블릭 IP 주소
        vpc_id: 소속 VPC ID
        platform: 플랫폼 정보 (Linux, Windows 등)
        launch_time: 인스턴스 시작 시간
        subnet_id: 소속 서브넷 ID
        availability_zone: 가용 영역
        iam_role: 연결된 IAM 역할
        key_name: SSH 키 페어 이름
        ebs_volume_ids: 연결된 EBS 볼륨 ID 목록
        security_group_ids: 연결된 보안 그룹 ID 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """Security Group 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        group_id: 보안 그룹 ID
        group_name: 보안 그룹 이름
        vpc_id: 소속 VPC ID
        description: 보안 그룹 설명
        inbound_rules: 인바운드 규칙 목록
        outbound_rules: 아웃바운드 규칙 목록
        attached_enis: 연결된 ENI 목록
        owner_id: 소유자 계정 ID
        tags: 리소스 태그 딕셔너리
        rule_count: 총 규칙 수
        has_public_access: 퍼블릭 접근 허용 여부
        attached_resource_ids: 연결된 리소스 ID 목록
        attached_resource_types: 연결된 리소스 유형 목록
    """

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
    """Elastic Network Interface 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        eni_id: ENI ID
        name: ENI Name 태그 값
        status: ENI 상태 (in-use, available 등)
        interface_type: 인터페이스 유형 (interface, nat_gateway 등)
        private_ip: 프라이빗 IP 주소
        public_ip: 퍼블릭 IP 주소
        vpc_id: 소속 VPC ID
        subnet_id: 소속 서브넷 ID
        instance_id: 연결된 EC2 인스턴스 ID
        availability_zone: 가용 영역
        security_group_ids: 연결된 보안 그룹 ID 목록
        attachment_time: ENI 연결 시간
        requester_id: 요청자 ID
        requester_managed: AWS 관리 ENI 여부
        tags: 리소스 태그 딕셔너리
        connected_resource_type: 연결된 리소스 유형
        connected_resource_id: 연결된 리소스 ID
    """

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
    """NAT Gateway 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        nat_gateway_id: NAT Gateway ID
        name: NAT Gateway Name 태그 값
        state: NAT Gateway 상태 (available, pending 등)
        connectivity_type: 연결 유형 (public, private)
        public_ip: 퍼블릭 IP 주소
        private_ip: 프라이빗 IP 주소
        vpc_id: 소속 VPC ID
        subnet_id: 소속 서브넷 ID
        create_time: 생성 시간
        allocation_id: Elastic IP 할당 ID
        tags: 리소스 태그 딕셔너리
    """

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
    """VPC Endpoint 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        endpoint_id: VPC Endpoint ID
        name: Endpoint Name 태그 값
        endpoint_type: Endpoint 유형 (Interface, Gateway 등)
        state: Endpoint 상태
        service_name: 연결된 AWS 서비스 이름
        vpc_id: 소속 VPC ID
        private_dns_enabled: Private DNS 활성화 여부
        creation_timestamp: 생성 시간
        route_table_ids: 연결된 라우트 테이블 ID 목록
        subnet_ids: 연결된 서브넷 ID 목록
        network_interface_ids: 연결된 네트워크 인터페이스 ID 목록
        policy_document: VPC Endpoint 정책 문서
        tags: 리소스 태그 딕셔너리
    """

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
    """Load Balancer 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        name: 로드 밸런서 이름
        arn: 로드 밸런서 ARN
        lb_type: 로드 밸런서 유형 (ALB, NLB, CLB 등)
        scheme: 스킴 (internet-facing, internal)
        state: 로드 밸런서 상태
        vpc_id: 소속 VPC ID
        dns_name: DNS 이름
        target_groups: 연결된 대상 그룹 목록
        total_targets: 전체 대상 수
        healthy_targets: 정상 대상 수
        created_time: 생성 시간
        availability_zones: 가용 영역 목록
        security_group_ids: 연결된 보안 그룹 ID 목록
        access_logs_enabled: 액세스 로그 활성화 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """Target Group 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        name: 대상 그룹 이름
        arn: 대상 그룹 ARN
        target_type: 대상 유형 (instance, ip, lambda 등)
        protocol: 프로토콜 (HTTP, HTTPS, TCP 등)
        port: 포트 번호
        vpc_id: 소속 VPC ID
        total_targets: 전체 대상 수
        healthy_targets: 정상 대상 수
        unhealthy_targets: 비정상 대상 수
        load_balancer_arns: 연결된 로드 밸런서 ARN 목록
        health_check_path: 헬스 체크 경로
        health_check_protocol: 헬스 체크 프로토콜
        health_check_interval: 헬스 체크 간격 (초)
        deregistration_delay: 등록 해제 지연 시간 (초)
        tags: 리소스 태그 딕셔너리
    """

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
    """VPC 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        vpc_id: VPC ID
        name: VPC Name 태그 값
        cidr_block: CIDR 블록
        state: VPC 상태
        is_default: 기본 VPC 여부
        instance_tenancy: 인스턴스 테넌시 (default, dedicated 등)
        dhcp_options_id: DHCP 옵션 세트 ID
        tags: 리소스 태그 딕셔너리
    """

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
    """Subnet 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        subnet_id: 서브넷 ID
        name: 서브넷 Name 태그 값
        vpc_id: 소속 VPC ID
        cidr_block: CIDR 블록
        availability_zone: 가용 영역
        state: 서브넷 상태
        available_ip_count: 사용 가능한 IP 수
        map_public_ip_on_launch: 퍼블릭 IP 자동 할당 여부
        is_default: 기본 서브넷 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """Route Table 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        route_table_id: 라우트 테이블 ID
        name: 라우트 테이블 Name 태그 값
        vpc_id: 소속 VPC ID
        is_main: 메인 라우트 테이블 여부
        route_count: 라우트 규칙 수
        association_count: 서브넷 연결 수
        subnet_ids: 연결된 서브넷 ID 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """Internet Gateway 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        igw_id: Internet Gateway ID
        name: IGW Name 태그 값
        state: IGW 상태
        vpc_id: 연결된 VPC ID
        tags: 리소스 태그 딕셔너리
    """

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
    """Elastic IP 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        allocation_id: EIP 할당 ID
        public_ip: 퍼블릭 IP 주소
        name: EIP Name 태그 값
        domain: 도메인 (vpc 또는 standard)
        instance_id: 연결된 EC2 인스턴스 ID
        network_interface_id: 연결된 네트워크 인터페이스 ID
        private_ip: 연결된 프라이빗 IP 주소
        association_id: EIP 연결 ID
        is_attached: 리소스 연결 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """EBS Volume 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        volume_id: EBS 볼륨 ID
        name: 볼륨 Name 태그 값
        size_gb: 볼륨 크기 (GB)
        volume_type: 볼륨 유형 (gp3, io2 등)
        state: 볼륨 상태 (in-use, available 등)
        availability_zone: 가용 영역
        iops: 초당 I/O 작업 수
        throughput: 처리량 (MiB/s)
        encrypted: 암호화 여부
        kms_key_id: KMS 키 ID
        snapshot_id: 원본 스냅샷 ID
        instance_id: 연결된 EC2 인스턴스 ID
        device_name: 디바이스 이름 (예: /dev/xvda)
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Lambda Function 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        function_name: 함수 이름
        function_arn: 함수 ARN
        runtime: 런타임 (python3.12, nodejs20.x 등)
        handler: 핸들러 경로
        code_size: 코드 크기 (바이트)
        memory_size: 메모리 크기 (MB)
        timeout: 제한 시간 (초)
        state: 함수 상태
        last_modified: 마지막 수정 시간
        description: 함수 설명
        role: 실행 역할 ARN
        vpc_id: 연결된 VPC ID
        subnet_ids: 연결된 서브넷 ID 목록
        security_group_ids: 연결된 보안 그룹 ID 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """ECS Cluster 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_name: 클러스터 이름
        cluster_arn: 클러스터 ARN
        status: 클러스터 상태
        running_tasks_count: 실행 중인 태스크 수
        pending_tasks_count: 대기 중인 태스크 수
        active_services_count: 활성 서비스 수
        registered_container_instances_count: 등록된 컨테이너 인스턴스 수
        capacity_providers: 용량 공급자 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """ECS Service 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        service_name: 서비스 이름
        service_arn: 서비스 ARN
        cluster_arn: 소속 클러스터 ARN
        status: 서비스 상태
        desired_count: 희망 태스크 수
        running_count: 실행 중인 태스크 수
        pending_count: 대기 중인 태스크 수
        launch_type: 실행 유형 (FARGATE, EC2 등)
        task_definition: 태스크 정의 ARN
        load_balancer_count: 연결된 로드 밸런서 수
        created_at: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """RDS Instance 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        db_instance_id: DB 인스턴스 식별자
        db_instance_arn: DB 인스턴스 ARN
        db_instance_class: DB 인스턴스 클래스 (예: db.r6g.large)
        engine: DB 엔진 (mysql, postgres 등)
        engine_version: DB 엔진 버전
        status: DB 인스턴스 상태
        endpoint: 접속 엔드포인트 주소
        port: 접속 포트 번호
        allocated_storage: 할당된 스토리지 크기 (GB)
        storage_type: 스토리지 유형 (gp3, io1 등)
        multi_az: Multi-AZ 배포 여부
        publicly_accessible: 퍼블릭 접근 가능 여부
        encrypted: 스토리지 암호화 여부
        vpc_id: 소속 VPC ID
        availability_zone: 가용 영역
        db_cluster_id: 소속 Aurora 클러스터 ID
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """S3 Bucket 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        bucket_name: 버킷 이름
        creation_date: 버킷 생성 일시
        versioning_status: 버전 관리 상태 (Enabled, Suspended 등)
        encryption_type: 암호화 유형 (AES256, aws:kms 등)
        public_access_block: 퍼블릭 액세스 차단 여부
        logging_enabled: 서버 액세스 로깅 활성화 여부
        lifecycle_rules_count: 수명 주기 규칙 수
        tags: 리소스 태그 딕셔너리
    """

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
    """DynamoDB Table 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        table_name: 테이블 이름
        table_arn: 테이블 ARN
        status: 테이블 상태
        billing_mode: 과금 모드 (PAY_PER_REQUEST, PROVISIONED)
        item_count: 아이템 수
        table_size_bytes: 테이블 크기 (바이트)
        read_capacity: 프로비저닝된 읽기 용량 유닛
        write_capacity: 프로비저닝된 쓰기 용량 유닛
        gsi_count: 글로벌 보조 인덱스 수
        lsi_count: 로컬 보조 인덱스 수
        stream_enabled: DynamoDB Streams 활성화 여부
        encryption_type: 암호화 유형
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """ElastiCache Cluster 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_id: 클러스터 ID
        cluster_arn: 클러스터 ARN
        engine: 엔진 유형 (redis, memcached)
        engine_version: 엔진 버전
        node_type: 노드 유형 (예: cache.r6g.large)
        status: 클러스터 상태
        num_nodes: 노드 수
        availability_zone: 가용 영역
        vpc_id: 소속 VPC ID
        subnet_group: 서브넷 그룹 이름
        security_groups: 연결된 보안 그룹 목록
        encryption_at_rest: 저장 데이터 암호화 여부
        encryption_in_transit: 전송 중 암호화 여부
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """KMS Key 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        key_id: KMS 키 ID
        key_arn: KMS 키 ARN
        alias: 키 별칭
        description: 키 설명
        key_state: 키 상태 (Enabled, Disabled 등)
        key_usage: 키 용도 (ENCRYPT_DECRYPT, SIGN_VERIFY 등)
        key_spec: 키 사양 (SYMMETRIC_DEFAULT, RSA_2048 등)
        origin: 키 생성 출처 (AWS_KMS, EXTERNAL 등)
        key_manager: 키 관리자 (AWS, CUSTOMER)
        creation_date: 키 생성 일시
        enabled: 키 활성화 여부
        multi_region: 멀티 리전 키 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """Secrets Manager Secret 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        secret_id: 시크릿 ID
        secret_arn: 시크릿 ARN
        name: 시크릿 이름
        description: 시크릿 설명
        kms_key_id: 암호화에 사용된 KMS 키 ID
        rotation_enabled: 자동 교체 활성화 여부
        rotation_lambda_arn: 교체용 Lambda 함수 ARN
        last_rotated_date: 마지막 교체 일시
        last_accessed_date: 마지막 접근 일시
        created_date: 생성 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """CloudFront Distribution 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 (항상 "global")
        distribution_id: 배포 ID
        distribution_arn: 배포 ARN
        domain_name: CloudFront 도메인 이름
        status: 배포 상태
        enabled: 배포 활성화 여부
        origin_count: 오리진 수
        aliases: 대체 도메인 이름(CNAME) 목록
        price_class: 요금 클래스
        http_version: HTTP 버전
        is_ipv6_enabled: IPv6 활성화 여부
        web_acl_id: 연결된 WAF WebACL ID
        last_modified_time: 마지막 수정 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Route 53 Hosted Zone 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 (항상 "global")
        zone_id: 호스팅 영역 ID
        name: 호스팅 영역 도메인 이름
        record_count: DNS 레코드 수
        is_private: 프라이빗 호스팅 영역 여부
        comment: 호스팅 영역 설명
        vpc_ids: 연결된 VPC ID 목록 (프라이빗 영역)
        tags: 리소스 태그 딕셔너리
    """

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
    """Auto Scaling Group 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        asg_name: Auto Scaling 그룹 이름
        asg_arn: Auto Scaling 그룹 ARN
        launch_template_id: 시작 템플릿 ID
        launch_template_name: 시작 템플릿 이름
        launch_config_name: 시작 구성 이름 (레거시)
        min_size: 최소 인스턴스 수
        max_size: 최대 인스턴스 수
        desired_capacity: 희망 인스턴스 수
        current_capacity: 현재 인스턴스 수
        health_check_type: 헬스 체크 유형 (EC2, ELB)
        availability_zones: 가용 영역 목록
        target_group_arns: 연결된 대상 그룹 ARN 목록
        vpc_zone_identifier: VPC 서브넷 식별자
        status: ASG 상태
        created_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Launch Template 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        template_id: 시작 템플릿 ID
        template_name: 시작 템플릿 이름
        version_number: 현재 버전 번호
        default_version: 기본 버전 번호
        latest_version: 최신 버전 번호
        instance_type: 인스턴스 유형
        ami_id: AMI ID
        key_name: SSH 키 페어 이름
        security_group_ids: 보안 그룹 ID 목록
        created_by: 생성자
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """EKS Cluster 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_name: EKS 클러스터 이름
        cluster_arn: EKS 클러스터 ARN
        status: 클러스터 상태
        version: Kubernetes 버전
        endpoint: API 서버 엔드포인트 URL
        role_arn: 클러스터 서비스 역할 ARN
        vpc_id: 소속 VPC ID
        subnet_ids: 클러스터 서브넷 ID 목록
        security_group_ids: 추가 보안 그룹 ID 목록
        cluster_security_group_id: 클러스터 보안 그룹 ID
        endpoint_public_access: 퍼블릭 API 엔드포인트 활성화 여부
        endpoint_private_access: 프라이빗 API 엔드포인트 활성화 여부
        created_at: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """EKS Node Group 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_name: 소속 EKS 클러스터 이름
        nodegroup_name: 노드 그룹 이름
        nodegroup_arn: 노드 그룹 ARN
        status: 노드 그룹 상태
        capacity_type: 용량 유형 (ON_DEMAND, SPOT)
        instance_types: 인스턴스 유형 목록
        scaling_desired: 희망 노드 수
        scaling_min: 최소 노드 수
        scaling_max: 최대 노드 수
        ami_type: AMI 유형 (AL2_x86_64 등)
        disk_size: 디스크 크기 (GB)
        subnet_ids: 서브넷 ID 목록
        created_at: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """EC2 AMI 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        image_id: AMI ID
        name: AMI 이름
        description: AMI 설명
        state: AMI 상태 (available, pending 등)
        owner_id: 소유자 계정 ID
        is_public: 퍼블릭 공유 여부
        architecture: 아키텍처 (x86_64, arm64 등)
        platform: 플랫폼 (Linux, Windows 등)
        root_device_type: 루트 디바이스 유형 (ebs, instance-store)
        virtualization_type: 가상화 유형 (hvm, paravirtual)
        ena_support: ENA 지원 여부
        creation_date: 생성 일시 문자열
        tags: 리소스 태그 딕셔너리
    """

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
    """EC2 Snapshot 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        snapshot_id: 스냅샷 ID
        name: 스냅샷 Name 태그 값
        volume_id: 원본 볼륨 ID
        volume_size: 볼륨 크기 (GB)
        state: 스냅샷 상태 (completed, pending 등)
        description: 스냅샷 설명
        encrypted: 암호화 여부
        kms_key_id: KMS 키 ID
        owner_id: 소유자 계정 ID
        progress: 생성 진행률
        start_time: 스냅샷 생성 시작 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """RDS Cluster (Aurora) 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_id: 클러스터 식별자
        cluster_arn: 클러스터 ARN
        engine: DB 엔진 (aurora-mysql, aurora-postgresql 등)
        engine_version: DB 엔진 버전
        status: 클러스터 상태
        endpoint: 쓰기 엔드포인트 주소
        reader_endpoint: 읽기 엔드포인트 주소
        port: 접속 포트 번호
        db_cluster_members: 클러스터 멤버(인스턴스) 수
        multi_az: Multi-AZ 배포 여부
        storage_encrypted: 스토리지 암호화 여부
        kms_key_id: 암호화에 사용된 KMS 키 ID
        vpc_id: 소속 VPC ID
        availability_zones: 가용 영역 목록
        backup_retention_period: 백업 보존 기간 (일)
        cluster_create_time: 클러스터 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Redshift Cluster 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        cluster_id: 클러스터 식별자
        cluster_arn: 클러스터 ARN
        node_type: 노드 유형 (예: dc2.large)
        cluster_status: 클러스터 상태
        number_of_nodes: 노드 수
        db_name: 데이터베이스 이름
        endpoint: 접속 엔드포인트 주소
        port: 접속 포트 번호
        vpc_id: 소속 VPC ID
        availability_zone: 가용 영역
        encrypted: 암호화 여부
        kms_key_id: KMS 키 ID
        publicly_accessible: 퍼블릭 접근 가능 여부
        cluster_create_time: 클러스터 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """EFS File System 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        file_system_id: 파일 시스템 ID
        file_system_arn: 파일 시스템 ARN
        name: 파일 시스템 이름
        life_cycle_state: 수명 주기 상태 (available, creating 등)
        performance_mode: 성능 모드 (generalPurpose, maxIO)
        throughput_mode: 처리량 모드 (bursting, provisioned, elastic)
        provisioned_throughput: 프로비저닝된 처리량 (MiB/s)
        size_in_bytes: 파일 시스템 크기 (바이트)
        number_of_mount_targets: 마운트 타겟 수
        encrypted: 암호화 여부
        kms_key_id: KMS 키 ID
        creation_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """FSx File System 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        file_system_id: 파일 시스템 ID
        file_system_arn: 파일 시스템 ARN
        file_system_type: 파일 시스템 유형 (LUSTRE, WINDOWS, ONTAP 등)
        lifecycle: 수명 주기 상태
        storage_capacity: 스토리지 용량 (GB)
        storage_type: 스토리지 유형 (SSD, HDD)
        vpc_id: 소속 VPC ID
        subnet_ids: 서브넷 ID 목록
        dns_name: DNS 이름
        kms_key_id: KMS 키 ID
        creation_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Transit Gateway 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        tgw_id: Transit Gateway ID
        tgw_arn: Transit Gateway ARN
        name: TGW Name 태그 값
        state: TGW 상태
        owner_id: 소유자 계정 ID
        description: TGW 설명
        amazon_side_asn: Amazon 측 ASN 번호
        default_route_table_id: 기본 라우트 테이블 ID
        auto_accept_shared_attachments: 공유 연결 자동 수락 설정
        dns_support: DNS 지원 설정
        vpn_ecmp_support: VPN ECMP 지원 설정
        creation_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Transit Gateway Attachment 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        attachment_id: Attachment ID
        tgw_id: 연결된 Transit Gateway ID
        resource_id: 연결된 리소스 ID (VPC, VPN 등)
        resource_type: 연결된 리소스 유형
        resource_owner_id: 리소스 소유자 계정 ID
        state: Attachment 상태
        association_state: 라우트 테이블 연결 상태
        creation_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """VPN Gateway 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        vpn_gateway_id: VPN Gateway ID
        name: VGW Name 태그 값
        state: VGW 상태
        vpn_type: VPN 유형 (ipsec.1 등)
        amazon_side_asn: Amazon 측 ASN 번호
        availability_zone: 가용 영역
        vpc_attachments: 연결된 VPC ID 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """VPN Connection 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        vpn_connection_id: VPN Connection ID
        name: VPN Connection Name 태그 값
        state: VPN 연결 상태
        vpn_type: VPN 유형
        customer_gateway_id: Customer Gateway ID
        vpn_gateway_id: VPN Gateway ID
        transit_gateway_id: Transit Gateway ID
        category: VPN 카테고리
        static_routes_only: 정적 라우팅 전용 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """Network ACL 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        nacl_id: Network ACL ID
        name: NACL Name 태그 값
        vpc_id: 소속 VPC ID
        is_default: 기본 NACL 여부
        inbound_rule_count: 인바운드 규칙 수
        outbound_rule_count: 아웃바운드 규칙 수
        associated_subnets: 연결된 서브넷 ID 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """VPC Peering Connection 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        peering_id: Peering Connection ID
        name: Peering Name 태그 값
        status: 피어링 상태
        requester_vpc_id: 요청자 VPC ID
        requester_owner_id: 요청자 계정 ID
        requester_cidr: 요청자 VPC CIDR
        accepter_vpc_id: 수락자 VPC ID
        accepter_owner_id: 수락자 계정 ID
        accepter_cidr: 수락자 VPC CIDR
        tags: 리소스 태그 딕셔너리
    """

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
    """SNS Topic 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        topic_arn: 토픽 ARN
        name: 토픽 이름
        display_name: 토픽 표시 이름
        subscriptions_confirmed: 확인된 구독 수
        subscriptions_pending: 대기 중인 구독 수
        kms_key_id: 암호화에 사용된 KMS 키 ID
        fifo_topic: FIFO 토픽 여부
        content_based_deduplication: 콘텐츠 기반 중복 제거 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """SQS Queue 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        queue_url: 큐 URL
        queue_arn: 큐 ARN
        name: 큐 이름
        fifo_queue: FIFO 큐 여부
        visibility_timeout: 가시성 타임아웃 (초)
        message_retention_period: 메시지 보존 기간 (초)
        max_message_size: 최대 메시지 크기 (바이트)
        delay_seconds: 메시지 지연 시간 (초)
        receive_message_wait_time: 수신 대기 시간 (초)
        approximate_number_of_messages: 대기 중인 메시지 수 (근사값)
        kms_key_id: 암호화에 사용된 KMS 키 ID
        dead_letter_target_arn: 데드 레터 큐 대상 ARN
        created_timestamp: 큐 생성 타임스탬프
        tags: 리소스 태그 딕셔너리
    """

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
    """EventBridge Rule 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        rule_name: 규칙 이름
        rule_arn: 규칙 ARN
        event_bus_name: 이벤트 버스 이름
        state: 규칙 상태 (ENABLED, DISABLED)
        description: 규칙 설명
        schedule_expression: 스케줄 표현식 (cron/rate)
        event_pattern: 이벤트 패턴 JSON
        target_count: 대상 수
        managed_by: 관리 서비스 식별자
        tags: 리소스 태그 딕셔너리
    """

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
    """Step Functions State Machine 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        state_machine_arn: 상태 머신 ARN
        name: 상태 머신 이름
        state_machine_type: 상태 머신 유형 (STANDARD, EXPRESS)
        status: 상태 머신 상태
        role_arn: 실행 역할 ARN
        logging_level: 로깅 레벨
        tracing_enabled: X-Ray 추적 활성화 여부
        creation_date: 생성 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """API Gateway REST/HTTP API 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        api_id: API ID
        name: API 이름
        api_type: API 유형 (REST, HTTP, WEBSOCKET)
        protocol_type: 프로토콜 유형
        endpoint_type: 엔드포인트 유형 (REGIONAL, EDGE, PRIVATE)
        description: API 설명
        version: API 버전
        api_endpoint: API 엔드포인트 URL
        disable_execute_api_endpoint: 기본 엔드포인트 비활성화 여부
        created_date: 생성 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """CloudWatch Alarm 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        alarm_name: 경보 이름
        alarm_arn: 경보 ARN
        state_value: 경보 상태 값 (OK, ALARM, INSUFFICIENT_DATA)
        metric_name: 메트릭 이름
        namespace: 메트릭 네임스페이스
        statistic: 통계 유형 (Average, Sum 등)
        period: 평가 기간 (초)
        threshold: 임계값
        comparison_operator: 비교 연산자
        evaluation_periods: 평가 기간 수
        datapoints_to_alarm: 경보 발생에 필요한 데이터포인트 수
        treat_missing_data: 누락 데이터 처리 방법
        actions_enabled: 경보 액션 활성화 여부
        alarm_actions: ALARM 상태 액션 ARN 목록
        insufficient_data_actions: INSUFFICIENT_DATA 상태 액션 ARN 목록
        ok_actions: OK 상태 액션 ARN 목록
        state_updated_timestamp: 상태 최종 변경 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """CloudWatch Log Group 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        log_group_name: 로그 그룹 이름
        log_group_arn: 로그 그룹 ARN
        stored_bytes: 저장된 데이터 크기 (바이트)
        retention_in_days: 보존 기간 (일, None이면 무기한)
        metric_filter_count: 메트릭 필터 수
        kms_key_id: 암호화에 사용된 KMS 키 ID
        creation_time: 생성 시간 (Unix 타임스탬프)
        tags: 리소스 태그 딕셔너리
    """

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
    """IAM Role 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 (항상 "global")
        role_id: IAM 역할 ID
        role_name: IAM 역할 이름
        role_arn: IAM 역할 ARN
        path: 역할 경로
        description: 역할 설명
        max_session_duration: 최대 세션 지속 시간 (초)
        create_date: 역할 생성 일시
        last_used_date: 마지막 사용 일시
        last_used_region: 마지막 사용 리전
        attached_policies_count: 연결된 관리형 정책 수
        inline_policies_count: 인라인 정책 수
        tags: 리소스 태그 딕셔너리
    """

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
    """IAM User 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 (항상 "global")
        user_id: IAM 사용자 ID
        user_name: IAM 사용자 이름
        user_arn: IAM 사용자 ARN
        path: 사용자 경로
        create_date: 사용자 생성 일시
        password_last_used: 콘솔 비밀번호 마지막 사용 일시
        has_console_access: 콘솔 로그인 활성화 여부
        has_access_keys: 액세스 키 보유 여부
        access_key_count: 액세스 키 수
        mfa_enabled: MFA 활성화 여부
        attached_policies_count: 연결된 관리형 정책 수
        inline_policies_count: 인라인 정책 수
        groups: 소속 그룹 이름 목록
        tags: 리소스 태그 딕셔너리
    """

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
    """IAM Policy 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 (항상 "global")
        policy_id: IAM 정책 ID
        policy_name: IAM 정책 이름
        policy_arn: IAM 정책 ARN
        path: 정책 경로
        description: 정책 설명
        is_attachable: 연결 가능 여부
        attachment_count: 연결된 엔터티 수
        permissions_boundary_usage_count: 권한 경계로 사용된 횟수
        default_version_id: 기본 정책 버전 ID
        create_date: 정책 생성 일시
        update_date: 정책 최종 수정 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """ACM Certificate 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        certificate_arn: 인증서 ARN
        domain_name: 주 도메인 이름
        status: 인증서 상태 (ISSUED, PENDING_VALIDATION 등)
        certificate_type: 인증서 유형 (AMAZON_ISSUED, IMPORTED 등)
        key_algorithm: 키 알고리즘 (RSA_2048, EC_prime256v1 등)
        issuer: 발급 기관
        subject_alternative_names: 대체 도메인 이름(SAN) 목록
        in_use_by: 인증서를 사용하는 리소스 ARN 목록
        not_before: 유효 기간 시작 일시
        not_after: 유효 기간 만료 일시
        created_at: 생성 일시
        renewal_eligibility: 갱신 자격 상태
        tags: 리소스 태그 딕셔너리
    """

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
    """WAF WebACL 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        web_acl_id: WebACL ID
        web_acl_arn: WebACL ARN
        name: WebACL 이름
        scope: 적용 범위 (REGIONAL, CLOUDFRONT)
        description: WebACL 설명
        capacity: WCU 용량
        rule_count: 규칙 수
        default_action: 기본 액션 (Allow, Block)
        visibility_config_metric_name: 가시성 설정 메트릭 이름
        managed_by_firewall_manager: Firewall Manager 관리 여부
        tags: 리소스 태그 딕셔너리
    """

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
    """Kinesis Data Stream 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        stream_name: 스트림 이름
        stream_arn: 스트림 ARN
        status: 스트림 상태
        stream_mode: 스트림 모드 (PROVISIONED, ON_DEMAND)
        shard_count: 샤드 수
        retention_period_hours: 데이터 보존 기간 (시간)
        encryption_type: 암호화 유형
        kms_key_id: KMS 키 ID
        stream_creation_timestamp: 스트림 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Kinesis Firehose Delivery Stream 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        delivery_stream_name: 전송 스트림 이름
        delivery_stream_arn: 전송 스트림 ARN
        delivery_stream_status: 전송 스트림 상태
        delivery_stream_type: 전송 스트림 유형
        source_type: 소스 유형
        destination_type: 대상 유형 (S3, Redshift, Elasticsearch 등)
        has_more_destinations: 추가 대상 존재 여부
        version_id: 버전 ID
        create_timestamp: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """Glue Database 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        database_name: 데이터베이스 이름
        catalog_id: Glue 카탈로그 ID
        description: 데이터베이스 설명
        location_uri: 데이터 위치 URI
        table_count: 테이블 수
        create_time: 생성 시간
        tags: 리소스 태그 딕셔너리
    """

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
    """CloudFormation Stack 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        stack_id: 스택 ID
        stack_name: 스택 이름
        stack_status: 스택 상태 (CREATE_COMPLETE 등)
        description: 스택 설명
        creation_time: 생성 시간
        last_updated_time: 마지막 업데이트 시간
        deletion_time: 삭제 시간
        parent_id: 부모 스택 ID (중첩 스택)
        root_id: 루트 스택 ID (중첩 스택)
        drift_status: 드리프트 감지 상태
        enable_termination_protection: 종료 보호 활성화 여부
        role_arn: 스택 실행 역할 ARN
        tags: 리소스 태그 딕셔너리
    """

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
    """CodePipeline 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        pipeline_name: 파이프라인 이름
        pipeline_arn: 파이프라인 ARN
        pipeline_version: 파이프라인 버전
        stage_count: 스테이지 수
        role_arn: 파이프라인 서비스 역할 ARN
        execution_mode: 실행 모드
        pipeline_type: 파이프라인 유형
        created: 생성 일시
        updated: 최종 수정 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """CodeBuild Project 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        project_name: 프로젝트 이름
        project_arn: 프로젝트 ARN
        description: 프로젝트 설명
        source_type: 소스 유형 (CODECOMMIT, GITHUB 등)
        source_location: 소스 위치 URL
        environment_type: 빌드 환경 유형
        compute_type: 컴퓨팅 유형 (BUILD_GENERAL1_SMALL 등)
        environment_image: 빌드 환경 이미지
        service_role: 서비스 역할 ARN
        timeout_in_minutes: 빌드 제한 시간 (분)
        queued_timeout_in_minutes: 큐 대기 제한 시간 (분)
        encryption_key: 암호화 키 ARN
        badge_enabled: 빌드 배지 활성화 여부
        last_modified: 마지막 수정 일시
        created: 생성 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """Backup Vault 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        vault_name: 백업 볼트 이름
        vault_arn: 백업 볼트 ARN
        encryption_key_arn: 암호화 키 ARN
        creator_request_id: 생성 요청 ID
        number_of_recovery_points: 복구 지점 수
        locked: 볼트 잠금 여부
        min_retention_days: 최소 보존 기간 (일)
        max_retention_days: 최대 보존 기간 (일)
        creation_date: 생성 일시
        tags: 리소스 태그 딕셔너리
    """

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
    """Backup Plan 정보

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        backup_plan_id: 백업 플랜 ID
        backup_plan_arn: 백업 플랜 ARN
        backup_plan_name: 백업 플랜 이름
        version_id: 플랜 버전 ID
        creator_request_id: 생성 요청 ID
        rule_count: 백업 규칙 수
        advanced_backup_settings: 고급 백업 설정 사용 여부
        creation_date: 생성 일시
        last_execution_date: 마지막 실행 일시
        tags: 리소스 태그 딕셔너리
    """

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
