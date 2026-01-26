"""
plugins/vpc/ip_search/common/ip_ranges/providers.py - Cloud Provider IP Range Services

클라우드 프로바이더별 IP 대역 데이터 서비스:
- AWS, GCP, Azure, Oracle Cloud

Features:
- 24시간 캐시로 빠른 응답
- 병렬 데이터 로딩
- CIDR 및 단일 IP 검색
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PublicIPResult:
    """Public IP search result"""

    ip_address: str
    provider: str  # AWS, GCP, Azure, Oracle, Unknown
    service: str
    ip_prefix: str
    region: str
    extra: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Cache Management
# =============================================================================


def _get_cache_dir() -> str:
    """Get cache directory path (project root's temp folder)"""
    # plugins/vpc/ip_search/common/ip_ranges -> ip_ranges -> common -> ip_search -> vpc -> plugins -> project_root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    )
    cache_dir = os.path.join(project_root, "temp", "ip_ranges")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _load_from_cache(name: str, max_age_hours: int = 24) -> dict | None:
    """Load data from cache"""
    cache_file = os.path.join(_get_cache_dir(), f"{name}.json")
    if not os.path.exists(cache_file):
        return None

    cache_age = time.time() - os.path.getmtime(cache_file)
    if cache_age > max_age_hours * 3600:
        return None

    try:
        with open(cache_file, encoding="utf-8") as f:
            data: dict[Any, Any] = json.load(f)
            return data
    except Exception as e:
        logger.debug("Failed to load cache %s: %s", name, e)
        return None


def _save_to_cache(name: str, data: dict) -> None:
    """Save data to cache"""
    cache_file = os.path.join(_get_cache_dir(), f"{name}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug("Cache operation failed: %s", e)


def clear_public_cache() -> int:
    """Clear all public IP caches (returns deleted file count)"""
    cache_dir = _get_cache_dir()
    count = 0
    for name in ["aws", "gcp", "azure", "oracle"]:
        cache_file = os.path.join(cache_dir, f"{name}.json")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                count += 1
            except Exception as e:
                logger.debug("Cache delete failed: %s", e)
    return count


def refresh_public_cache(callback=None) -> dict[str, Any]:
    """
    Refresh public IP cache (delete and re-download)

    Args:
        callback: Progress callback function (provider, status)

    Returns:
        {"success": [...], "failed": [...], "counts": {...}}
    """
    providers = ["aws", "gcp", "azure", "oracle"]
    result: dict[str, Any] = {"success": [], "failed": [], "counts": {}}

    # Clear cache first
    clear_public_cache()

    # Download each provider's data
    loaders = {
        "aws": lambda: _fetch_and_cache("aws", "https://ip-ranges.amazonaws.com/ip-ranges.json"),
        "gcp": lambda: _fetch_and_cache("gcp", "https://www.gstatic.com/ipranges/cloud.json"),
        "azure": _fetch_azure_fresh,
        "oracle": lambda: _fetch_and_cache("oracle", "https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json"),
    }

    for provider in providers:
        if callback:
            callback(provider, "downloading")

        try:
            data = loaders[provider]()
            if data:
                # Calculate count
                if provider == "aws" or provider == "gcp":
                    count = len(data.get("prefixes", []))
                elif provider == "azure":
                    count = len(data.get("values", []))
                elif provider == "oracle":
                    count = sum(len(r.get("cidrs", [])) for r in data.get("regions", []))
                else:
                    count = 0

                result["success"].append(provider.upper())
                result["counts"][provider.upper()] = count
            else:
                result["failed"].append(provider.upper())
        except Exception as e:
            logger.debug("Failed to refresh %s: %s", provider, e)
            result["failed"].append(provider.upper())

    return result


def _fetch_and_cache(name: str, url: str) -> dict[Any, Any] | None:
    """Download data from URL and save to cache"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data: dict[Any, Any] = response.json()
            _save_to_cache(name, data)
            return data
    except Exception as e:
        logger.debug("Cache operation failed: %s", e)
    return None


def _fetch_azure_fresh() -> dict[Any, Any] | None:
    """Download Azure data (weekly update URL search)"""
    from datetime import datetime, timedelta

    base_url = (
        "https://download.microsoft.com/download/7/1/d/71d86715-5596-4529-9b13-da13a5de5b63/ServiceTags_Public_{}.json"
    )

    for weeks_back in range(5):
        for day_offset in range(7):
            try_date = datetime.now() - timedelta(weeks=weeks_back, days=day_offset)
            url = base_url.format(try_date.strftime("%Y%m%d"))

            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    data: dict[Any, Any] = response.json()
                    if data.get("values"):
                        _save_to_cache("azure", data)
                        return data
            except Exception as e:
                logger.debug("Network operation failed: %s", e)
                continue

    return None


def get_public_cache_status() -> dict[str, Any]:
    """Get public IP cache status"""
    from datetime import datetime

    cache_dir = _get_cache_dir()
    providers = ["aws", "gcp", "azure", "oracle"]
    status: dict[str, Any] = {"providers": {}, "total_files": 0}

    for name in providers:
        cache_file = os.path.join(cache_dir, f"{name}.json")
        if os.path.exists(cache_file):
            try:
                mtime = os.path.getmtime(cache_file)
                cache_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                age_hours = (time.time() - mtime) / 3600
                is_valid = age_hours < 24

                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Calculate prefix count for each provider
                    if name == "aws" or name == "gcp":
                        count = len(data.get("prefixes", []))
                    elif name == "azure":
                        count = len(data.get("values", []))
                    elif name == "oracle":
                        count = sum(len(r.get("cidrs", [])) for r in data.get("regions", []))
                    else:
                        count = 0

                status["providers"][name.upper()] = {
                    "cached": True,
                    "time": cache_time,
                    "valid": is_valid,
                    "count": count,
                }
                status["total_files"] += 1
            except Exception as e:
                logger.debug("Failed to read cache status for %s: %s", name, e)
                status["providers"][name.upper()] = {"cached": False}
        else:
            status["providers"][name.upper()] = {"cached": False}

    return status


# =============================================================================
# Cloud Provider IP Range Loaders
# =============================================================================


def get_aws_ip_ranges() -> dict[str, Any]:
    """Get AWS IP ranges"""
    cached = _load_from_cache("aws")
    if cached:
        return cached

    try:
        response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json", timeout=5)
        data: dict[str, Any] = response.json()
        _save_to_cache("aws", data)
        return data
    except Exception as e:
        logger.debug("Failed to fetch AWS IP ranges: %s", e)
        return {"prefixes": [], "ipv6_prefixes": []}


def get_gcp_ip_ranges() -> dict[str, Any]:
    """Get GCP IP ranges"""
    cached = _load_from_cache("gcp")
    if cached:
        return cached

    try:
        response = requests.get("https://www.gstatic.com/ipranges/cloud.json", timeout=10)
        data: dict[str, Any] = response.json()
        _save_to_cache("gcp", data)
        return data
    except Exception as e:
        logger.debug("Failed to fetch GCP IP ranges: %s", e)
        return {"prefixes": []}


def get_azure_ip_ranges() -> dict[str, Any]:
    """Get Azure IP ranges (weekly update)"""
    cached = _load_from_cache("azure")
    if cached and cached.get("values"):
        return cached

    from datetime import datetime, timedelta

    base_url = (
        "https://download.microsoft.com/download/7/1/d/71d86715-5596-4529-9b13-da13a5de5b63/ServiceTags_Public_{}.json"
    )

    for weeks_back in range(5):
        for day_offset in range(7):
            try_date = datetime.now() - timedelta(weeks=weeks_back, days=day_offset)
            url = base_url.format(try_date.strftime("%Y%m%d"))

            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data: dict[str, Any] = response.json()
                    if data.get("values"):
                        _save_to_cache("azure", data)
                        return data
            except Exception as e:
                logger.debug("Network operation failed: %s", e)
                continue

    return {"values": []}


def get_oracle_ip_ranges() -> dict[str, Any]:
    """Get Oracle Cloud IP ranges"""
    cached = _load_from_cache("oracle")
    if cached:
        return cached

    try:
        response = requests.get("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json", timeout=10)
        data: dict[str, Any] = response.json()
        _save_to_cache("oracle", data)
        return data
    except Exception as e:
        logger.debug("Failed to fetch Oracle IP ranges: %s", e)
        return {"regions": []}


# =============================================================================
# IP Search Functions
# =============================================================================


def search_in_aws(ip: str, data: dict[str, Any]) -> list[PublicIPResult]:
    """Search in AWS IP ranges"""
    results: list[PublicIPResult] = []
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return results

    prefixes = data.get("prefixes", []) if ip_obj.version == 4 else data.get("ipv6_prefixes", [])
    prefix_key = "ip_prefix" if ip_obj.version == 4 else "ipv6_prefix"

    for prefix in prefixes:
        try:
            network = ipaddress.ip_network(prefix[prefix_key])
            if ip_obj in network:
                results.append(
                    PublicIPResult(
                        ip_address=ip,
                        provider="AWS",
                        service=prefix.get("service", ""),
                        ip_prefix=prefix[prefix_key],
                        region=prefix.get("region", ""),
                        extra={"network_border_group": prefix.get("network_border_group", "")},
                    )
                )
        except (ValueError, KeyError):
            continue

    return results


def search_in_gcp(ip: str, data: dict[str, Any]) -> list[PublicIPResult]:
    """Search in GCP IP ranges"""
    results: list[PublicIPResult] = []
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return results

    for prefix in data.get("prefixes", []):
        prefix_key = "ipv4Prefix" if ip_obj.version == 4 else "ipv6Prefix"
        if prefix_key not in prefix:
            continue

        try:
            network = ipaddress.ip_network(prefix[prefix_key])
            if ip_obj in network:
                results.append(
                    PublicIPResult(
                        ip_address=ip,
                        provider="GCP",
                        service=prefix.get("service", "Google Cloud"),
                        ip_prefix=prefix[prefix_key],
                        region=prefix.get("scope", ""),
                    )
                )
        except ValueError:
            continue

    return results


def search_in_azure(ip: str, data: dict[str, Any]) -> list[PublicIPResult]:
    """Search in Azure IP ranges"""
    results: list[PublicIPResult] = []
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return results

    for service in data.get("values", []):
        service_name = service.get("name", "Azure")
        region = service.get("properties", {}).get("region", "Global")

        for prefix in service.get("properties", {}).get("addressPrefixes", []):
            try:
                network = ipaddress.ip_network(prefix)
                if ip_obj in network:
                    results.append(
                        PublicIPResult(
                            ip_address=ip,
                            provider="Azure",
                            service=service_name,
                            ip_prefix=prefix,
                            region=region,
                        )
                    )
            except ValueError:
                continue

    return results


def search_in_oracle(ip: str, data: dict[str, Any]) -> list[PublicIPResult]:
    """Search in Oracle Cloud IP ranges"""
    results: list[PublicIPResult] = []
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return results

    for region in data.get("regions", []):
        region_name = region.get("region", "Unknown")

        for cidr_obj in region.get("cidrs", []):
            cidr = cidr_obj.get("cidr", "")
            tags = cidr_obj.get("tags", [])

            try:
                network = ipaddress.ip_network(cidr)
                if ip_obj in network:
                    service = ", ".join(tags) if tags else "Oracle Cloud"
                    results.append(
                        PublicIPResult(
                            ip_address=ip,
                            provider="Oracle",
                            service=service,
                            ip_prefix=cidr,
                            region=region_name,
                        )
                    )
            except ValueError:
                continue

    return results


# =============================================================================
# Main Search Functions
# =============================================================================


def load_ip_ranges_parallel(target_providers: set[str]) -> dict[str, dict[str, Any]]:
    """Load IP range data in parallel"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    loaders = {
        "aws": get_aws_ip_ranges,
        "gcp": get_gcp_ip_ranges,
        "azure": get_azure_ip_ranges,
        "oracle": get_oracle_ip_ranges,
    }

    data_sources: dict[str, dict[str, Any]] = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(loaders[p]): p for p in target_providers if p in loaders}

        for future in as_completed(futures):
            provider = futures[future]
            try:
                data_sources[provider] = future.result()
            except Exception as e:
                logger.debug("Failed to load %s IP ranges: %s", provider, e)
                data_sources[provider] = {}

    return data_sources


def search_public_ip(
    ip_list: list[str],
    providers: list[str] | None = None,
) -> list[PublicIPResult]:
    """
    Search public IP ranges

    Args:
        ip_list: List of IP addresses to search
        providers: List of providers to search (None for all)

    Returns:
        List of search results
    """
    all_providers = {"aws", "gcp", "azure", "oracle"}
    target_providers = {p.lower() for p in providers} & all_providers if providers else all_providers

    data_sources = load_ip_ranges_parallel(target_providers)

    all_results = []

    for ip in ip_list:
        ip = ip.strip()
        if not ip:
            continue

        found = False

        if "aws" in data_sources:
            results = search_in_aws(ip, data_sources["aws"])
            if results:
                all_results.extend(results)
                found = True

        if "gcp" in data_sources:
            results = search_in_gcp(ip, data_sources["gcp"])
            if results:
                all_results.extend(results)
                found = True

        if "azure" in data_sources:
            results = search_in_azure(ip, data_sources["azure"])
            if results:
                all_results.extend(results)
                found = True

        if "oracle" in data_sources:
            results = search_in_oracle(ip, data_sources["oracle"])
            if results:
                all_results.extend(results)
                found = True

        if not found:
            all_results.append(
                PublicIPResult(
                    ip_address=ip,
                    provider="Unknown",
                    service="",
                    ip_prefix="",
                    region="",
                )
            )

    return all_results


def list_aws_regions(data: dict) -> list[str]:
    """Get unique region list from AWS IP ranges"""
    regions = set()
    for prefix in data.get("prefixes", []):
        region = prefix.get("region", "")
        if region:
            regions.add(region)
    return sorted(regions)


def list_aws_services(data: dict) -> list[str]:
    """Get unique service list from AWS IP ranges"""
    services = set()
    for prefix in data.get("prefixes", []):
        service = prefix.get("service", "")
        if service:
            services.add(service)
    return sorted(services)


def search_by_filter(
    provider: str = "aws",
    region: str | None = None,
    service: str | None = None,
) -> list[PublicIPResult]:
    """
    Search IP ranges by region or service

    Args:
        provider: Cloud provider (aws, gcp, azure, oracle)
        region: Region filter (partial match)
        service: Service filter (partial match)

    Returns:
        List of matching IP ranges
    """
    provider = provider.lower()

    # Load data
    loaders = {
        "aws": get_aws_ip_ranges,
        "gcp": get_gcp_ip_ranges,
        "azure": get_azure_ip_ranges,
        "oracle": get_oracle_ip_ranges,
    }

    if provider not in loaders:
        return []

    data = loaders[provider]()
    results: list[PublicIPResult] = []

    if provider == "aws":
        for prefix in data.get("prefixes", []):
            p_region = prefix.get("region", "")
            p_service = prefix.get("service", "")
            ip_prefix = prefix.get("ip_prefix", "")

            # Check filter conditions
            if region and region.lower() not in p_region.lower():
                continue
            if service and service.lower() not in p_service.lower():
                continue

            results.append(
                PublicIPResult(
                    ip_address="",
                    provider="AWS",
                    service=p_service,
                    ip_prefix=ip_prefix,
                    region=p_region,
                    extra={"network_border_group": prefix.get("network_border_group", "")},
                )
            )

    elif provider == "gcp":
        for prefix in data.get("prefixes", []):
            p_scope = prefix.get("scope", "")
            p_service = prefix.get("service", "Google Cloud")
            ip_prefix = prefix.get("ipv4Prefix", "") or prefix.get("ipv6Prefix", "")

            if region and region.lower() not in p_scope.lower():
                continue
            if service and service.lower() not in p_service.lower():
                continue

            results.append(
                PublicIPResult(
                    ip_address="",
                    provider="GCP",
                    service=p_service,
                    ip_prefix=ip_prefix,
                    region=p_scope,
                )
            )

    elif provider == "azure":
        for svc in data.get("values", []):
            svc_name = svc.get("name", "Azure")
            svc_region = svc.get("properties", {}).get("region", "Global")

            if region and region.lower() not in svc_region.lower():
                continue
            if service and service.lower() not in svc_name.lower():
                continue

            for ip_prefix in svc.get("properties", {}).get("addressPrefixes", []):
                results.append(
                    PublicIPResult(
                        ip_address="",
                        provider="Azure",
                        service=svc_name,
                        ip_prefix=ip_prefix,
                        region=svc_region,
                    )
                )

    elif provider == "oracle":
        for reg in data.get("regions", []):
            reg_name = reg.get("region", "Unknown")

            if region and region.lower() not in reg_name.lower():
                continue

            for cidr_obj in reg.get("cidrs", []):
                cidr = cidr_obj.get("cidr", "")
                tags = cidr_obj.get("tags", [])
                svc_name = ", ".join(tags) if tags else "Oracle Cloud"

                if service and service.lower() not in svc_name.lower():
                    continue

                results.append(
                    PublicIPResult(
                        ip_address="",
                        provider="Oracle",
                        service=svc_name,
                        ip_prefix=cidr,
                        region=reg_name,
                    )
                )

    return results


def get_available_filters(provider: str = "aws") -> dict[str, list[str]]:
    """Get available region/service lists"""
    provider = provider.lower()

    loaders = {
        "aws": get_aws_ip_ranges,
        "gcp": get_gcp_ip_ranges,
        "azure": get_azure_ip_ranges,
        "oracle": get_oracle_ip_ranges,
    }

    if provider not in loaders:
        return {"regions": [], "services": []}

    data = loaders[provider]()
    regions = set()
    services = set()

    if provider == "aws":
        for prefix in data.get("prefixes", []):
            regions.add(prefix.get("region", ""))
            services.add(prefix.get("service", ""))

    elif provider == "gcp":
        for prefix in data.get("prefixes", []):
            regions.add(prefix.get("scope", ""))
            services.add(prefix.get("service", "Google Cloud"))

    elif provider == "azure":
        for svc in data.get("values", []):
            regions.add(svc.get("properties", {}).get("region", "Global"))
            services.add(svc.get("name", ""))

    elif provider == "oracle":
        for reg in data.get("regions", []):
            regions.add(reg.get("region", ""))
            for cidr_obj in reg.get("cidrs", []):
                tags = cidr_obj.get("tags", [])
                if tags:
                    services.update(tags)

    return {
        "regions": sorted(r for r in regions if r),
        "services": sorted(s for s in services if s),
    }
