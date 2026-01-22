"""
core/data/inventory - Resource Inventory Collection and Caching

Provides centralized resource inventory collection with TTL-based caching
to reduce API calls across multiple analysis tools.

Classes:
    - ResourceCache: TTL-based cache for resource data
    - InventoryCollector: Collects and caches AWS resources

Usage:
    from core.data.inventory import InventoryCollector, ResourceCache

    # Basic usage (auto-managed cache)
    collector = InventoryCollector(ctx)
    ec2_instances = collector.collect_ec2()
    security_groups = collector.collect_security_groups()

    # With custom cache
    cache = ResourceCache(ttl_minutes=60)
    collector = InventoryCollector(ctx, cache=cache)
"""

from .cache import CacheConfig, ResourceCache
from .collector import InventoryCollector
from .types import (
    EC2Instance,
    LoadBalancer,
    NATGateway,
    NetworkInterface,
    SecurityGroup,
    TargetGroup,
    VPCEndpoint,
)

__all__ = [
    # Cache
    "CacheConfig",
    "ResourceCache",
    # Collector
    "InventoryCollector",
    # Types
    "EC2Instance",
    "SecurityGroup",
    "NetworkInterface",
    "NATGateway",
    "VPCEndpoint",
    "LoadBalancer",
    "TargetGroup",
]
