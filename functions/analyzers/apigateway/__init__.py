"""
plugins/apigateway - API Gateway Management Tools
"""

CATEGORY = {
    "name": "apigateway",
    "display_name": "API Gateway",
    "description": "API Gateway 관리",
    "description_en": "API Gateway Management",
    "aliases": ["api", "gateway", "apigw"],
}

TOOLS = [
    {
        "name": "미사용 API Gateway 탐지",
        "name_en": "Unused API Gateway Detection",
        "description": "유휴/미사용 API 탐지",
        "description_en": "Detect idle/unused APIs",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
