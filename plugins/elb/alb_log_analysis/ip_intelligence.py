"""
IP Intelligence 통합 모듈

IPDeny (국가별 IP 블록) + AbuseIPDB (악성 IP) 데이터를 통합 관리합니다.

클래스:
    IPDataCache        - 캐시 공통 로직
    IPDenyProvider     - IPDeny 데이터 제공자
    AbuseIPDBProvider  - AbuseIPDB 데이터 제공자
    IPIntelligence     - 통합 IP 인텔리전스 (국가 매핑 + 악성 IP 체크)
"""

import ipaddress
import json
import os
import tarfile
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from ipaddress import AddressValueError, IPv4Network, IPv6Network
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from rich.console import Console

from core.tools.cache import get_cache_dir, get_cache_path

# 콘솔 및 로거
try:
    from cli.ui import console, logger
except ImportError:
    import logging

    console = Console()
    logger = logging.getLogger(__name__)


# =============================================================================
# 캐시 공통 클래스
# =============================================================================


class IPDataCache:
    """IP 데이터 캐시 관리 클래스"""

    def __init__(self, cache_name: str, expiry_hours: int = 12):
        """캐시 관리자 초기화

        Args:
            cache_name: 캐시 파일 이름 (확장자 제외)
            expiry_hours: 캐시 만료 시간 (시간 단위)
        """
        self.cache_dir = get_cache_dir("ip")
        self.cache_file = get_cache_path("ip", f"{cache_name}_cache.json")
        self.expiry_hours = expiry_hours

    def load(self) -> Optional[Dict[str, Any]]:
        """캐시에서 데이터 로드"""
        try:
            if not os.path.exists(self.cache_file):
                return None

            with open(self.cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)

            # 캐시 만료 확인
            cache_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
            if datetime.now() - cache_time > timedelta(hours=self.expiry_hours):
                logger.debug(f"캐시 만료됨: {self.cache_file}")
                return None

            return cached_data

        except Exception as e:
            logger.debug(f"캐시 로드 실패: {e}")
            return None

    def save(self, data: Dict[str, Any]) -> None:
        """데이터를 캐시에 저장"""
        try:
            data["timestamp"] = datetime.now().isoformat()
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"캐시 저장 실패: {e}")


# =============================================================================
# IPDeny 데이터 제공자
# =============================================================================


class IPDenyProvider:
    """IPDeny 국가별 IP 블록 데이터 제공자"""

    IPV4_URL = "https://www.ipdeny.com/ipblocks/data/countries/all-zones.tar.gz"
    IPV6_URL = "https://www.ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz"

    def __init__(self):
        """IPDeny 제공자 초기화"""
        self._cache = IPDataCache("ipdeny", expiry_hours=168)  # 7일

    def download(self) -> Dict[str, Any]:
        """IPDeny 데이터 다운로드 및 파싱

        Returns:
            {
                "ipv4_blocks": {"KR": ["1.0.0.0/24", ...], ...},
                "ipv6_blocks": {"KR": ["2001::/32", ...], ...},
                "timestamp": "...",
                "total_countries": 250,
                "total_ipv4_blocks": 123456,
                "total_ipv6_blocks": 12345,
            }
        """
        # 캐시 확인
        cached = self._cache.load()
        if cached:
            logger.debug("✓ 캐시된 IPDeny 데이터 사용")
            return cached

        logger.debug("🌐 IPDeny 데이터 다운로드 시작...")

        try:
            ipv4_data = self._download_and_parse(self.IPV4_URL, is_ipv6=False)
            ipv6_data = self._download_and_parse(self.IPV6_URL, is_ipv6=True)

            result = {
                "ipv4_blocks": ipv4_data,
                "ipv6_blocks": ipv6_data,
                "total_countries": len(set(ipv4_data.keys()) | set(ipv6_data.keys())),
                "total_ipv4_blocks": sum(len(b) for b in ipv4_data.values()),
                "total_ipv6_blocks": sum(len(b) for b in ipv6_data.values()),
            }

            self._cache.save(result)
            logger.debug(
                f"✅ IPDeny 다운로드 완료: {result['total_countries']}개 국가, "
                f"IPv4 {result['total_ipv4_blocks']:,}개, IPv6 {result['total_ipv6_blocks']:,}개"
            )
            return result

        except Exception as e:
            logger.error(f"❌ IPDeny 다운로드 실패: {e}")
            return {"ipv4_blocks": {}, "ipv6_blocks": {}}

    def _download_and_parse(self, url: str, is_ipv6: bool) -> Dict[str, List[str]]:
        """tar.gz 파일 다운로드 및 파싱"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        try:
            country_blocks = {}
            network_class = IPv6Network if is_ipv6 else IPv4Network

            with tarfile.open(tmp_path, "r:gz") as tar:
                for member in tar.getmembers():
                    # Path traversal 방지: 절대 경로나 상위 디렉토리 참조 차단
                    if member.name.startswith("/") or ".." in member.name:
                        logger.warning(f"Unsafe tar member 감지: {member.name}")
                        continue
                    if member.isfile() and member.name.endswith(".zone"):
                        country_code = (
                            os.path.basename(member.name).replace(".zone", "").upper()
                        )
                        content = tar.extractfile(member)
                        if content:
                            blocks = []
                            for line in content.read().decode("utf-8").splitlines():
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    try:
                                        network_class(line, strict=False)
                                        blocks.append(line)
                                    except AddressValueError:
                                        continue
                            if blocks:
                                country_blocks[country_code] = blocks

            return country_blocks
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def get_country_codes(self) -> List[str]:
        """사용 가능한 국가 코드 목록"""
        data = self.download()
        ipv4 = set(data.get("ipv4_blocks", {}).keys())
        ipv6 = set(data.get("ipv6_blocks", {}).keys())
        return sorted(ipv4 | ipv6)


# =============================================================================
# AbuseIPDB 데이터 제공자
# =============================================================================


class AbuseIPDBProvider:
    """AbuseIPDB 악성 IP 목록 데이터 제공자"""

    DEFAULT_URL = "https://raw.githubusercontent.com/borestad/blocklist-abuseipdb/main/abuseipdb-s100-30d.ipv4"

    def __init__(self):
        """AbuseIPDB 제공자 초기화"""
        self._cache = IPDataCache("abuseipdb", expiry_hours=12)

    def download(self, url: Optional[str] = None) -> Dict[str, Any]:
        """AbuseIPDB 목록 다운로드 및 파싱

        Returns:
            {
                "abuse_ips": ["1.2.3.4", ...],
                "abuse_ip_details": {
                    "1.2.3.4": {"countryCode": "CN", "asn": "AS12345", "isp": "..."},
                    ...
                },
                "timestamp": "...",
            }
        """
        url = url or self.DEFAULT_URL

        # 캐시 확인
        cached = self._cache.load()
        if cached:
            logger.debug("✓ 캐시된 AbuseIPDB 데이터 사용")
            # list를 set으로 변환 (호환성)
            cached["abuse_ips"] = set(cached.get("abuse_ips", []))
            return cached

        logger.debug("🔒 AbuseIPDB 데이터 다운로드 중...")

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            abuse_ips: Set[str] = set()
            abuse_details: Dict[str, Dict[str, str]] = {}

            for line in response.text.splitlines():
                if not line.strip() or line.startswith("#"):
                    continue

                if "#" in line:
                    parts = line.strip().split("#", 1)
                    ip = parts[0].strip()
                    if ip:
                        abuse_ips.add(ip)
                        if len(parts) > 1:
                            info_parts = parts[1].strip().split(None, 2)
                            abuse_details[ip] = {
                                "countryCode": info_parts[0] if info_parts else "N/A",
                                "asn": info_parts[1] if len(info_parts) > 1 else "N/A",
                                "isp": info_parts[2] if len(info_parts) > 2 else "N/A",
                            }

            result = {
                "abuse_ips": list(abuse_ips),
                "abuse_ip_details": abuse_details,
            }

            self._cache.save(result)
            logger.debug(f"✅ AbuseIPDB 다운로드 완료: {len(abuse_ips):,}개 악성 IP")

            # set으로 반환 (편의성)
            result["abuse_ips"] = abuse_ips
            return result

        except Exception as e:
            logger.error(f"❌ AbuseIPDB 다운로드 실패: {e}")
            return {"abuse_ips": set(), "abuse_ip_details": {}}

    def is_abuse_ip(self, ip: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """IP가 악성 IP인지 확인"""
        if data is None:
            data = self.download()
        return ip in data.get("abuse_ips", set())


# =============================================================================
# 통합 IP 인텔리전스 클래스
# =============================================================================


class IPIntelligence:
    """IP 인텔리전스 통합 클래스

    IPDeny (국가 매핑) + AbuseIPDB (악성 IP) 기능을 통합 제공합니다.
    """

    def __init__(self):
        """IP 인텔리전스 초기화"""
        self._ipdeny = IPDenyProvider()
        self._abuseipdb = AbuseIPDBProvider()

        # 네트워크 객체 캐시
        self._ipv4_networks: Dict[str, List[ipaddress.IPv4Network]] = {}
        self._ipv6_networks: Dict[str, List[ipaddress.IPv6Network]] = {}

        # 빠른 조회를 위한 버킷 인덱스
        self._ipv4_index: Dict[int, List[Tuple[ipaddress.IPv4Network, str]]] = {}
        self._ipv6_index: Dict[int, List[Tuple[ipaddress.IPv6Network, str]]] = {}

        # IP 결과 캐시
        self._ip_cache: Dict[str, Optional[str]] = {}

        # AbuseIPDB 데이터 캐시
        self._abuse_data: Optional[Dict[str, Any]] = None

        self._initialized = False

    def initialize(self) -> bool:
        """IP 인텔리전스 데이터 초기화"""
        if self._initialized:
            return True

        try:
            logger.debug("🌍 IP 인텔리전스 초기화 중...")

            # IPDeny 데이터 로드
            data = self._ipdeny.download()
            if not data.get("ipv4_blocks") and not data.get("ipv6_blocks"):
                logger.warning("⚠️ IPDeny 데이터가 비어있습니다.")
                return False

            # IPv4 네트워크 객체 생성
            for country, blocks in data.get("ipv4_blocks", {}).items():
                networks = []
                for block in blocks:
                    try:
                        networks.append(ipaddress.IPv4Network(block, strict=False))
                    except ipaddress.AddressValueError:
                        continue
                if networks:
                    self._ipv4_networks[country] = networks

            # IPv6 네트워크 객체 생성
            for country, blocks in data.get("ipv6_blocks", {}).items():
                networks = []
                for block in blocks:
                    try:
                        networks.append(ipaddress.IPv6Network(block, strict=False))
                    except ipaddress.AddressValueError:
                        continue
                if networks:
                    self._ipv6_networks[country] = networks

            # 인덱스 구축
            self._build_indexes()

            self._initialized = True

            total_countries = len(
                set(self._ipv4_networks.keys()) | set(self._ipv6_networks.keys())
            )
            total_ipv4 = sum(len(n) for n in self._ipv4_networks.values())
            total_ipv6 = sum(len(n) for n in self._ipv6_networks.values())

            logger.debug(
                f"✅ IP 인텔리전스 초기화 완료: {total_countries}개 국가, "
                f"IPv4 {total_ipv4:,}개, IPv6 {total_ipv6:,}개"
            )
            return True

        except Exception as e:
            logger.error(f"❌ IP 인텔리전스 초기화 실패: {e}")
            return False

    def _build_indexes(self) -> None:
        """빠른 조회를 위한 인덱스 구축"""
        # IPv4 인덱스 (첫 옥텟 기준)
        self._ipv4_index.clear()
        for country, networks in self._ipv4_networks.items():
            for network in networks:
                start = int(network.network_address) >> 24
                end = int(network.broadcast_address) >> 24
                for octet in range(start, end + 1):
                    self._ipv4_index.setdefault(octet, []).append((network, country))
        for bucket in self._ipv4_index.values():
            bucket.sort(key=lambda x: x[0].prefixlen, reverse=True)

        # IPv6 인덱스 (상위 8비트 기준)
        self._ipv6_index.clear()
        for country, networks in self._ipv6_networks.items():
            for network in networks:
                start = int(network.network_address) >> 120
                end = int(network.broadcast_address) >> 120
                for b in range(start, end + 1):
                    self._ipv6_index.setdefault(b, []).append((network, country))
        for bucket in self._ipv6_index.values():
            bucket.sort(key=lambda x: x[0].prefixlen, reverse=True)

        logger.debug(
            f"인덱스 구축 완료: IPv4 {len(self._ipv4_index):,}개, "
            f"IPv6 {len(self._ipv6_index):,}개 버킷"
        )

    # -------------------------------------------------------------------------
    # 국가 매핑 API
    # -------------------------------------------------------------------------

    def get_country_code(self, ip_str: str) -> Optional[str]:
        """IP 주소의 국가 코드 반환

        Args:
            ip_str: IP 주소 문자열

        Returns:
            국가 코드 (예: "KR", "US") 또는 특수 코드:
            - "PRIVATE": 사설 IP
            - "LOOPBACK": 루프백
            - "LINK_LOCAL": 링크 로컬
            - "MULTICAST": 멀티캐스트
            - None: 매칭 없음
        """
        # 캐시 확인
        if ip_str in self._ip_cache:
            return self._ip_cache[ip_str]

        if not self._initialized and not self.initialize():
            return None

        try:
            ip = ipaddress.ip_address(ip_str)
        except ipaddress.AddressValueError:
            return None

        # 특수 IP 처리
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            result = self._get_special_ip_type(ip)
            self._ip_cache[ip_str] = result
            return result

        # 국가 매칭
        if isinstance(ip, ipaddress.IPv4Address):
            result = self._match_ipv4(ip)
        else:
            result = self._match_ipv6(ip)

        self._ip_cache[ip_str] = result
        return result

    def _match_ipv4(self, ip: ipaddress.IPv4Address) -> Optional[str]:
        """IPv4 주소 국가 매칭 (Longest-Prefix-Win)"""
        first_octet = int(ip) >> 24
        candidates = self._ipv4_index.get(first_octet, [])

        best_country: Optional[str] = None
        best_prefix: int = -1

        for network, country in candidates:
            if ip in network and network.prefixlen > best_prefix:
                best_prefix = network.prefixlen
                best_country = country

        # Fallback: 전체 탐색
        if best_country is None:
            for country, networks in self._ipv4_networks.items():
                for network in networks:
                    if ip in network and network.prefixlen > best_prefix:
                        best_prefix = network.prefixlen
                        best_country = country

        return best_country

    def _match_ipv6(self, ip: ipaddress.IPv6Address) -> Optional[str]:
        """IPv6 주소 국가 매칭 (Longest-Prefix-Win)"""
        first_byte = int(ip) >> 120
        candidates = self._ipv6_index.get(first_byte, [])

        best_country: Optional[str] = None
        best_prefix: int = -1

        for network, country in candidates:
            if ip in network and network.prefixlen > best_prefix:
                best_prefix = network.prefixlen
                best_country = country

        # Fallback: 전체 탐색
        if best_country is None:
            for country, networks in self._ipv6_networks.items():
                for network in networks:
                    if ip in network and network.prefixlen > best_prefix:
                        best_prefix = network.prefixlen
                        best_country = country

        return best_country

    def _get_special_ip_type(self, ip: ipaddress._BaseAddress) -> str:
        """특수 IP 타입 반환"""
        if ip.is_loopback:
            return "LOOPBACK"
        elif ip.is_link_local:
            return "LINK_LOCAL"
        elif ip.is_multicast:
            return "MULTICAST"
        elif ip.is_private:
            return "PRIVATE"
        return "UNKNOWN"

    def get_country_codes_batch(self, ip_addresses: List[str]) -> Dict[str, str]:
        """여러 IP 주소의 국가 코드 일괄 조회

        Args:
            ip_addresses: IP 주소 목록

        Returns:
            {IP: 국가코드} 딕셔너리 (매칭 없으면 "ZZ")
        """
        if not self._initialized and not self.initialize():
            return {ip: "ZZ" for ip in ip_addresses}

        special_types = {"PRIVATE", "LOOPBACK", "LINK_LOCAL", "MULTICAST", "UNKNOWN"}
        results = {}

        for ip in ip_addresses:
            country = self.get_country_code(ip)
            results[ip] = "ZZ" if country in special_types or not country else country

        return results

    def get_country_statistics(self, ip_addresses: List[str]) -> Dict[str, int]:
        """IP 주소 목록의 국가별 통계"""
        counts: Dict[str, int] = {}
        special_types = {"PRIVATE", "LOOPBACK", "LINK_LOCAL", "MULTICAST", "UNKNOWN"}

        for ip in ip_addresses:
            country = self.get_country_code(ip)
            if not country or country in special_types:
                country = "ZZ"
            counts[country] = counts.get(country, 0) + 1

        return counts

    # -------------------------------------------------------------------------
    # 악성 IP API
    # -------------------------------------------------------------------------

    def download_abuse_data(self) -> Dict[str, Any]:
        """AbuseIPDB 데이터 다운로드

        Returns:
            {
                "abuse_ips": set(...),
                "abuse_ip_details": {...},
            }
        """
        if self._abuse_data is None:
            self._abuse_data = self._abuseipdb.download()
        return self._abuse_data

    def is_abuse_ip(self, ip: str) -> bool:
        """IP가 악성 IP인지 확인"""
        data = self.download_abuse_data()
        return ip in data.get("abuse_ips", set())

    def get_abuse_details(self, ip: str) -> Optional[Dict[str, str]]:
        """악성 IP의 상세 정보 반환"""
        data = self.download_abuse_data()
        return data.get("abuse_ip_details", {}).get(ip)

    def get_abuse_ips_in_list(self, ip_addresses: List[str]) -> List[str]:
        """목록 중 악성 IP만 반환"""
        data = self.download_abuse_data()
        abuse_set = data.get("abuse_ips", set())
        return [ip for ip in ip_addresses if ip in abuse_set]

    # -------------------------------------------------------------------------
    # 통합 API
    # -------------------------------------------------------------------------

    def analyze_ip(self, ip: str) -> Dict[str, Any]:
        """IP 종합 분석

        Returns:
            {
                "ip": "1.2.3.4",
                "country_code": "CN",
                "is_abuse": True,
                "abuse_details": {"countryCode": "CN", "asn": "...", "isp": "..."},
                "is_special": False,
                "special_type": None,
            }
        """
        country = self.get_country_code(ip)
        special_types = {"PRIVATE", "LOOPBACK", "LINK_LOCAL", "MULTICAST", "UNKNOWN"}

        return {
            "ip": ip,
            "country_code": country if country not in special_types else "ZZ",
            "is_abuse": self.is_abuse_ip(ip),
            "abuse_details": self.get_abuse_details(ip),
            "is_special": country in special_types,
            "special_type": country if country in special_types else None,
        }

    def get_available_countries(self) -> List[str]:
        """사용 가능한 국가 코드 목록"""
        if not self._initialized and not self.initialize():
            return []
        return sorted(set(self._ipv4_networks.keys()) | set(self._ipv6_networks.keys()))

    def is_initialized(self) -> bool:
        """초기화 여부"""
        return self._initialized
