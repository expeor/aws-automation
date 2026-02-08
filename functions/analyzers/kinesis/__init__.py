"""
plugins/kinesis - Kinesis Stream Analysis Tools

Kinesis Data Streams management and optimization
"""

CATEGORY = {
    "name": "kinesis",
    "display_name": "Kinesis",
    "description": "Kinesis 스트림 관리 및 최적화",
    "description_en": "Kinesis Stream Management and Optimization",
    "aliases": ["stream", "streaming"],
}

TOOLS = [
    {
        "name": "미사용 스트림 분석",
        "name_en": "Unused Stream Analysis",
        "description": "유휴/저사용 Kinesis 스트림 탐지 (CloudWatch 지표 기반)",
        "description_en": "Detect idle/low-usage Kinesis streams based on CloudWatch metrics",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
