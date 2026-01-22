"""
plugins/sns - SNS Topic Management Tools
"""

CATEGORY = {
    "name": "sns",
    "display_name": "SNS",
    "description": "SNS 토픽 관리",
    "description_en": "SNS Topic Management",
    "aliases": ["topic", "notification", "pubsub"],
}

TOOLS = [
    {
        "name": "미사용 SNS 토픽 분석",
        "name_en": "Unused SNS Topic Analysis",
        "description": "유휴/미사용 SNS 토픽 탐지",
        "description_en": "Detect idle/unused SNS topics",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
