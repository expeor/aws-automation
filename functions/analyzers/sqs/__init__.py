"""
plugins/sqs - SQS Queue Management Tools
"""

CATEGORY = {
    "name": "sqs",
    "display_name": "SQS",
    "description": "SQS 큐 관리",
    "description_en": "SQS Queue Management",
    "aliases": ["queue", "message"],
}

TOOLS = [
    {
        "name": "미사용 SQS 큐 탐지",
        "name_en": "Unused SQS Queue Detection",
        "description": "유휴/미사용 SQS 큐 탐지",
        "description_en": "Detect idle/unused SQS queues",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
