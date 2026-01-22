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
        "name": "IAM 종합 점검",
        "name_en": "IAM Comprehensive Audit",
        "description": "사용자, 역할, Access Key, MFA, 비밀번호 정책 등 보안 점검",
        "description_en": "Security audit for users, roles, access keys, MFA, password policies",
        "permission": "read",
        "module": "iam_audit",
        "area": "security",
        "is_global": True,  # IAM is a Global service - no region selection needed
    },
]
