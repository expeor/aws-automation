"""
plugins/elasticache - ElastiCache 분석 도구

ElastiCache 클러스터 관리 및 미사용 리소스 탐지

하위 서비스:
    - redis: ElastiCache for Redis
    - memcached: ElastiCache for Memcached

CLI 사용법:
    aa elasticache  → 모든 ElastiCache 도구
    aa redis        → Redis 전용 도구만
    aa memcached    → Memcached 전용 도구만
"""

CATEGORY = {
    "name": "elasticache",
    "display_name": "ElastiCache",
    "description": "ElastiCache 클러스터 관리 (Redis/Memcached)",
    "aliases": ["cache"],
    # 하위 서비스 정의 - 각각 별도 CLI 명령어로 등록됨
    "sub_services": ["redis", "memcached"],
}

TOOLS = [
    # 전체 ElastiCache 분석 (Redis + Memcached)
    {
        "name": "미사용 ElastiCache 클러스터 분석",
        "description": "유휴/저사용 ElastiCache 클러스터 탐지 (Redis/Memcached)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
        # sub_service 미지정 → aa elasticache에서만 표시 (전체 대상)
    },
    # TODO: Redis 전용 도구 추가 시 sub_service: "redis"
    # TODO: Memcached 전용 도구 추가 시 sub_service: "memcached"
]
