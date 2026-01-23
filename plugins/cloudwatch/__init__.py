"""
plugins/cloudwatch - CloudWatch Monitoring Tools
"""

CATEGORY = {
    "name": "cloudwatch",
    "display_name": "CloudWatch",
    "description": "CloudWatch 모니터링 및 로그 관리",
    "description_en": "CloudWatch Monitoring and Log Management",
    "aliases": ["cw", "logs", "metrics"],
}

TOOLS = [
    {
        "name": "미사용 Log Group 탐지",
        "name_en": "Unused Log Group Detection",
        "description": "빈 로그 그룹 및 오래된 로그 탐지",
        "description_en": "Detect empty log groups and old logs",
        "permission": "read",
        "module": "loggroup_audit",
        "area": "unused",
    },
    {
        "name": "미사용 알람 탐지",
        "name_en": "Unused Alarm Detection",
        "description": "모니터링 대상 없는 알람 탐지",
        "description_en": "Detect alarms without monitoring targets",
        "permission": "read",
        "module": "alarm_orphan",
        "area": "unused",
    },
]
