"""
plugins/sqs - SQS 분석 도구

SQS 큐 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "sqs",
    "display_name": "SQS",
    "description": "SQS 큐 관리",
    "aliases": ["queue", "message"],
}

TOOLS = [
    {
        "name": "미사용 SQS 큐 분석",
        "description": "유휴/미사용 SQS 큐 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
