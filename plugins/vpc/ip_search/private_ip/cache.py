"""
plugins/vpc/ip_search/private_ip/cache.py - Multi-Profile ENI Cache Management

Cache file naming: {profile_name}_{account_id}_eni.msgpack
Supports searching across multiple cache files.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import threading
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, cast

import msgpack
from botocore.exceptions import ClientError

from core.parallel import ErrorCollector, ErrorSeverity, get_client, safe_collect

logger = logging.getLogger(__name__)

# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class CacheInfo:
    """Information about a cache file."""

    filepath: str
    profile_name: str
    account_id: str
    eni_count: int
    created_at: datetime
    is_valid: bool
    regions: list[str] = field(default_factory=list)


@dataclass
class PrivateIPResult:
    """Private IP search result."""

    ip_address: str
    account_id: str
    account_name: str
    region: str
    eni_id: str
    vpc_id: str
    subnet_id: str
    availability_zone: str
    private_ip: str
    public_ip: str
    interface_type: str
    status: str
    description: str
    security_groups: list[str] = field(default_factory=list)
    name: str = ""
    is_managed: bool = False
    managed_by: str = "User"
    mapped_resource: str = ""
    profile_name: str = ""  # Which profile/cache this came from


# =============================================================================
# Cache Directory Management
# =============================================================================


def _get_cache_dir() -> str:
    """Get cache directory path (project root's temp/eni_cache folder)."""
    # Navigate from current file to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    cache_dir = os.path.join(project_root, "temp", "eni_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _sanitize_filename(name: str) -> str:
    """Convert to filesystem-safe string."""
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)
    safe = re.sub(r"_+", "_", safe).strip(" ._")
    return safe[:50] if safe else "default"


def _get_cache_filename(profile_name: str, account_id: str) -> str:
    """Generate cache filename: {profile}_{account}_eni.msgpack"""
    safe_profile = _sanitize_filename(profile_name)
    safe_account = _sanitize_filename(account_id)
    return f"{safe_profile}_{safe_account}_eni.msgpack"


def _parse_cache_filename(filename: str) -> tuple[str, str] | None:
    """Parse profile and account from cache filename."""
    if not filename.endswith("_eni.msgpack"):
        return None

    base = filename[:-12]  # Remove "_eni.msgpack"
    parts = base.rsplit("_", 1)
    if len(parts) != 2:
        return None

    return parts[0], parts[1]  # profile_name, account_id


# =============================================================================
# Cache Discovery
# =============================================================================


def list_available_caches(expiry_hours: int = 24) -> list[CacheInfo]:
    """
    List all available ENI cache files.

    Args:
        expiry_hours: Hours after which cache is considered expired

    Returns:
        List of CacheInfo objects
    """
    cache_dir = _get_cache_dir()
    caches = []

    if not os.path.exists(cache_dir):
        return caches

    for filename in os.listdir(cache_dir):
        if not filename.endswith("_eni.msgpack"):
            continue

        parsed = _parse_cache_filename(filename)
        if not parsed:
            continue

        profile_name, account_id = parsed
        filepath = os.path.join(cache_dir, filename)

        try:
            mtime = os.path.getmtime(filepath)
            created_at = datetime.fromtimestamp(mtime)
            age_hours = (time.time() - mtime) / 3600
            is_valid = age_hours < expiry_hours

            # Load to get ENI count and regions
            with open(filepath, "rb") as f:
                data = cast(dict[str, Any], msgpack.load(f))

            eni_count = len(data)
            regions: set[str] = set()
            for entry in data.values():
                for eni in entry.get("interfaces", []):
                    region = eni.get("Region")
                    if region:
                        regions.add(region)

            caches.append(
                CacheInfo(
                    filepath=filepath,
                    profile_name=profile_name,
                    account_id=account_id,
                    eni_count=eni_count,
                    created_at=created_at,
                    is_valid=is_valid,
                    regions=sorted(regions),
                )
            )
        except Exception as e:
            logger.debug("Failed to load cache %s: %s", filename, e)
            continue

    # Sort by profile name, then account
    caches.sort(key=lambda c: (c.profile_name, c.account_id))
    return caches


def delete_cache(profile_name: str, account_id: str) -> bool:
    """Delete a specific cache file."""
    cache_dir = _get_cache_dir()
    filename = _get_cache_filename(profile_name, account_id)
    filepath = os.path.join(cache_dir, filename)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            logger.debug("Failed to delete cache %s: %s", filepath, e)
    return False


def delete_all_caches() -> int:
    """Delete all cache files. Returns count of deleted files."""
    cache_dir = _get_cache_dir()
    count = 0

    if not os.path.exists(cache_dir):
        return count

    for filename in os.listdir(cache_dir):
        if filename.endswith("_eni.msgpack"):
            try:
                os.remove(os.path.join(cache_dir, filename))
                count += 1
            except Exception as e:
                logger.debug("Failed to delete %s: %s", filename, e)

    return count


# =============================================================================
# ENI Cache Class
# =============================================================================


class ENICache:
    """
    ENI Cache for a single profile/account.

    Cache file: {profile}_{account}_eni.msgpack
    """

    DEFAULT_EXPIRY_HOURS = 24

    def __init__(
        self,
        profile_name: str,
        account_id: str,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ):
        self.profile_name = profile_name
        self.account_id = account_id
        self.cache_dir = _get_cache_dir()

        filename = _get_cache_filename(profile_name, account_id)
        self.cache_file = os.path.join(self.cache_dir, filename)
        self.expiry = timedelta(hours=expiry_hours)

        # Cache data
        self.cache: dict[str, dict[str, Any]] = {}
        self.sorted_ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        self.lock = threading.Lock()

        # Secondary indices
        self._region_index: dict[str, set[str]] = {}
        self._vpc_index: dict[str, set[str]] = {}

        # Load existing cache
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file."""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "rb") as f:
                data = cast(dict[str, Any], msgpack.load(f))

            current = time.time()
            expiry_secs = self.expiry.total_seconds()

            self.cache = {
                ip_str: entry
                for ip_str, entry in data.items()
                if isinstance(entry, dict) and current - entry.get("last_accessed", 0) < expiry_secs
            }

            self._rebuild_indices()
        except Exception as e:
            logger.debug("Failed to load cache: %s", e)
            self.cache = {}

    def _rebuild_indices(self) -> None:
        """Rebuild IP index and secondary indices."""
        parsed = []
        self._region_index.clear()
        self._vpc_index.clear()

        for ip_str, entry in self.cache.items():
            try:
                parsed.append(ipaddress.ip_address(ip_str))
            except ValueError:
                continue

            for eni in entry.get("interfaces", []):
                region = eni.get("Region", "")
                vpc_id = eni.get("VpcId", "")

                if region:
                    if region not in self._region_index:
                        self._region_index[region] = set()
                    self._region_index[region].add(ip_str)

                if vpc_id:
                    if vpc_id not in self._vpc_index:
                        self._vpc_index[vpc_id] = set()
                    self._vpc_index[vpc_id].add(ip_str)

        self.sorted_ips = sorted(parsed)

    def save(self) -> None:
        """Save cache to file."""
        with self.lock, open(self.cache_file, "wb") as f:
            msgpack.dump(self._convert_datetime(self.cache), f)

    def _convert_datetime(self, obj: Any) -> Any:
        """Convert datetime objects to strings for serialization."""
        if isinstance(obj, dict):
            return {k: self._convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime(e) for e in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def is_valid(self) -> bool:
        """Check if cache is valid (exists and not expired)."""
        if not os.path.exists(self.cache_file):
            return False

        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.cache_file))
        return age < self.expiry

    def count(self) -> int:
        """Return number of cached IP addresses."""
        return len(self.cache)

    def get_regions(self) -> list[str]:
        """Get list of regions in cache."""
        return sorted(self._region_index.keys())

    def clear(self) -> None:
        """Clear cache and delete file."""
        with self.lock:
            self.cache.clear()
            self.sorted_ips.clear()
            self._region_index.clear()
            self._vpc_index.clear()

        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def update(self, interfaces: list[dict[str, Any]]) -> None:
        """Update cache with ENI data."""
        current = time.time()

        with self.lock:
            for eni in interfaces:
                # Add private IPs
                for priv_ip in eni.get("PrivateIpAddresses", []):
                    ip = priv_ip.get("PrivateIpAddress")
                    if ip:
                        self._add_to_cache(ip, eni, current)

                    # Add public IP
                    pub_ip = priv_ip.get("Association", {}).get("PublicIp")
                    if pub_ip:
                        self._add_to_cache(pub_ip, eni, current)

                # Add IPv6
                for ipv6 in eni.get("Ipv6Addresses", []):
                    ip = ipv6.get("Ipv6Address")
                    if ip:
                        self._add_to_cache(ip, eni, current)

        self._rebuild_indices()

    def _add_to_cache(self, ip: str, eni: dict[str, Any], timestamp: float) -> None:
        """Add IP-ENI mapping to cache."""
        if ip not in self.cache:
            self.cache[ip] = {"interfaces": [], "last_accessed": timestamp}

        if eni not in self.cache[ip]["interfaces"]:
            self.cache[ip]["interfaces"].append(eni)

        self.cache[ip]["last_accessed"] = timestamp

    def get_by_ip(self, ip: str) -> list[dict[str, Any]]:
        """Get ENI data by IP address."""
        with self.lock:
            entry = self.cache.get(ip)
            if entry:
                entry["last_accessed"] = time.time()
                return entry["interfaces"]
        return []

    def get_by_cidr(self, cidr: str) -> list[tuple[str, dict[str, Any]]]:
        """Get ENI data by CIDR range."""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return []

        min_ip = network.network_address
        max_ip = network.broadcast_address

        left = bisect_left(self.sorted_ips, min_ip)
        right = bisect_right(self.sorted_ips, max_ip)

        results = []
        with self.lock:
            for idx in range(left, right):
                ip_obj = self.sorted_ips[idx]
                if ip_obj in network:
                    ip_str = str(ip_obj)
                    entry = self.cache.get(ip_str)
                    if entry:
                        entry["last_accessed"] = time.time()
                        for intf in entry["interfaces"]:
                            results.append((ip_str, intf))

        return results

    def search_by_vpc(self, vpc_id: str) -> list[tuple[str, dict[str, Any]]]:
        """Search by VPC ID using secondary index."""
        results = []
        with self.lock:
            ip_set = self._vpc_index.get(vpc_id, set())
            for ip_str in ip_set:
                entry = self.cache.get(ip_str)
                if entry:
                    for eni in entry["interfaces"]:
                        if eni.get("VpcId") == vpc_id:
                            results.append((ip_str, eni))
        return results


# =============================================================================
# Multi-Cache Search
# =============================================================================


class MultiCacheSearch:
    """Search across multiple ENI caches."""

    def __init__(self, caches: list[ENICache]):
        self.caches = caches

    def search_ip(self, ip: str) -> list[PrivateIPResult]:
        """Search for an IP across all caches."""
        results = []

        for cache in self.caches:
            eni_list = cache.get_by_ip(ip)
            for eni in eni_list:
                result = _eni_to_result(ip, eni, cache.profile_name)
                results.append(result)

        return results

    def search_cidr(self, cidr: str) -> list[PrivateIPResult]:
        """Search for CIDR range across all caches."""
        results = []

        for cache in self.caches:
            matches = cache.get_by_cidr(cidr)
            for ip_str, eni in matches:
                result = _eni_to_result(ip_str, eni, cache.profile_name)
                results.append(result)

        return results

    def search_vpc(self, vpc_id: str) -> list[PrivateIPResult]:
        """Search by VPC ID across all caches."""
        results = []

        for cache in self.caches:
            matches = cache.search_by_vpc(vpc_id)
            for ip_str, eni in matches:
                result = _eni_to_result(ip_str, eni, cache.profile_name)
                results.append(result)

        return results

    def search_text(self, text: str) -> list[PrivateIPResult]:
        """Search by text in description/name across all caches."""
        results = []
        text_lower = text.lower()

        for cache in self.caches:
            with cache.lock:
                for ip_str, entry in cache.cache.items():
                    for eni in entry.get("interfaces", []):
                        description = eni.get("Description", "").lower()
                        name = ""
                        for tag in eni.get("TagSet", []):
                            if tag.get("Key") == "Name":
                                name = tag.get("Value", "").lower()
                                break

                        if text_lower in description or text_lower in name:
                            result = _eni_to_result(ip_str, eni, cache.profile_name)
                            results.append(result)

        return results


def _eni_to_result(ip: str, eni: dict[str, Any], profile_name: str) -> PrivateIPResult:
    """Convert ENI data to PrivateIPResult."""
    from plugins.vpc.ip_search.parser import parse_eni_to_display_string

    name = ""
    for tag in eni.get("TagSet", []):
        if tag.get("Key") == "Name":
            name = tag.get("Value", "")
            break

    security_groups = [sg.get("GroupName", "") for sg in eni.get("Groups", [])]

    primary_private = ""
    primary_public = ""
    for priv_ip in eni.get("PrivateIpAddresses", []):
        if priv_ip.get("Primary"):
            primary_private = priv_ip.get("PrivateIpAddress", "")
            primary_public = priv_ip.get("Association", {}).get("PublicIp", "")
            break

    mapped_resource = parse_eni_to_display_string(eni)

    return PrivateIPResult(
        ip_address=ip,
        account_id=eni.get("AccountId", ""),
        account_name=eni.get("AccountName", ""),
        region=eni.get("Region", ""),
        eni_id=eni.get("NetworkInterfaceId", ""),
        vpc_id=eni.get("VpcId", ""),
        subnet_id=eni.get("SubnetId", ""),
        availability_zone=eni.get("AvailabilityZone", ""),
        private_ip=primary_private,
        public_ip=primary_public,
        interface_type=eni.get("InterfaceType", ""),
        status=eni.get("Status", ""),
        description=eni.get("Description", ""),
        security_groups=security_groups,
        name=name,
        is_managed=eni.get("IsManaged", False),
        managed_by=eni.get("ManagedBy", "User"),
        mapped_resource=mapped_resource,
        profile_name=profile_name,
    )


# =============================================================================
# Cache Building
# =============================================================================


@dataclass
class ENIFetchResult:
    """Result of fetching ENIs from an account"""

    interfaces: list[dict[str, Any]]
    errors: ErrorCollector


def fetch_enis_from_account(
    session,
    account_id: str,
    account_name: str,
    regions: list[str],
    progress_callback=None,
    error_collector: ErrorCollector | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch ENI list from an account.

    Args:
        session: boto3 session
        account_id: AWS account ID
        account_name: Display name for account
        regions: List of regions to scan
        progress_callback: Optional callback for progress updates
        error_collector: Optional ErrorCollector for structured error handling

    Returns:
        List of ENI dictionaries
    """
    interfaces: list[dict[str, Any]] = []
    collector = error_collector or ErrorCollector("ec2")

    for region in regions:
        try:
            ec2 = get_client(session, "ec2", region_name=region)
            paginator = ec2.get_paginator("describe_network_interfaces")

            for page in paginator.paginate():
                for eni in page["NetworkInterfaces"]:
                    eni["AccountId"] = account_id
                    eni["AccountName"] = account_name
                    eni["Region"] = region

                    is_managed = eni.get("RequesterManaged", False)
                    managed_by = "User"

                    if is_managed:
                        operator = eni.get("Operator", {})
                        if operator.get("Principal"):
                            managed_by = operator["Principal"]
                        elif eni.get("RequesterId"):
                            req_id = eni.get("RequesterId", "").lower()
                            if "elb" in req_id:
                                managed_by = "ELB"
                            elif "rds" in req_id:
                                managed_by = "RDS"
                            elif "lambda" in req_id:
                                managed_by = "Lambda"
                            elif "eks" in req_id:
                                managed_by = "EKS"
                            else:
                                managed_by = f"AWS ({eni.get('RequesterId', '')})"
                        else:
                            managed_by = "AWS"

                    eni["IsManaged"] = is_managed
                    eni["ManagedBy"] = managed_by

                    interfaces.append(eni)

            if progress_callback:
                progress_callback(region)

        except ClientError as e:
            safe_collect(
                collector,
                e,
                account_id=account_id,
                account_name=account_name,
                region=region,
                operation="describe_network_interfaces",
                severity=ErrorSeverity.INFO,  # Access denied is common
            )
        except Exception as e:
            collector.collect_generic(
                error_code="UnexpectedError",
                error_message=str(e),
                account_id=account_id,
                account_name=account_name,
                region=region,
                operation="describe_network_interfaces",
                severity=ErrorSeverity.WARNING,
            )
            logger.debug("Failed to fetch ENIs from region %s: %s", region, e)

    return interfaces


def fetch_enis_from_account_with_errors(
    session,
    account_id: str,
    account_name: str,
    regions: list[str],
    progress_callback=None,
) -> ENIFetchResult:
    """
    Fetch ENI list from an account with detailed error information.

    Args:
        session: boto3 session
        account_id: AWS account ID
        account_name: Display name for account
        regions: List of regions to scan
        progress_callback: Optional callback for progress updates

    Returns:
        ENIFetchResult with interfaces and error collector
    """
    collector = ErrorCollector("ec2")
    interfaces = fetch_enis_from_account(
        session=session,
        account_id=account_id,
        account_name=account_name,
        regions=regions,
        progress_callback=progress_callback,
        error_collector=collector,
    )
    return ENIFetchResult(interfaces=interfaces, errors=collector)


def build_cache(
    profile_name: str,
    account_id: str,
    account_name: str,
    session,
    regions: list[str],
    progress_callback=None,
) -> ENICache:
    """
    Build ENI cache for a profile/account.

    Args:
        profile_name: AWS profile name
        account_id: AWS account ID
        account_name: Display name for account
        session: boto3 session
        regions: List of regions to scan
        progress_callback: Optional callback for progress updates

    Returns:
        ENICache instance with data
    """
    cache = ENICache(profile_name=profile_name, account_id=account_id)
    cache.clear()

    interfaces = fetch_enis_from_account(
        session=session,
        account_id=account_id,
        account_name=account_name,
        regions=regions,
        progress_callback=progress_callback,
    )

    cache.update(interfaces)
    cache.save()

    return cache
