"""
plugins/eventbridge - EventBridge 분석 도구

EventBridge 규칙 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "eventbridge",
    "display_name": "EventBridge",
    "description": "EventBridge 규칙 관리",
    "aliases": ["events", "eb", "cwe"],
}

TOOLS = [
    {
        "name": "미사용 EventBridge 규칙 분석",
        "description": "비활성화/미사용 규칙 탐지",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
]
