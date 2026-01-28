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
    # Unused resource detection
    {
        "name": "미사용 Lambda 탐지",
        "name_en": "Unused Lambda Detection",
        "description": "미사용 Lambda 함수 탐지 (30일 이상 미호출)",
        "description_en": "Detect unused Lambda functions (30+ days no invocations)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "미사용 Lambda Version 탐지",
        "name_en": "Unused Lambda Version Detection",
        "description": "오래된 버전 및 미사용 Alias 탐지",
        "description_en": "Detect old versions and unused aliases",
        "permission": "read",
        "module": "versions",
        "area": "unused",
    },
    # Inventory
    {
        "name": "Lambda 현황",
        "name_en": "Lambda Inventory",
        "description": "런타임 EOL, 메모리, 비용, 에러율 현황",
        "description_en": "Runtime EOL, memory, cost, error rate inventory",
        "permission": "read",
        "module": "comprehensive",
        "area": "inventory",
    },
    # Cost optimization
    {
        "name": "Provisioned Concurrency 비용 최적화",
        "name_en": "Provisioned Concurrency Cost Optimization",
        "description": "PC 최적화 (과다/부족 설정 탐지)",
        "description_en": "PC optimization (over/under-provisioned detection)",
        "permission": "read",
        "module": "provisioned",
        "area": "cost",
    },
]
