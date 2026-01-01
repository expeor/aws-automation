"""
plugins/sso - IAM Identity Center(SSO) 보안 감사 및 관리 도구

도구 목록:
    - SSO 종합 점검: Permission Set, 사용자, MFA, 권한 할당 등 종합 점검
"""

CATEGORY = {
    "name": "sso",
    "description": "IAM Identity Center(SSO) 보안 감사 도구",
    "aliases": ["identity-center", "sso-audit"],
}

TOOLS = [
    {
        "name": "SSO 종합 점검",
        "description": "Permission Set 위험 정책, Admin 권한 현황, 미사용 사용자, MFA 점검",
        "permission": "read",
        "module": "sso_audit",
        "area": "security",
        "is_global": True,  # Identity Center는 Global 서비스 - 리전 선택 불필요
    },
]
