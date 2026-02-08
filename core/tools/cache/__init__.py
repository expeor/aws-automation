"""공통 캐시 경로 및 TTL 관리.

모든 캐시 파일은 프로젝트 루트의 ``temp/`` 하위에 저장됩니다.
캐시 경로 생성, TTL 기반 유효성 검사, 캐시 우선 데이터 조회 기능을 제공합니다.

디렉토리 구조::

    temp/
    ├── ip/           <- IP 관련 캐시 (pub_ip_search, ip_intelligence)
    │   ├── azure_servicetags_cache.json
    │   ├── cloudflare_ips_cache.json
    │   └── ...
    ├── eni/          <- ENI 캐시 (run_ip_search)
    │   └── network_interfaces_cache_{session}.msgpack
    └── history/      <- 사용 이력 (recent, favorites, profile_groups)

Example:
    ::

        from core.tools.cache import get_cache_dir, get_cache_path, get_or_fetch

        # 캐시 디렉토리 경로
        cache_dir = get_cache_dir("ip")

        # 캐시 파일 경로
        cache_path = get_cache_path("ip", "azure_servicetags_cache.json")

        # 캐시 우선 데이터 조회
        data = get_or_fetch("pricing", "ec2_prices.json", fetch_fn=fetch_ec2_prices)
"""

from .path import CACHE_ROOT, get_cache_dir, get_cache_path
from .ttl import CACHE_TTL, DEFAULT_TTL, get_or_fetch, get_ttl, is_cache_valid

__all__: list[str] = [
    "get_cache_dir",
    "get_cache_path",
    "CACHE_ROOT",
    "CACHE_TTL",
    "DEFAULT_TTL",
    "get_ttl",
    "is_cache_valid",
    "get_or_fetch",
]
