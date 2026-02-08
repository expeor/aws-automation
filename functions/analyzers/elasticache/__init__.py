"""
functions/analyzers/elasticache - ElastiCache 클러스터 관리 도구

ElastiCache(Redis/Memcached) 클러스터의 사용 현황을 분석하고
유휴/저사용 클러스터를 탐지합니다.

도구 목록:
    - unused: 유휴/저사용 ElastiCache 클러스터 탐지 (Redis/Memcached)
"""

CATEGORY = {
    "name": "elasticache",
    "display_name": "ElastiCache",
    "description": "ElastiCache 클러스터 관리 (Redis/Memcached)",
    "description_en": "ElastiCache Cluster Management (Redis/Memcached)",
    "aliases": ["cache"],
    "sub_services": ["redis", "memcached"],
}

TOOLS = [
    {
        "name": "미사용 ElastiCache 클러스터 탐지",
        "name_en": "Unused ElastiCache Cluster Detection",
        "description": "유휴/저사용 ElastiCache 클러스터 탐지 (Redis/Memcached)",
        "description_en": "Detect idle/underutilized ElastiCache clusters (Redis/Memcached)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
