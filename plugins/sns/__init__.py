"""
plugins/sns - SNS 분석 도구

SNS 토픽 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "sns",
    "display_name": "SNS",
    "description": "SNS 토픽 관리",
    "aliases": ["topic", "notification", "pubsub"],
}

TOOLS = [
    {
        "name": "미사용 SNS 토픽 분석",
        "description": "유휴/미사용 SNS 토픽 탐지",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
]
