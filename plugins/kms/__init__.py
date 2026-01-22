"""
plugins/kms - KMS Key Management Tools
"""

CATEGORY = {
    "name": "kms",
    "display_name": "KMS",
    "description": "KMS 키 관리",
    "description_en": "KMS Key Management",
    "aliases": ["key", "cmk"],
}

TOOLS = [
    {
        "name": "미사용 KMS 키 분석",
        "name_en": "Unused KMS Key Analysis",
        "description": "미사용/비활성화 CMK 탐지",
        "description_en": "Detect unused/disabled CMKs",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "CMK 사용처 분석",
        "name_en": "CMK Usage Analysis",
        "description": "고객 관리 키(CMK)가 사용되는 AWS 리소스 매핑",
        "description_en": "Map AWS resources using Customer Managed Keys (CMK)",
        "permission": "read",
        "module": "key_usage",
        "area": "search",
    },
    {
        "name": "KMS 감사 보고서",
        "name_en": "KMS Audit Report",
        "description": "키 로테이션, 정책, Grants 보안 감사",
        "description_en": "Key rotation, policy, and Grants security audit",
        "permission": "read",
        "module": "audit",
        "area": "security",
    },
]
