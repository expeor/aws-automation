"""
functions/analyzers/secretsmanager - Secrets Manager 시크릿 관리 도구

Secrets Manager 시크릿의 사용 현황을 분석하고
미사용 시크릿을 탐지하여 비용 절감 기회를 제공합니다.

도구 목록:
    - unused: 미사용 시크릿 탐지 및 비용 분석
"""

CATEGORY = {
    "name": "secretsmanager",
    "display_name": "Secrets Manager",
    "description": "Secrets Manager 시크릿 관리",
    "description_en": "Secrets Manager Secret Management",
    "aliases": ["secrets", "sm"],
}

TOOLS = [
    {
        "name": "미사용 시크릿 탐지",
        "name_en": "Unused Secret Detection",
        "description": "미사용 시크릿 탐지 및 비용 분석",
        "description_en": "Detect unused secrets and cost analysis",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
