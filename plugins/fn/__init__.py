"""
plugins/fn - Lambda 관련 분석 도구

Lambda 함수 미사용, 런타임 EOL, 비용 분석 등

폴더명 fn: 'lambda'가 Python 예약어이므로 function의 약자 사용
"""

CATEGORY = {
    "name": "fn",
    "display_name": "Lambda",
    "description": "Lambda 함수 관리 및 분석",
    "aliases": ["lambda", "function", "serverless"],
}

TOOLS = [
    {
        "name": "Lambda 미사용 분석",
        "description": "미사용 Lambda 함수 탐지 (30일 이상 미호출)",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
    {
        "name": "Lambda 종합 분석",
        "description": "런타임 EOL, 메모리, 비용, 에러율 종합 분석",
        "permission": "read",
        "module": "comprehensive",
        "area": "cost",
    },
    {
        "name": "Provisioned Concurrency 분석",
        "description": "PC 최적화 분석 (과다/부족 설정 탐지)",
        "permission": "read",
        "module": "provisioned",
        "area": "cost",
    },
    {
        "name": "Version/Alias 정리",
        "description": "오래된 버전 및 미사용 Alias 탐지",
        "permission": "read",
        "module": "versions",
        "area": "operational",
    },
]
