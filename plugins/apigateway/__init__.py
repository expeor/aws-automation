"""
plugins/apigateway - API Gateway 분석 도구

API Gateway 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "apigateway",
    "display_name": "API Gateway",
    "description": "API Gateway 관리",
    "aliases": ["api", "gateway", "apigw"],
}

TOOLS = [
    {
        "name": "미사용 API Gateway 분석",
        "description": "유휴/미사용 API 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
