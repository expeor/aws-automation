"""
plugins/elasticache - ElastiCache Cluster Management Tools
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
        "name": "미사용 ElastiCache 클러스터 분석",
        "name_en": "Unused ElastiCache Cluster Analysis",
        "description": "유휴/저사용 ElastiCache 클러스터 탐지 (Redis/Memcached)",
        "description_en": "Detect idle/underutilized ElastiCache clusters (Redis/Memcached)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
