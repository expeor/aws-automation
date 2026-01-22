"""
plugins/cloudtrail - CloudTrail Log Management Tools
"""

CATEGORY = {
    "name": "cloudtrail",
    "display_name": "CloudTrail",
    "description": "CloudTrail 로그 관리 및 분석",
    "description_en": "CloudTrail Log Management and Analysis",
    "aliases": ["trail", "audit-log"],
}

TOOLS = [
    {
        "name": "설정 현황",
        "name_en": "Configuration Status",
        "description": "전체 계정의 CloudTrail 설정 현황 보고서",
        "description_en": "CloudTrail configuration status report for all accounts",
        "permission": "read",
        "module": "trail_audit",
        "function": "run",
        "area": "security",
    },
    {
        "name": "보안 이벤트",
        "name_en": "Security Events",
        "description": "최근 90일 보안 이벤트 (루트 로그인, IAM 변경 등) - us-east-1 자동 포함",
        "description_en": "Last 90 days security events (root login, IAM changes) - includes us-east-1",
        "permission": "read",
        "module": "security_events",
        "area": "security",
    },
]
