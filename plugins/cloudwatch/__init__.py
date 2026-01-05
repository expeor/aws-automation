"""
plugins/cloudwatch - CloudWatch 분석 도구

CloudWatch Logs, Metrics, Alarms 관련 분석
"""

CATEGORY = {
    "name": "cloudwatch",
    "display_name": "CloudWatch",
    "description": "CloudWatch 모니터링 및 로그 관리",
    "aliases": ["cw", "logs", "metrics"],
}

TOOLS = [
    {
        "name": "Log Group 미사용 분석",
        "description": "빈 로그 그룹 및 오래된 로그 탐지",
        "permission": "read",
        "module": "loggroup_audit",
        "area": "unused",
    },
    {
        "name": "고아 알람 분석",
        "description": "모니터링 대상 없는 알람 탐지",
        "permission": "read",
        "module": "alarm_orphan",
        "area": "unused",
    },
]
