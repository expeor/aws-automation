"""
plugins/vpc/ip_search/common/ip_ranges - Cloud Provider Public IP Ranges

클라우드 프로바이더별 공용 IP 대역 검색 서비스.
AWS, GCP, Azure, Oracle Cloud, Cloudflare, Fastly 지원.

Usage:
    from plugins.vpc.ip_search.common.ip_ranges import (
        search_public_ip,
        search_public_ip_optimized,  # Radix Tree / Binary Search
        search_by_filter,
        get_available_filters,
        get_public_cache_status,
        refresh_public_cache,
        clear_public_cache,
    )

    # Search for IP in cloud ranges (original linear search)
    results = search_public_ip(["52.94.76.1"])

    # Optimized search (Radix Tree / Binary Search)
    results = search_public_ip_optimized(["52.94.76.1"])

    # Filter by provider/region/service
    aws_s3_ranges = search_by_filter(provider="aws", service="S3")
"""

from .providers import (
    # Data types
    PublicIPResult,
    # Cache management
    clear_public_cache,
    # Filter helpers
    get_available_filters,
    # Provider data loaders
    get_aws_ip_ranges,
    get_azure_ip_ranges,
    get_cloudflare_ip_ranges,
    get_fastly_ip_ranges,
    get_gcp_ip_ranges,
    get_oracle_ip_ranges,
    get_public_cache_status,
    get_search_backend,
    list_aws_regions,
    list_aws_services,
    load_ip_ranges_parallel,
    refresh_public_cache,
    # Search functions
    search_by_filter,
    search_in_aws,
    search_in_azure,
    search_in_cloudflare,
    search_in_fastly,
    search_in_gcp,
    search_in_oracle,
    search_public_ip,
    search_public_ip_optimized,
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
    "get_cloudflare_ip_ranges",
    "get_fastly_ip_ranges",
    "load_ip_ranges_parallel",
    # Search functions
    "search_public_ip",
    "search_public_ip_optimized",
    "search_in_aws",
    "search_in_gcp",
    "search_in_azure",
    "search_in_oracle",
    "search_in_cloudflare",
    "search_in_fastly",
    "search_by_filter",
    "get_search_backend",
    # Filter helpers
    "get_available_filters",
    "list_aws_regions",
    "list_aws_services",
]
