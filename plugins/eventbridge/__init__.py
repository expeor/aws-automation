"""
plugins/eventbridge - EventBridge Rule Management Tools
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
        "name": "미사용 EventBridge 규칙 분석",
        "name_en": "Unused EventBridge Rule Analysis",
        "description": "비활성화/미사용 규칙 탐지",
        "description_en": "Detect disabled/unused rules",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
