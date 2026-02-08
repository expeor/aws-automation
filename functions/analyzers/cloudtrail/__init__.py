"""
functions/analyzers/cloudtrail - CloudTrail 로그 관리 및 분석 도구

CloudTrail 설정 현황을 점검하고, 최근 90일간 보안 이벤트
(루트 로그인, IAM 변경 등)를 조회합니다.

도구 목록:
    - trail_audit: 전체 계정의 CloudTrail 설정 현황 보고서
    - security_events: 최근 90일 보안 이벤트 조회 (us-east-1 자동 포함)
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
        "name": "CloudTrail 설정 현황",
        "name_en": "CloudTrail Configuration Status",
        "description": "전체 계정의 CloudTrail 설정 현황 보고서",
        "description_en": "CloudTrail configuration status report for all accounts",
        "permission": "read",
        "module": "trail_audit",
        "function": "run",
        "area": "security",
    },
    {
        "name": "CloudTrail 보안 이벤트 조회",
        "name_en": "CloudTrail Security Event Lookup",
        "description": "최근 90일 보안 이벤트 (루트 로그인, IAM 변경 등) - us-east-1 자동 포함",
        "description_en": "Last 90 days security events (root login, IAM changes) - includes us-east-1",
        "permission": "read",
        "module": "security_events",
        "area": "security",
    },
]
