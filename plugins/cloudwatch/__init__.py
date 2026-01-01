"""
plugins/cloudwatch - CloudWatch 분석 도구

CloudWatch Logs, Metrics, Alarms 관련 분석
"""

CATEGORY = {
    "name": "cloudwatch",
    "description": "CloudWatch 모니터링 및 로그 관리",
    "aliases": ["cw", "logs", "metrics"],
}

TOOLS = [
    {
        "name": "Log Group 미사용 분석",
        "description": "빈 로그 그룹 및 오래된 로그 탐지",
        "permission": "read",
        "module": "loggroup_audit",
        "area": "cost",
    },
]
