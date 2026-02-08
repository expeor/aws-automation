"""
functions/analyzers/opensearch - OpenSearch 도메인 관리 및 최적화 도구

OpenSearch(Elasticsearch Service) 도메인의 사용량을 CloudWatch 지표
기반으로 분석하고 유휴/저사용 도메인을 탐지합니다.

도구 목록:
    - unused: 유휴/저사용 OpenSearch 도메인 탐지 (CloudWatch 지표 기반)
"""

CATEGORY = {
    "name": "opensearch",
    "display_name": "OpenSearch",
    "description": "OpenSearch 도메인 관리 및 최적화",
    "description_en": "OpenSearch Domain Management and Optimization",
    "aliases": ["es", "elasticsearch", "search"],
}

TOOLS = [
    {
        "name": "미사용 도메인 분석",
        "name_en": "Unused Domain Analysis",
        "description": "유휴/저사용 OpenSearch 도메인 탐지 (CloudWatch 지표 기반)",
        "description_en": "Detect idle/low-usage OpenSearch domains based on CloudWatch metrics",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
