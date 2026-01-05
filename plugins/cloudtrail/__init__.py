"""
plugins/cloudtrail - CloudTrail 관리 도구

CloudTrail 현황 분석 및 보고서 생성
"""

CATEGORY = {
    "name": "cloudtrail",
    "display_name": "CloudTrail",
    "description": "CloudTrail 로그 관리 및 분석",
    "aliases": ["trail", "audit-log"],
}

TOOLS = [
    {
        "name": "설정 현황",
        "description": "전체 계정의 CloudTrail 설정 현황 보고서",
        "permission": "read",
        "module": "trail_audit",
        "function": "run",
        "area": "security",
    },
    {
        "name": "보안 이벤트",
        "description": "최근 90일 보안 이벤트 (루트 로그인, IAM 변경 등) - us-east-1 자동 포함",
        "permission": "read",
        "module": "security_events",
        "area": "security",
    },
]
