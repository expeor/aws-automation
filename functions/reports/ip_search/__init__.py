"""functions/reports/ip_search/__init__.py - IP 검색 도구 패키지.

클라우드 환경에서 IP 주소의 소유자와 리소스 매핑 정보를 검색합니다.

하위 모듈:
    - public_ip: 클라우드 프로바이더(AWS, GCP, Azure, Oracle) IP 대역 검색.
      AWS 인증 불필요.
    - private_ip: AWS ENI 캐시 기반 내부 IP 검색.
      멀티 계정/리전 캐시 관리 지원.

각 하위 모듈은 독립적인 ``run(ctx)`` 엔트리포인트를 제공합니다.

Example:
    >>> from functions.reports.ip_search.public_ip import run as public_search
    >>> from functions.reports.ip_search.private_ip import run as private_search
"""

CATEGORY = {
    "name": "ip_search",
    "display_name": "IP Search",
    "description": "IP 주소 검색 (Public/Private)",
    "description_en": "IP Address Search (Public/Private)",
    "aliases": ["ip", "ipsearch", "ip_lookup"],
}

TOOLS = [
    {
        "name": "Public IP 검색",
        "name_en": "Public IP Search",
        "description": "AWS, GCP, Azure, Oracle 등 클라우드 IP 대역 검색",
        "description_en": "Search cloud provider IP ranges (AWS, GCP, Azure, Oracle)",
        "permission": "read",
        "module": "public_ip.tool",
        "area": "search",
        "require_session": False,
    },
    {
        "name": "Private IP 검색",
        "name_en": "Private IP Search",
        "description": "AWS ENI 캐시 기반 내부 IP 검색",
        "description_en": "AWS ENI cache-based internal IP search",
        "permission": "read",
        "module": "private_ip.tool",
        "area": "search",
        "require_session": False,
    },
]

__all__: list[str] = ["CATEGORY", "TOOLS"]
