"""
core/data - Data Services Layer

Centralized data collection, caching, and management services.

Modules:
    - inventory: Resource inventory collection and caching
    - pricing: AWS Pricing API services
    - cloudwatch: CloudWatch metrics collection
    - ip_ranges: Cloud provider public IP ranges

Design Principle:
    core/ = How (infrastructure) + Data (shared services)
    plugins/ = What (analysis features)

Usage:
    # Inventory
    from core.data.inventory import InventoryCollector, ResourceCache

    # Pricing (canonical path)
    from core.data.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost

    # CloudWatch (canonical path)
    from core.data.cloudwatch import MetricQuery, batch_get_metrics

    # Public IP ranges
    from core.data.ip_ranges import search_public_ip, get_public_cache_status
"""

from .inventory import InventoryCollector, ResourceCache

# Re-export commonly used pricing functions for convenience
from .pricing import (
    get_ec2_monthly_cost,
    get_ebs_monthly_cost,
    get_elb_monthly_cost,
    get_nat_monthly_cost,
    get_endpoint_monthly_cost,
)

# Re-export CloudWatch utilities
from .cloudwatch import MetricQuery, batch_get_metrics

# Re-export IP ranges utilities
from .ip_ranges import (
    PublicIPResult,
    search_public_ip,
    get_public_cache_status,
    refresh_public_cache,
    clear_public_cache,
)

__all__ = [
    # Inventory
    "InventoryCollector",
    "ResourceCache",
    # Pricing (commonly used)
    "get_ec2_monthly_cost",
    "get_ebs_monthly_cost",
    "get_elb_monthly_cost",
    "get_nat_monthly_cost",
    "get_endpoint_monthly_cost",
    # CloudWatch
    "MetricQuery",
    "batch_get_metrics",
    # IP Ranges
    "PublicIPResult",
    "search_public_ip",
    "get_public_cache_status",
    "refresh_public_cache",
    "clear_public_cache",
]
