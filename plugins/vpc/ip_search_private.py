"""
plugins/vpc/ip_search_private.py - 사설 IP 검색기

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
from typing import Any, Dict, List, Optional, Tuple, Union

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
    security_groups: List[str] = field(default_factory=list)
    name: str = ""
    is_managed: bool = False
    managed_by: str = "User"
    mapped_resource: str = ""  # 상세 모드에서 사용


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
        cache_dir: Optional[str] = None,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ):
        # 캐시 디렉토리 설정 (프로젝트 루트의 temp 폴더)
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            # plugins/vpc -> plugins -> project_root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.cache_dir = os.path.join(project_root, "temp", "eni")

        os.makedirs(self.cache_dir, exist_ok=True)

        # 세션별 캐시 파일
        safe_name = self._sanitize_filename(session_name)
        self.cache_file = os.path.join(self.cache_dir, f"eni_cache_{safe_name}.msgpack")
        self.expiry = timedelta(hours=expiry_hours)

        # 캐시 데이터
        self.cache: Dict[
            str, Dict[str, Any]
        ] = {}  # IP -> {interfaces: [], last_accessed: float}
        self.sorted_ips: List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = []
        self.lock = threading.Lock()

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

            # 만료되지 않은 항목만 로드
            self.cache = {
                ip_str: entry
                for ip_str, entry in data.items()
                if isinstance(entry, dict)
                and current - entry.get("last_accessed", 0) < expiry_secs
            }

            self._rebuild_ip_index()
        except Exception:
            self.cache = {}

    def _rebuild_ip_index(self) -> None:
        """IP 인덱스 재구성 (CIDR 검색용)"""
        parsed = []
        for ip_str in self.cache.keys():
            try:
                parsed.append(ipaddress.ip_address(ip_str))
            except ValueError:
                continue
        self.sorted_ips = sorted(parsed)

    def save(self) -> None:
        """캐시 저장"""
        with self.lock:
            with open(self.cache_file, "wb") as f:
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

    def get_by_ip(self, ip: str) -> List[Dict[str, Any]]:
        """IP 주소로 ENI 검색"""
        with self.lock:
            entry = self.cache.get(ip)
            if entry:
                entry["last_accessed"] = time.time()
                return entry["interfaces"]
        return []

    def get_by_cidr(self, cidr: str) -> List[Tuple[str, Dict[str, Any]]]:
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

    def update(self, interfaces: List[Dict[str, Any]]) -> None:
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

    def _add_to_cache(self, ip: str, eni: Dict[str, Any], timestamp: float) -> None:
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

        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def count(self) -> int:
        """캐시된 ENI 수 반환"""
        return len(self.cache)


# =============================================================================
# ENI 수집 함수
# =============================================================================


def fetch_enis_from_account(
    session,
    account_id: str,
    account_name: str,
    regions: List[str],
    progress_callback=None,
) -> List[Dict[str, Any]]:
    """
    계정에서 ENI 목록 수집

    Args:
        session: boto3 세션
        account_id: 계정 ID
        account_name: 계정 이름
        regions: 조회할 리전 목록
        progress_callback: 진행 콜백 함수

    Returns:
        ENI 정보 목록
    """
    interfaces = []

    for region in regions:
        try:
            ec2 = get_client(session, "ec2", region_name=region)
            paginator = ec2.get_paginator("describe_network_interfaces")

            for page in paginator.paginate():
                for eni in page["NetworkInterfaces"]:
                    # 메타 정보 추가
                    eni["AccountId"] = account_id
                    eni["AccountName"] = account_name
                    eni["Region"] = region

                    # 관리형 여부 판단
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


def map_eni_to_resource(eni: Dict[str, Any]) -> str:
    """
    ENI Description을 파싱하여 연결된 리소스 추출 (빠른 매핑)

    Returns:
        리소스 정보 문자열 (예: "EC2: i-xxx", "RDS: mydb", "Lambda: my-func")
    """
    import re

    description = eni.get("Description", "")
    interface_type = eni.get("InterfaceType", "")
    attachment = eni.get("Attachment", {})

    # EC2 인스턴스 (Attachment에서 확인)
    instance_id = attachment.get("InstanceId")
    if instance_id:
        return f"EC2: {instance_id}"

    if not description:
        return ""

    # EFS Mount Target
    if "EFS" in description or "mount target" in description.lower():
        fs_match = re.search(r"fs-[a-zA-Z0-9]+", description)
        if fs_match:
            return f"EFS: {fs_match.group(0)}"
        return "EFS"

    # Lambda
    if "AWS Lambda VPC ENI" in description:
        func_match = re.search(r"AWS Lambda VPC ENI-(.+)", description)
        if func_match:
            return f"Lambda: {func_match.group(1).strip()}"
        return "Lambda"

    # ELB (ALB/NLB/CLB)
    if "ELB" in description:
        if "app/" in description:
            alb_name = description.split("app/")[1].split("/")[0]
            return f"ALB: {alb_name}"
        elif "net/" in description:
            nlb_name = description.split("net/")[1].split("/")[0]
            return f"NLB: {nlb_name}"
        else:
            clb_name = description.replace("ELB ", "").strip()
            return f"CLB: {clb_name}"

    # RDS
    if "RDSNetworkInterface" in description:
        rds_patterns = [
            r"RDSNetworkInterface[:\s-]+([a-zA-Z0-9_-]+)",
            r"db[:\s-]+([a-zA-Z0-9_-]+)",
            r"([a-zA-Z0-9_-]+)\..*\.rds\.amazonaws\.com",
        ]
        for pattern in rds_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                db_id = match.group(1)
                if db_id.lower() not in ["network", "interface", "eni"]:
                    return f"RDS: {db_id}"
        return "RDS"

    # VPC Endpoint
    if "VPC Endpoint" in description:
        return "VPC Endpoint"

    # FSx
    if "FSx" in description or "fsx" in description.lower():
        fs_match = re.search(r"fs-[a-zA-Z0-9]+", description)
        if fs_match:
            return f"FSx: {fs_match.group(0)}"
        return "FSx"

    # NAT Gateway
    if "NAT Gateway" in description or interface_type == "nat_gateway":
        nat_match = re.search(r"nat-[a-zA-Z0-9]+", description)
        if nat_match:
            return f"NAT: {nat_match.group(0)}"
        return "NAT Gateway"

    # ECS
    if "ecs" in interface_type.lower() or "ecs" in description.lower():
        return "ECS Task"

    # ElastiCache
    if "ElastiCache" in description:
        return "ElastiCache"

    # OpenSearch / Elasticsearch
    if "OpenSearch" in description or "Elasticsearch" in description:
        return "OpenSearch"

    # Transit Gateway
    if "Transit Gateway" in description:
        return "Transit Gateway"

    # API Gateway
    if "API Gateway" in description:
        return "API Gateway"

    return ""


# =============================================================================
# 검색 결과 변환
# =============================================================================


def eni_to_result(
    ip: str, eni: Dict[str, Any], detailed: bool = False
) -> PrivateIPResult:
    """ENI 데이터를 검색 결과로 변환"""
    # 태그에서 Name 추출
    name = ""
    for tag in eni.get("TagSet", []):
        if tag.get("Key") == "Name":
            name = tag.get("Value", "")
            break

    # 보안 그룹 목록
    security_groups = [sg.get("GroupName", "") for sg in eni.get("Groups", [])]

    # Primary IP 추출
    primary_private = ""
    primary_public = ""
    for priv_ip in eni.get("PrivateIpAddresses", []):
        if priv_ip.get("Primary"):
            primary_private = priv_ip.get("PrivateIpAddress", "")
            primary_public = priv_ip.get("Association", {}).get("PublicIp", "")
            break

    # 상세 모드일 때만 리소스 매핑
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
# 메인 검색 함수
# =============================================================================


def search_private_ip(
    ip_list: List[str],
    cache: ENICache,
    detailed: bool = False,
) -> List[PrivateIPResult]:
    """
    사설 IP 검색 (캐시 기반)

    Args:
        ip_list: 검색할 IP 주소 또는 CIDR 목록
        cache: ENI 캐시
        detailed: 상세 모드 (리소스 매핑 포함)

    Returns:
        검색 결과 목록
    """
    results = []

    for ip_or_cidr in ip_list:
        ip_or_cidr = ip_or_cidr.strip()
        if not ip_or_cidr:
            continue

        # CIDR인지 확인
        if "/" in ip_or_cidr:
            matches = cache.get_by_cidr(ip_or_cidr)
            for ip, eni in matches:
                results.append(eni_to_result(ip, eni, detailed))
        else:
            matches = cache.get_by_ip(ip_or_cidr)
            for eni in matches:
                results.append(eni_to_result(ip_or_cidr, eni, detailed))

    return results


def refresh_cache(
    cache: ENICache,
    session_iterator: SessionIterator,
    regions: Optional[List[str]] = None,
    progress_callback=None,
) -> int:
    """
    캐시 새로고침

    Args:
        cache: ENI 캐시
        session_iterator: 세션 반복자
        regions: 조회할 리전 목록 (None이면 활성 리전)
        progress_callback: 진행 콜백

    Returns:
        수집된 ENI 수
    """
    from core.region import get_active_regions

    total_count = 0

    for account_id, account_name, session in session_iterator:
        # 리전 목록 결정
        if regions:
            target_regions = regions
        else:
            target_regions = get_active_regions(session)

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
