"""
functions/analyzers/apigateway - API Gateway 관리 도구

API Gateway(REST, HTTP, WebSocket)의 사용 현황을 분석하고
유휴 또는 미사용 API를 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 API Gateway 탐지
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
