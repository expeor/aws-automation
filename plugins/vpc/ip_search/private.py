"""
plugins/vpc/ip_search/private.py - 사설 IP 검색기

AWS ENI(Elastic Network Interface) 캐시를 사용한 사설 IP 검색

특징:
- 멀티 계정/멀티 리전 ENI 캐시
- CIDR 범위 검색 지원
- 정규식 기반 필드 검색 (ENI ID, VPC, 서브넷 등)
"""

import ipaddress
import os
import threading
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import msgpack
from botocore.exceptions import ClientError

from core.auth import SessionIterator
from core.parallel import get_client

# =============================================================================
# 데이터 구조
# =============================================================================


@dataclass
class PrivateIPResult:
    """사설 IP 검색 결과"""

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


# =============================================================================
# ENI 캐시 관리
# =============================================================================


class ENICache:
    """
    ENI 캐시 관리자

    IP 주소를 키로 ENI 정보를 저장하고 검색
    """

    DEFAULT_EXPIRY_HOURS = 24

    def __init__(
        self,
        session_name: str = "default",
        cache_dir: str | None = None,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ):
        # 캐시 디렉토리 설정 (프로젝트 루트의 temp 폴더)
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            # plugins/vpc/ip_search -> vpc -> plugins -> project_root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.cache_dir = os.path.join(project_root, "temp", "eni")

        os.makedirs(self.cache_dir, exist_ok=True)

        # 세션별 캐시 파일
        safe_name = self._sanitize_filename(session_name)
        self.cache_file = os.path.join(self.cache_dir, f"eni_cache_{safe_name}.msgpack")
        self.expiry = timedelta(hours=expiry_hours)

        # 캐시 데이터
        self.cache: dict[str, dict[str, Any]] = {}
        self.sorted_ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        self.lock = threading.Lock()

        # Secondary indices for O(1) field lookups
        self._account_index: dict[str, set[str]] = {}  # account_id -> {ips}
        self._region_index: dict[str, set[str]] = {}  # region -> {ips}
        self._vpc_index: dict[str, set[str]] = {}  # vpc_id -> {ips}

        # 캐시 로드
        self._load_cache()

    def _sanitize_filename(self, name: str) -> str:
        """파일명에 안전한 문자열로 변환"""
        import re

        safe = re.sub(r'[<>:"/\\|?*]', "_", name)
        safe = re.sub(r"_+", "_", safe).strip(" ._")
        return safe[:100] if safe else "default"

    def _load_cache(self) -> None:
        """캐시 파일 로드"""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "rb") as f:
                data = msgpack.load(f)

            current = time.time()
            expiry_secs = self.expiry.total_seconds()

            self.cache = {
                ip_str: entry
                for ip_str, entry in data.items()
                if isinstance(entry, dict) and current - entry.get("last_accessed", 0) < expiry_secs
            }

            self._rebuild_ip_index()
        except Exception:
            self.cache = {}

    def _rebuild_ip_index(self) -> None:
        """IP 인덱스 재구성 (CIDR 검색 + secondary indices)"""
        parsed = []
        # Reset secondary indices
        self._account_index.clear()
        self._region_index.clear()
        self._vpc_index.clear()

        for ip_str, entry in self.cache.items():
            # Build sorted IP list for CIDR search
            try:
                parsed.append(ipaddress.ip_address(ip_str))
            except ValueError:
                continue

            # Build secondary indices
            for eni in entry.get("interfaces", []):
                account_id = eni.get("AccountId", "")
                region = eni.get("Region", "")
                vpc_id = eni.get("VpcId", "")

                if account_id:
                    if account_id not in self._account_index:
                        self._account_index[account_id] = set()
                    self._account_index[account_id].add(ip_str)

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
        """캐시 저장"""
        with self.lock, open(self.cache_file, "wb") as f:
            msgpack.dump(self._convert_datetime(self.cache), f)

    def _convert_datetime(self, obj: Any) -> Any:
        """datetime 객체를 문자열로 변환"""
        if isinstance(obj, dict):
            return {k: self._convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime(e) for e in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def is_valid(self) -> bool:
        """캐시 유효성 검사"""
        if not os.path.exists(self.cache_file):
            return False

        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.cache_file))
        return age < self.expiry

    def get_by_ip(self, ip: str) -> list[dict[str, Any]]:
        """IP 주소로 ENI 검색"""
        with self.lock:
            entry = self.cache.get(ip)
            if entry:
                entry["last_accessed"] = time.time()
                interfaces: list[dict[str, Any]] = entry["interfaces"]
                return interfaces
        return []

    def get_by_cidr(self, cidr: str) -> list[tuple[str, dict[str, Any]]]:
        """CIDR 범위로 ENI 검색"""
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

    def update(self, interfaces: list[dict[str, Any]]) -> None:
        """ENI 데이터로 캐시 업데이트"""
        current = time.time()

        with self.lock:
            for eni in interfaces:
                # Private IP 추가
                for priv_ip in eni.get("PrivateIpAddresses", []):
                    ip = priv_ip.get("PrivateIpAddress")
                    if ip:
                        self._add_to_cache(ip, eni, current)

                    # Public IP 추가
                    pub_ip = priv_ip.get("Association", {}).get("PublicIp")
                    if pub_ip:
                        self._add_to_cache(pub_ip, eni, current)

                # IPv6 추가
                for ipv6 in eni.get("Ipv6Addresses", []):
                    ip = ipv6.get("Ipv6Address")
                    if ip:
                        self._add_to_cache(ip, eni, current)

        self._rebuild_ip_index()

    def _add_to_cache(self, ip: str, eni: dict[str, Any], timestamp: float) -> None:
        """캐시에 IP-ENI 매핑 추가"""
        if ip not in self.cache:
            self.cache[ip] = {"interfaces": [], "last_accessed": timestamp}

        if eni not in self.cache[ip]["interfaces"]:
            self.cache[ip]["interfaces"].append(eni)

        self.cache[ip]["last_accessed"] = timestamp

    def clear(self) -> None:
        """캐시 초기화"""
        with self.lock:
            self.cache.clear()
            self.sorted_ips.clear()
            # Clear secondary indices
            self._account_index.clear()
            self._region_index.clear()
            self._vpc_index.clear()

        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def count(self) -> int:
        """캐시된 ENI 수 반환"""
        return len(self.cache)

    def get_stats(self) -> dict[str, Any]:
        """캐시 통계 반환 (리전별, 계정별 ENI 수)"""
        regions: dict[str, int] = {}
        accounts: dict[str, str] = {}  # account_id -> account_name

        with self.lock:
            for entry in self.cache.values():
                eni = entry.get("eni", {})
                region = eni.get("Region", "unknown")
                account_id = eni.get("AccountId", "unknown")
                account_name = eni.get("AccountName", account_id)

                regions[region] = regions.get(region, 0) + 1
                if account_id not in accounts:
                    accounts[account_id] = account_name

        return {
            "total": len(self.cache),
            "regions": regions,
            "accounts": accounts,
        }

    # =========================================================================
    # Secondary Index Search Methods (O(1) lookup by field)
    # =========================================================================

    def search_by_account(self, account_id: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Search ENIs by account ID using secondary index.

        Args:
            account_id: AWS account ID to search for

        Returns:
            List of (ip_str, eni_dict) tuples
        """
        results = []
        with self.lock:
            ip_set = self._account_index.get(account_id, set())
            for ip_str in ip_set:
                entry = self.cache.get(ip_str)
                if entry:
                    entry["last_accessed"] = time.time()
                    for eni in entry["interfaces"]:
                        if eni.get("AccountId") == account_id:
                            results.append((ip_str, eni))
        return results

    def search_by_region(self, region: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Search ENIs by region using secondary index.

        Args:
            region: AWS region to search for (e.g., "ap-northeast-2")

        Returns:
            List of (ip_str, eni_dict) tuples
        """
        results = []
        with self.lock:
            ip_set = self._region_index.get(region, set())
            for ip_str in ip_set:
                entry = self.cache.get(ip_str)
                if entry:
                    entry["last_accessed"] = time.time()
                    for eni in entry["interfaces"]:
                        if eni.get("Region") == region:
                            results.append((ip_str, eni))
        return results

    def search_by_vpc(self, vpc_id: str) -> list[tuple[str, dict[str, Any]]]:
        """
        Search ENIs by VPC ID using secondary index.

        Args:
            vpc_id: VPC ID to search for (e.g., "vpc-abc12345")

        Returns:
            List of (ip_str, eni_dict) tuples
        """
        results = []
        with self.lock:
            ip_set = self._vpc_index.get(vpc_id, set())
            for ip_str in ip_set:
                entry = self.cache.get(ip_str)
                if entry:
                    entry["last_accessed"] = time.time()
                    for eni in entry["interfaces"]:
                        if eni.get("VpcId") == vpc_id:
                            results.append((ip_str, eni))
        return results

    def get_indexed_accounts(self) -> list[str]:
        """Get list of all indexed account IDs."""
        return list(self._account_index.keys())

    def get_indexed_regions(self) -> list[str]:
        """Get list of all indexed regions."""
        return list(self._region_index.keys())

    def get_indexed_vpcs(self) -> list[str]:
        """Get list of all indexed VPC IDs."""
        return list(self._vpc_index.keys())


# =============================================================================
# ENI 수집 함수
# =============================================================================


def fetch_enis_from_account(
    session,
    account_id: str,
    account_name: str,
    regions: list[str],
    progress_callback=None,
) -> list[dict[str, Any]]:
    """계정에서 ENI 목록 수집"""
    interfaces = []

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
            code = e.response["Error"]["Code"]
            if code == "UnauthorizedOperation":
                continue
        except Exception:
            continue

    return interfaces


# =============================================================================
# 리소스 매핑 (Description 파싱 기반)
# =============================================================================


def map_eni_to_resource(eni: dict[str, Any]) -> str:
    """ENI Description을 파싱하여 연결된 리소스 추출 (빠른 매핑)"""
    from plugins.vpc.ip_search.parser import parse_eni_to_display_string

    return parse_eni_to_display_string(eni)


# =============================================================================
# 검색 결과 변환
# =============================================================================


def eni_to_result(ip: str, eni: dict[str, Any], detailed: bool = False) -> PrivateIPResult:
    """ENI 데이터를 검색 결과로 변환"""
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

    mapped_resource = map_eni_to_resource(eni) if detailed else ""

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
    )


# =============================================================================
# 쿼리 파서
# =============================================================================


class QueryType:
    """검색 쿼리 타입"""

    IP = "ip"
    CIDR = "cidr"
    ENI_ID = "eni_id"
    VPC_ID = "vpc_id"
    SUBNET_ID = "subnet_id"
    INSTANCE_ID = "instance_id"
    SECURITY_GROUP = "security_group"
    TEXT = "text"


def parse_query(query: str) -> tuple[str, str]:
    """검색 쿼리 파싱하여 타입과 값 반환"""
    query = query.strip()
    if not query:
        return QueryType.TEXT, ""

    if query.startswith("eni-"):
        return QueryType.ENI_ID, query
    if query.startswith("vpc-"):
        return QueryType.VPC_ID, query
    if query.startswith("subnet-"):
        return QueryType.SUBNET_ID, query
    if query.startswith("i-"):
        return QueryType.INSTANCE_ID, query
    if query.startswith("sg-"):
        return QueryType.SECURITY_GROUP, query

    if "/" in query:
        try:
            ipaddress.ip_network(query, strict=False)
            return QueryType.CIDR, query
        except ValueError:
            pass

    try:
        ipaddress.ip_address(query)
        return QueryType.IP, query
    except ValueError:
        pass

    return QueryType.TEXT, query


# =============================================================================
# 메인 검색 함수
# =============================================================================


def search_private_ip(
    ip_list: list[str],
    cache: ENICache,
    detailed: bool = False,
) -> list[PrivateIPResult]:
    """사설 IP 검색 (캐시 기반)"""
    results = []

    for ip_or_cidr in ip_list:
        ip_or_cidr = ip_or_cidr.strip()
        if not ip_or_cidr:
            continue

        if "/" in ip_or_cidr:
            cidr_matches = cache.get_by_cidr(ip_or_cidr)
            for ip, eni in cidr_matches:
                results.append(eni_to_result(ip, eni, detailed))
        else:
            ip_matches = cache.get_by_ip(ip_or_cidr)
            for eni in ip_matches:
                results.append(eni_to_result(ip_or_cidr, eni, detailed))

    return results


def search_by_query(queries: list[str], cache: ENICache) -> list[PrivateIPResult]:
    """다양한 쿼리 타입으로 검색 (통합 검색용)"""
    results = []
    seen_enis = set()

    for query in queries:
        query_type, value = parse_query(query)
        if not value:
            continue

        matched_enis = []

        if query_type == QueryType.IP:
            for eni in cache.get_by_ip(value):
                matched_enis.append((value, eni))

        elif query_type == QueryType.CIDR:
            matched_enis = cache.get_by_cidr(value)

        elif query_type in (
            QueryType.ENI_ID,
            QueryType.VPC_ID,
            QueryType.SUBNET_ID,
            QueryType.INSTANCE_ID,
            QueryType.SECURITY_GROUP,
            QueryType.TEXT,
        ):
            matched_enis = _search_by_field(cache, query_type, value)

        for ip, eni in matched_enis:
            eni_id = eni.get("NetworkInterfaceId", "")
            if eni_id and eni_id not in seen_enis:
                seen_enis.add(eni_id)
                results.append(eni_to_result(ip, eni, detailed=True))

    return results


def _search_by_field(cache: ENICache, query_type: str, value: str) -> list[tuple[str, dict[str, Any]]]:
    """
    필드 기반 검색

    Uses secondary indices for O(1) lookups where available:
    - VPC_ID: Uses cache._vpc_index
    - Other types: Falls back to O(n) cache scan
    """
    results = []
    value_lower = value.lower()

    # O(1) lookup using secondary indices for VPC_ID
    if query_type == QueryType.VPC_ID:
        return cache.search_by_vpc(value)

    # O(n) scan for other query types
    with cache.lock:
        for ip_str, entry in cache.cache.items():
            for eni in entry.get("interfaces", []):
                matched = False

                if query_type == QueryType.ENI_ID:
                    if eni.get("NetworkInterfaceId", "").lower() == value_lower:
                        matched = True

                elif query_type == QueryType.SUBNET_ID:
                    if eni.get("SubnetId", "").lower() == value_lower:
                        matched = True

                elif query_type == QueryType.INSTANCE_ID:
                    instance_id = eni.get("Attachment", {}).get("InstanceId", "")
                    if instance_id.lower() == value_lower:
                        matched = True

                elif query_type == QueryType.SECURITY_GROUP:
                    for sg in eni.get("Groups", []):
                        sg_id = sg.get("GroupId", "").lower()
                        sg_name = sg.get("GroupName", "").lower()
                        if value_lower in sg_id or value_lower in sg_name:
                            matched = True
                            break

                elif query_type == QueryType.TEXT:
                    description = eni.get("Description", "").lower()
                    name = ""
                    for tag in eni.get("TagSet", []):
                        if tag.get("Key") == "Name":
                            name = tag.get("Value", "").lower()
                            break

                    if value_lower in description or value_lower in name:
                        matched = True

                if matched:
                    results.append((ip_str, eni))

    return results


def refresh_cache(
    cache: ENICache,
    session_iterator: SessionIterator,
    regions: list[str] | None = None,
    progress_callback=None,
) -> int:
    """캐시 새로고침"""
    from core.region import ALL_REGIONS

    total_count = 0

    for account_id, account_name, session in session_iterator:
        target_regions = regions or ALL_REGIONS

        interfaces = fetch_enis_from_account(
            session=session,
            account_id=account_id,
            account_name=account_name,
            regions=target_regions,
            progress_callback=progress_callback,
        )

        cache.update(interfaces)
        total_count += len(interfaces)

    cache.save()
    return total_count
