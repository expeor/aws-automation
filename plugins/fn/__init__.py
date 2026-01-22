"""
plugins/fn - Lambda Analysis Tools

Folder name 'fn': 'lambda' is a Python reserved word
"""

CATEGORY = {
    "name": "fn",
    "display_name": "Lambda",
    "description": "Lambda 함수 관리 및 분석",
    "description_en": "Lambda Function Management and Analysis",
    "aliases": ["lambda", "function", "serverless"],
}

TOOLS = [
    {
        "name": "Lambda 미사용 분석",
        "name_en": "Unused Lambda Analysis",
        "description": "미사용 Lambda 함수 탐지 (30일 이상 미호출)",
        "description_en": "Detect unused Lambda functions (30+ days no invocations)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "Lambda 종합 분석",
        "name_en": "Lambda Comprehensive Analysis",
        "description": "런타임 EOL, 메모리, 비용, 에러율 종합 분석",
        "description_en": "Runtime EOL, memory, cost, error rate analysis",
        "permission": "read",
        "module": "comprehensive",
        "area": "audit",
    },
    {
        "name": "Provisioned Concurrency 분석",
        "name_en": "Provisioned Concurrency Analysis",
        "description": "PC 최적화 분석 (과다/부족 설정 탐지)",
        "description_en": "PC optimization (over/under-provisioned detection)",
        "permission": "read",
        "module": "provisioned",
        "area": "cost",
    },
    {
        "name": "Version/Alias 정리",
        "name_en": "Version/Alias Cleanup",
        "description": "오래된 버전 및 미사용 Alias 탐지",
        "description_en": "Detect old versions and unused aliases",
        "permission": "read",
        "module": "versions",
        "area": "cleanup",
    },
]
