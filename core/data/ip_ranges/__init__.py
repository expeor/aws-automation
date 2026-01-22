"""
core/data/ip_ranges - Cloud Provider Public IP Ranges

Centralized data service for cloud provider IP ranges.
Supports AWS, GCP, Azure, and Oracle Cloud.

Usage:
    from core.data.ip_ranges import (
        search_public_ip,
        search_by_filter,
        get_available_filters,
        get_public_cache_status,
        refresh_public_cache,
        clear_public_cache,
    )

    # Search for IP in cloud ranges
    results = search_public_ip(["52.94.76.1"])

    # Filter by provider/region/service
    aws_s3_ranges = search_by_filter(provider="aws", service="S3")
"""

from .providers import (
    # Data types
    PublicIPResult,
    # Cache management
    clear_public_cache,
    get_public_cache_status,
    refresh_public_cache,
    # Provider data loaders
    get_aws_ip_ranges,
    get_azure_ip_ranges,
    get_gcp_ip_ranges,
    get_oracle_ip_ranges,
    load_ip_ranges_parallel,
    # Search functions
    search_by_filter,
    search_in_aws,
    search_in_azure,
    search_in_gcp,
    search_in_oracle,
    search_public_ip,
    # Filter helpers
    get_available_filters,
    list_aws_regions,
    list_aws_services,
)

__all__ = [
    # Data types
    "PublicIPResult",
    # Cache management
    "clear_public_cache",
    "get_public_cache_status",
    "refresh_public_cache",
    # Provider data loaders
    "get_aws_ip_ranges",
    "get_gcp_ip_ranges",
    "get_azure_ip_ranges",
    "get_oracle_ip_ranges",
    "load_ip_ranges_parallel",
    # Search functions
    "search_public_ip",
    "search_in_aws",
    "search_in_gcp",
    "search_in_azure",
    "search_in_oracle",
    "search_by_filter",
    # Filter helpers
    "get_available_filters",
    "list_aws_regions",
    "list_aws_services",
]
