"""
pkg/cache - 공통 캐시 경로 관리

모든 캐시 파일은 프로젝트 루트의 temp/ 하위에 저장됩니다.

구조:
    temp/
    ├── ip/           ← IP 관련 캐시 (pub_ip_search, ip_intelligence)
    │   ├── azure_servicetags_cache.json
    │   ├── cloudflare_ips_cache.json
    │   ├── fastly_ips_cache.json
    │   ├── ipdeny_cache.json
    │   ├── abuseipdb_cache.json
    │   └── ...
    └── eni/          ← ENI 캐시 (run_ip_search)
        └── network_interfaces_cache_{session}.msgpack

사용법:
    from core.tools.cache import get_cache_dir, get_cache_path

    # 캐시 디렉토리 경로
    cache_dir = get_cache_dir("ip")
    # → {project_root}/temp/ip/

    # 캐시 파일 경로
    cache_path = get_cache_path("ip", "azure_servicetags_cache.json")
    # → {project_root}/temp/ip/azure_servicetags_cache.json
"""

from .path import CACHE_ROOT, get_cache_dir, get_cache_path

__all__: list[str] = [
    "get_cache_dir",
    "get_cache_path",
    "CACHE_ROOT",
]
