"""
functions/analyzers/redshift - Redshift 클러스터 관리 및 최적화 도구

Redshift 데이터 웨어하우스 클러스터의 사용량을 CloudWatch 지표
기반으로 분석하고 유휴/저사용 클러스터를 탐지합니다.

도구 목록:
    - unused: 유휴/저사용 Redshift 클러스터 탐지 (CloudWatch 지표 기반)
"""

CATEGORY = {
    "name": "redshift",
    "display_name": "Redshift",
    "description": "Redshift 클러스터 관리 및 최적화",
    "description_en": "Redshift Cluster Management and Optimization",
    "aliases": ["rs", "datawarehouse", "dw"],
}

TOOLS = [
    {
        "name": "미사용 클러스터 분석",
        "name_en": "Unused Cluster Analysis",
        "description": "유휴/저사용 Redshift 클러스터 탐지 (CloudWatch 지표 기반)",
        "description_en": "Detect idle/low-usage Redshift clusters based on CloudWatch metrics",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
