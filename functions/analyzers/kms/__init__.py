"""
functions/analyzers/kms - KMS 키 관리 도구

KMS 고객 관리 키(CMK)의 사용 현황을 분석하고, 미사용/비활성화 키 탐지,
키 사용처 매핑, 키 로테이션/정책/Grants 보안 감사를 수행합니다.

도구 목록:
    - unused: 미사용/비활성화 CMK 탐지
    - key_usage: 고객 관리 키(CMK)가 사용되는 AWS 리소스 매핑
    - audit: 키 로테이션, 정책, Grants 보안 감사
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
        "name": "미사용 KMS 키 탐지",
        "name_en": "Unused KMS Key Detection",
        "description": "미사용/비활성화 CMK 탐지",
        "description_en": "Detect unused/disabled CMKs",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "CMK 사용처 조회",
        "name_en": "CMK Usage Lookup",
        "description": "고객 관리 키(CMK)가 사용되는 AWS 리소스 매핑",
        "description_en": "Map AWS resources using Customer Managed Keys (CMK)",
        "permission": "read",
        "module": "key_usage",
        "area": "search",
    },
    {
        "name": "KMS 보안 점검",
        "name_en": "KMS Security Check",
        "description": "키 로테이션, 정책, Grants 보안 감사",
        "description_en": "Key rotation, policy, and Grants security audit",
        "permission": "read",
        "module": "audit",
        "area": "security",
    },
]
