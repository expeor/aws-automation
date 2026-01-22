"""
core/data/inventory/services - AWS Service-specific inventory collectors

Each service module provides collection functions for specific AWS resources.
"""

from .ec2 import collect_ec2_instances, collect_security_groups
from .elb import collect_classic_lbs, collect_load_balancers, collect_target_groups
from .vpc import collect_enis, collect_nat_gateways, collect_vpc_endpoints

__all__ = [
    # EC2
    "collect_ec2_instances",
    "collect_security_groups",
    # VPC
    "collect_enis",
    "collect_nat_gateways",
    "collect_vpc_endpoints",
    # ELB
    "collect_load_balancers",
    "collect_classic_lbs",
    "collect_target_groups",
]
