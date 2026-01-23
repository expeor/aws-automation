"""
plugins/secretsmanager - Secrets Manager Tools
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
