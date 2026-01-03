"""
plugins/iam - IAM 보안 감사 및 관리 도구

도구 목록:
    - IAM 종합 점검: 사용자, 역할, Access Key, MFA, 비밀번호 정책 등 종합 점검
"""

CATEGORY = {
    "name": "iam",
    "display_name": "IAM",
    "description": "IAM 보안 감사 및 관리 도구",
    "aliases": ["iam-audit", "security"],
}

TOOLS = [
    {
        "name": "IAM 종합 점검",
        "description": "사용자, 역할, Access Key, MFA, 비밀번호 정책 등 보안 점검",
        "permission": "read",
        "module": "iam_audit",
        "area": "security",
        "is_global": True,  # IAM은 Global 서비스 - 리전 선택 불필요
    },
]
