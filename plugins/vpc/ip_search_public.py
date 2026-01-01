"""
plugins/vpc/ip_search_public.py - 공인 IP 검색기

클라우드 제공자(AWS, GCP, Azure, Oracle)의 공인 IP 범위에서 IP 검색

특징:
- AWS, GCP, Azure, Oracle Cloud IP 범위 지원
- CIDR 및 단일 IP 검색
- 24시간 캐시로 빠른 응답
"""

import ipaddress
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

# =============================================================================
# 데이터 구조
# =============================================================================


@dataclass
class PublicIPResult:
    """공인 IP 검색 결과"""

    ip_address: str
    provider: str  # AWS, GCP, Azure, Oracle, Unknown
    service: str
    ip_prefix: str
    region: str
    extra: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# 캐시 관리
# =============================================================================


def _get_cache_dir() -> str:
    """캐시 디렉토리 경로 (프로젝트 루트의 temp 폴더)"""
    # plugins/vpc -> plugins -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(project_root, "temp", "ip_ranges")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _load_from_cache(name: str, max_age_hours: int = 24) -> Optional[dict]:
    """캐시에서 데이터 로드"""
    cache_file = os.path.join(_get_cache_dir(), f"{name}.json")
    if not os.path.exists(cache_file):
        return None

    cache_age = time.time() - os.path.getmtime(cache_file)
    if cache_age > max_age_hours * 3600:
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_to_cache(name: str, data: dict) -> None:
    """캐시에 데이터 저장"""
    cache_file = os.path.join(_get_cache_dir(), f"{name}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# =============================================================================
# 클라우드 제공자 IP 범위 가져오기
# =============================================================================


def get_aws_ip_ranges() -> dict:
    """AWS IP 범위 가져오기"""
    cached = _load_from_cache("aws")
    if cached:
        return cached

    try:
        response = requests.get(
            "https://ip-ranges.amazonaws.com/ip-ranges.json",
            timeout=5
        )
        data = response.json()
        _save_to_cache("aws", data)
        return data
    except Exception:
        return {"prefixes": [], "ipv6_prefixes": []}


def get_gcp_ip_ranges() -> dict:
    """GCP IP 범위 가져오기"""
    cached = _load_from_cache("gcp")
    if cached:
        return cached

    try:
        response = requests.get(
            "https://www.gstatic.com/ipranges/cloud.json",
            timeout=10
        )
        data = response.json()
        _save_to_cache("gcp", data)
        return data
    except Exception:
        return {"prefixes": []}


def get_azure_ip_ranges() -> dict:
    """Azure IP 범위 가져오기 (주간 업데이트)"""
    cached = _load_from_cache("azure")
    if cached and cached.get("values"):
        return cached

    from datetime import datetime, timedelta

    # 최근 4주간 URL 시도
    base_url = "https://download.microsoft.com/download/7/1/d/71d86715-5596-4529-9b13-da13a5de5b63/ServiceTags_Public_{}.json"

    for weeks_back in range(5):
        for day_offset in range(7):
            try_date = datetime.now() - timedelta(weeks=weeks_back, days=day_offset)
            url = base_url.format(try_date.strftime("%Y%m%d"))

            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("values"):
                        _save_to_cache("azure", data)
                        return data
            except Exception:
                continue

    return {"values": []}


def get_oracle_ip_ranges() -> dict:
    """Oracle Cloud IP 범위 가져오기"""
    cached = _load_from_cache("oracle")
    if cached:
        return cached

    try:
        response = requests.get(
            "https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json",
            timeout=10
        )
        data = response.json()
        _save_to_cache("oracle", data)
        return data
    except Exception:
        return {"regions": []}


# =============================================================================
# IP 검색 함수
# =============================================================================


def search_in_aws(ip: str, data: dict) -> List[PublicIPResult]:
    """AWS IP 범위에서 검색"""
    results = []
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
                results.append(PublicIPResult(
                    ip_address=ip,
                    provider="AWS",
                    service=prefix.get("service", ""),
                    ip_prefix=prefix[prefix_key],
                    region=prefix.get("region", ""),
                    extra={"network_border_group": prefix.get("network_border_group", "")}
                ))
        except (ValueError, KeyError):
            continue

    return results


def search_in_gcp(ip: str, data: dict) -> List[PublicIPResult]:
    """GCP IP 범위에서 검색"""
    results = []
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
                results.append(PublicIPResult(
                    ip_address=ip,
                    provider="GCP",
                    service=prefix.get("service", "Google Cloud"),
                    ip_prefix=prefix[prefix_key],
                    region=prefix.get("scope", ""),
                ))
        except ValueError:
            continue

    return results


def search_in_azure(ip: str, data: dict) -> List[PublicIPResult]:
    """Azure IP 범위에서 검색"""
    results = []
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
                    results.append(PublicIPResult(
                        ip_address=ip,
                        provider="Azure",
                        service=service_name,
                        ip_prefix=prefix,
                        region=region,
                    ))
            except ValueError:
                continue

    return results


def search_in_oracle(ip: str, data: dict) -> List[PublicIPResult]:
    """Oracle Cloud IP 범위에서 검색"""
    results = []
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
                    results.append(PublicIPResult(
                        ip_address=ip,
                        provider="Oracle",
                        service=service,
                        ip_prefix=cidr,
                        region=region_name,
                    ))
            except ValueError:
                continue

    return results


# =============================================================================
# 메인 검색 함수
# =============================================================================


def load_ip_ranges_parallel(target_providers: set) -> Dict[str, dict]:
    """병렬로 IP 범위 데이터 로드"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    loaders = {
        "aws": get_aws_ip_ranges,
        "gcp": get_gcp_ip_ranges,
        "azure": get_azure_ip_ranges,
        "oracle": get_oracle_ip_ranges,
    }

    data_sources = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(loaders[p]): p
            for p in target_providers if p in loaders
        }

        for future in as_completed(futures):
            provider = futures[future]
            try:
                data_sources[provider] = future.result()
            except Exception:
                data_sources[provider] = {}

    return data_sources


def search_public_ip(
    ip_list: List[str],
    providers: Optional[List[str]] = None,
) -> List[PublicIPResult]:
    """
    공인 IP 범위에서 검색

    Args:
        ip_list: 검색할 IP 주소 목록
        providers: 검색할 제공자 목록 (None이면 전체)
                   예: ["aws", "gcp", "azure", "oracle"]

    Returns:
        검색 결과 목록
    """
    all_providers = {"aws", "gcp", "azure", "oracle"}
    if providers:
        target_providers = {p.lower() for p in providers} & all_providers
    else:
        target_providers = all_providers

    # 병렬로 데이터 로드
    data_sources = load_ip_ranges_parallel(target_providers)

    # 검색 실행
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

        # 결과 없으면 Unknown 추가
        if not found:
            all_results.append(PublicIPResult(
                ip_address=ip,
                provider="Unknown",
                service="",
                ip_prefix="",
                region="",
            ))

    return all_results
