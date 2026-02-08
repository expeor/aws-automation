"""
functions/analyzers/sso - IAM Identity Center(SSO) 보안 감사 도구

IAM Identity Center의 Permission Set 위험 정책, Admin 권한 현황,
미사용 사용자, MFA 설정을 점검합니다.
글로벌 서비스로 리전 선택이 불필요합니다.

도구 목록:
    - sso_audit: Permission Set 위험 정책, Admin 권한 현황, 미사용 사용자, MFA 점검
"""

CATEGORY = {
    "name": "sso",
    "display_name": "IAM Identity Center",
    "description": "IAM Identity Center(SSO) 보안 감사 도구",
    "description_en": "IAM Identity Center (SSO) Security Audit",
    "aliases": ["identity-center", "sso-audit"],
}

TOOLS = [
    {
        "name": "SSO 보안 점검",
        "name_en": "SSO Security Check",
        "description": "Permission Set 위험 정책, Admin 권한 현황, 미사용 사용자, MFA 점검",
        "description_en": "Permission Set risk policies, admin permissions, unused users, MFA audit",
        "permission": "read",
        "module": "sso_audit",
        "area": "security",
        "is_global": True,
    },
]
