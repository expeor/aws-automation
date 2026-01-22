"""
core/data/inventory/types.py - Resource dataclasses for inventory

Standardized dataclasses for AWS resources used across the toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EC2Instance:
    """EC2 Instance information"""

    instance_id: str
    instance_type: str
    state: str
    name: str = ""
    private_ip: str = ""
    public_ip: str = ""
    vpc_id: str = ""
    subnet_id: str = ""
    availability_zone: str = ""
    platform: str = ""
    launch_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)
    security_groups: list[str] = field(default_factory=list)

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_running(self) -> bool:
        return self.state == "running"

    @property
    def is_stopped(self) -> bool:
        return self.state == "stopped"


@dataclass
class SecurityGroup:
    """Security Group information"""

    group_id: str
    group_name: str
    vpc_id: str
    description: str = ""
    owner_id: str = ""
    inbound_rules: list[dict[str, Any]] = field(default_factory=list)
    outbound_rules: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    # Usage tracking
    attached_enis: list[str] = field(default_factory=list)

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_default(self) -> bool:
        return self.group_name == "default"

    @property
    def is_in_use(self) -> bool:
        return len(self.attached_enis) > 0


@dataclass
class NetworkInterface:
    """Elastic Network Interface (ENI) information"""

    eni_id: str
    status: str
    vpc_id: str
    subnet_id: str
    availability_zone: str = ""
    description: str = ""
    private_ip: str = ""
    public_ip: str = ""
    interface_type: str = ""
    requester_id: str = ""
    owner_id: str = ""
    instance_id: str = ""
    attachment_status: str = ""
    security_groups: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    name: str = ""

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_available(self) -> bool:
        return self.status == "available"

    @property
    def is_attached(self) -> bool:
        return self.status == "in-use"

    @property
    def is_aws_managed(self) -> bool:
        """Check if ENI is AWS-managed (NAT Gateway, Lambda, etc.)"""
        if self.requester_id and self.requester_id != self.owner_id:
            return True
        aws_managed_types = {
            "nat_gateway",
            "gateway_load_balancer",
            "gateway_load_balancer_endpoint",
            "vpc_endpoint",
            "efa",
            "trunk",
            "load_balancer",
            "lambda",
        }
        return self.interface_type in aws_managed_types


@dataclass
class NATGateway:
    """NAT Gateway information"""

    nat_gateway_id: str
    vpc_id: str
    subnet_id: str
    state: str
    connectivity_type: str = ""  # public or private
    public_ip: str = ""
    private_ip: str = ""
    create_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)
    name: str = ""

    # Metrics
    bytes_out_to_destination: float = 0.0
    bytes_out_to_source: float = 0.0

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_available(self) -> bool:
        return self.state == "available"


@dataclass
class VPCEndpoint:
    """VPC Endpoint information"""

    endpoint_id: str
    endpoint_type: str  # Interface, Gateway, GatewayLoadBalancer
    service_name: str
    vpc_id: str
    state: str
    creation_time: datetime | None = None
    name: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    # For Interface endpoints
    subnet_ids: list[str] = field(default_factory=list)
    network_interface_ids: list[str] = field(default_factory=list)
    private_dns_enabled: bool = False

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_interface(self) -> bool:
        return self.endpoint_type == "Interface"

    @property
    def is_gateway(self) -> bool:
        return self.endpoint_type == "Gateway"

    @property
    def is_available(self) -> bool:
        return self.state == "available"


@dataclass
class TargetGroup:
    """Target Group information"""

    arn: str
    name: str
    target_type: str
    protocol: str = ""
    port: int = 0
    vpc_id: str = ""
    health_check_enabled: bool = True

    # Target counts
    total_targets: int = 0
    healthy_targets: int = 0
    unhealthy_targets: int = 0

    # Associated load balancers
    load_balancer_arns: list[str] = field(default_factory=list)

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_orphaned(self) -> bool:
        return len(self.load_balancer_arns) == 0

    @property
    def is_empty(self) -> bool:
        return self.total_targets == 0

    @property
    def is_all_unhealthy(self) -> bool:
        return self.total_targets > 0 and self.healthy_targets == 0


@dataclass
class LoadBalancer:
    """Load Balancer information (ALB/NLB/CLB/GWLB)"""

    arn: str
    name: str
    dns_name: str
    lb_type: str  # application, network, gateway, classic
    scheme: str  # internet-facing, internal
    state: str
    vpc_id: str
    availability_zones: list[str] = field(default_factory=list)
    created_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)

    # Target groups (ALB/NLB/GWLB)
    target_groups: list[TargetGroup] = field(default_factory=list)

    # CLB specific
    registered_instances: int = 0
    healthy_instances: int = 0

    # Metadata
    account_id: str = ""
    account_name: str = ""
    region: str = ""

    @property
    def is_active(self) -> bool:
        return self.state in ("active", "")

    @property
    def total_targets(self) -> int:
        if self.lb_type == "classic":
            return self.registered_instances
        return sum(tg.total_targets for tg in self.target_groups)

    @property
    def healthy_targets(self) -> int:
        if self.lb_type == "classic":
            return self.healthy_instances
        return sum(tg.healthy_targets for tg in self.target_groups)

    @property
    def is_unused(self) -> bool:
        return self.total_targets == 0

    @property
    def is_all_unhealthy(self) -> bool:
        return self.total_targets > 0 and self.healthy_targets == 0
