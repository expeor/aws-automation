"""
functions/analyzers/eventbridge - EventBridge 규칙 관리 도구

EventBridge 규칙의 활성화 상태를 분석하고
비활성화/미사용 규칙을 탐지합니다.

도구 목록:
    - unused: 비활성화/미사용 EventBridge 규칙 탐지
"""

CATEGORY = {
    "name": "eventbridge",
    "display_name": "EventBridge",
    "description": "EventBridge 규칙 관리",
    "description_en": "EventBridge Rule Management",
    "aliases": ["events", "eb", "cwe"],
}

TOOLS = [
    {
        "name": "미사용 EventBridge 규칙 탐지",
        "name_en": "Unused EventBridge Rule Detection",
        "description": "비활성화/미사용 규칙 탐지",
        "description_en": "Detect disabled/unused rules",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
