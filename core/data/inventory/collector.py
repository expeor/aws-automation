"""
core/data/inventory/collector.py - Unified Inventory Collector

Orchestrates resource collection across multiple services with caching support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.parallel import parallel_collect

from .cache import ResourceCache, get_global_cache
from .services.ec2 import collect_ec2_instances, collect_security_groups
from .services.elb import collect_classic_lbs, collect_load_balancers, collect_target_groups
from .services.vpc import collect_enis, collect_nat_gateways, collect_vpc_endpoints
from .types import (
    EC2Instance,
    LoadBalancer,
    NATGateway,
    NetworkInterface,
    SecurityGroup,
    TargetGroup,
    VPCEndpoint,
)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext


class InventoryCollector:
    """Unified resource inventory collector with caching

    Provides a single interface for collecting AWS resources across services.
    Automatically caches results to reduce API calls when the same data
    is needed by multiple analysis tools.

    Example:
        collector = InventoryCollector(ctx)

        # Collect with caching (uses cache if available)
        instances = collector.collect_ec2()

        # Force refresh (ignores cache)
        instances = collector.collect_ec2(force_refresh=True)

        # Check cache stats
        print(collector.cache.stats)
    """

    def __init__(
        self,
        ctx: "ExecutionContext",
        cache: ResourceCache | None = None,
    ):
        """Initialize collector

        Args:
            ctx: Execution context with auth and region info
            cache: Optional ResourceCache (uses global cache if not provided)
        """
        self._ctx = ctx
        self._cache = cache or get_global_cache()

    @property
    def cache(self) -> ResourceCache:
        """Get the cache instance"""
        return self._cache

    # =========================================================================
    # EC2 Resources
    # =========================================================================

    def collect_ec2(self, force_refresh: bool = False) -> list[EC2Instance]:
        """Collect EC2 instances across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of EC2Instance objects
        """
        cache_key = self._make_cache_key("ec2_instances")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_ec2_instances,
            max_workers=20,
            service="ec2",
        )

        instances = self._flatten_results(results.get_data())
        self._cache.set(cache_key, instances)
        return instances

    def collect_security_groups(self, force_refresh: bool = False) -> list[SecurityGroup]:
        """Collect Security Groups across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of SecurityGroup objects
        """
        cache_key = self._make_cache_key("security_groups")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_security_groups,
            max_workers=20,
            service="ec2",
        )

        sgs = self._flatten_results(results.get_data())
        self._cache.set(cache_key, sgs)
        return sgs

    # =========================================================================
    # VPC Resources
    # =========================================================================

    def collect_enis(self, force_refresh: bool = False) -> list[NetworkInterface]:
        """Collect Elastic Network Interfaces across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of NetworkInterface objects
        """
        cache_key = self._make_cache_key("enis")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_enis,
            max_workers=20,
            service="ec2",
        )

        enis = self._flatten_results(results.get_data())
        self._cache.set(cache_key, enis)
        return enis

    def collect_nat_gateways(self, force_refresh: bool = False) -> list[NATGateway]:
        """Collect NAT Gateways across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of NATGateway objects
        """
        cache_key = self._make_cache_key("nat_gateways")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_nat_gateways,
            max_workers=20,
            service="ec2",
        )

        nats = self._flatten_results(results.get_data())
        self._cache.set(cache_key, nats)
        return nats

    def collect_vpc_endpoints(self, force_refresh: bool = False) -> list[VPCEndpoint]:
        """Collect VPC Endpoints across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of VPCEndpoint objects
        """
        cache_key = self._make_cache_key("vpc_endpoints")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_vpc_endpoints,
            max_workers=20,
            service="ec2",
        )

        endpoints = self._flatten_results(results.get_data())
        self._cache.set(cache_key, endpoints)
        return endpoints

    # =========================================================================
    # ELB Resources
    # =========================================================================

    def collect_load_balancers(
        self,
        force_refresh: bool = False,
        include_classic: bool = True,
    ) -> list[LoadBalancer]:
        """Collect all Load Balancers (ALB/NLB/GWLB/CLB) across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            include_classic: If True, include Classic Load Balancers

        Returns:
            List of LoadBalancer objects
        """
        cache_key = self._make_cache_key("load_balancers" + ("_with_clb" if include_classic else ""))

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Collect ELBv2 (ALB/NLB/GWLB)
        v2_results = parallel_collect(
            self._ctx,
            collect_load_balancers,
            max_workers=20,
            service="elasticloadbalancing",
        )
        load_balancers = self._flatten_results(v2_results.get_data())

        # Collect CLB if requested
        if include_classic:
            clb_results = parallel_collect(
                self._ctx,
                collect_classic_lbs,
                max_workers=20,
                service="elb",
            )
            load_balancers.extend(self._flatten_results(clb_results.get_data()))

        self._cache.set(cache_key, load_balancers)
        return load_balancers

    def collect_target_groups(self, force_refresh: bool = False) -> list[TargetGroup]:
        """Collect Target Groups across all regions

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of TargetGroup objects
        """
        cache_key = self._make_cache_key("target_groups")

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = parallel_collect(
            self._ctx,
            collect_target_groups,
            max_workers=20,
            service="elasticloadbalancing",
        )

        tgs = self._flatten_results(results.get_data())
        self._cache.set(cache_key, tgs)
        return tgs

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def collect_all_network_resources(
        self,
        force_refresh: bool = False,
    ) -> dict[str, list[Any]]:
        """Collect all network-related resources

        Returns:
            Dict with keys: enis, nat_gateways, vpc_endpoints, security_groups
        """
        return {
            "enis": self.collect_enis(force_refresh),
            "nat_gateways": self.collect_nat_gateways(force_refresh),
            "vpc_endpoints": self.collect_vpc_endpoints(force_refresh),
            "security_groups": self.collect_security_groups(force_refresh),
        }

    def collect_all_elb_resources(
        self,
        force_refresh: bool = False,
    ) -> dict[str, list[Any]]:
        """Collect all ELB-related resources

        Returns:
            Dict with keys: load_balancers, target_groups
        """
        return {
            "load_balancers": self.collect_load_balancers(force_refresh),
            "target_groups": self.collect_target_groups(force_refresh),
        }

    def invalidate(self, pattern: str = "*") -> int:
        """Invalidate cache entries

        Args:
            pattern: Glob pattern for keys to invalidate

        Returns:
            Number of entries invalidated
        """
        return self._cache.invalidate(pattern)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _make_cache_key(self, resource_type: str) -> str:
        """Generate cache key based on context

        Key format: {resource_type}:{account_ids}:{regions}
        """
        # Get account identifier
        if self._ctx.is_sso_session() and self._ctx.accounts:
            account_ids = ",".join(sorted(acc.id for acc in self._ctx.get_target_accounts()))
        elif self._ctx.profile_name:
            account_ids = self._ctx.profile_name
        else:
            account_ids = "default"

        # Get regions
        regions = ",".join(sorted(self._ctx.regions)) if self._ctx.regions else "all"

        return f"{resource_type}:{account_ids}:{regions}"

    def _flatten_results(self, results: list[list[Any]]) -> list[Any]:
        """Flatten nested lists from parallel collection"""
        flattened = []
        for result in results:
            if result is not None:
                if isinstance(result, list):
                    flattened.extend(result)
                else:
                    flattened.append(result)
        return flattened
