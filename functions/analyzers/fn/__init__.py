"""
functions/analyzers/fn - Lambda 함수 관리 및 분석 도구

Lambda 함수의 사용 현황, 런타임 EOL, 메모리/비용/에러율을 분석합니다.
미사용 함수 및 버전 탐지, 런타임 지원 종료 분석, Provisioned Concurrency
비용 최적화 기능을 제공합니다.

Note:
    폴더명 'fn': 'lambda'는 Python 예약어이므로 'fn'을 사용합니다.

도구 목록:
    - unused: 미사용 Lambda 함수 탐지 (30일 이상 미호출)
    - versions: 오래된 버전 및 미사용 Alias 탐지
    - comprehensive: 런타임 EOL, 메모리, 비용, 에러율 현황
    - runtime_deprecated: Lambda 런타임 지원 종료 현황 분석 (종료됨/곧 종료/안전, OS 버전, 업그레이드 경로)
    - provisioned: Provisioned Concurrency 비용 최적화 (과다/부족 설정 탐지)
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
    # Security
    {
        "name": "런타임 지원 종료 분석",
        "name_en": "Runtime Deprecation Analysis",
        "description": "Lambda 런타임 지원 종료 현황 분석 (종료됨/곧 종료/안전 분류, OS 버전, 업그레이드 경로)",
        "description_en": "Lambda runtime deprecation analysis (deprecated/soon/safe, OS version, upgrade path)",
        "permission": "read",
        "module": "runtime_deprecated",
        "area": "security",
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
