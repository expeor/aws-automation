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
        "name": "CloudTrail 전체 보고서",
        "description": "전체 계정의 CloudTrail 설정 현황 보고서 생성",
        "permission": "read",
        "module": "trail_audit",
        "function": "run",
        "area": "security",
    },
]
