"""
plugins/secretsmanager - Secrets Manager 분석 도구

시크릿 관리 및 미사용 시크릿 탐지
"""

CATEGORY = {
    "name": "secretsmanager",
    "description": "Secrets Manager 시크릿 관리",
    "aliases": ["secrets", "sm"],
}

TOOLS = [
    {
        "name": "미사용 시크릿 분석",
        "description": "미사용 시크릿 탐지 및 비용 분석",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
]
