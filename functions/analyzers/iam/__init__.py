"""
plugins/iam - IAM Security Audit and Management Tools

Tools:
    - IAM Comprehensive Audit: Users, roles, access keys, MFA, password policies
"""

CATEGORY = {
    "name": "iam",
    "display_name": "IAM",
    "description": "IAM 보안 감사 및 관리 도구",
    "description_en": "IAM Security Audit and Management",
    "aliases": ["iam-audit", "security"],
}

TOOLS = [
    {
        "name": "IAM 보안 점검",
        "name_en": "IAM Security Check",
        "description": "사용자, 역할, Access Key, MFA, 비밀번호 정책 등 보안 점검",
        "description_en": "Security audit for users, roles, access keys, MFA, password policies",
        "permission": "read",
        "module": "iam_audit",
        "area": "security",
        "is_global": True,  # IAM is a Global service - no region selection needed
    },
    {
        "name": "IAM 사용자 현황 보고서",
        "name_en": "IAM User Snapshot Report",
        "description": "IAM 사용자 종합 현황 (Access Key, Git Credential, 비활성 사용자, 오래된 키)",
        "description_en": "IAM user snapshot including access keys, git credentials, inactive users, old keys",
        "permission": "read",
        "module": "user_snapshot",
        "area": "inventory",
        "is_global": True,
    },
    {
        "name": "미사용 IAM Role 탐지",
        "name_en": "Unused IAM Roles Detection",
        "description": "365일 이상 미사용 Role 탐지 및 연결 리소스 분석",
        "description_en": "Detect unused IAM roles (365+ days) with connected resource analysis",
        "permission": "read",
        "module": "unused_roles",
        "area": "unused",
        "is_global": True,
    },
]
