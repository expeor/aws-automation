"""
reports/ip_search - IP Search Tools

Submodules:
    - public_ip: Cloud provider IP range search (AWS, GCP, Azure, Oracle)
    - private_ip: AWS ENI cache-based internal IP search

Each submodule provides its own `run(ctx)` entry point.

Usage:
    from reports.ip_search.public_ip import run as public_search
    from reports.ip_search.private_ip import run as private_search
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
