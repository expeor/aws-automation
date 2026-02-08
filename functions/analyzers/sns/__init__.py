"""
functions/analyzers/sns - SNS 토픽 관리 도구

SNS 토픽의 사용 현황을 분석하고
유휴/미사용 토픽을 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 SNS 토픽 탐지
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
        "name": "미사용 SNS 토픽 탐지",
        "name_en": "Unused SNS Topic Detection",
        "description": "유휴/미사용 SNS 토픽 탐지",
        "description_en": "Detect idle/unused SNS topics",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
