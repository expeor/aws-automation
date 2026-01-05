"""
plugins/kms - KMS 분석 도구

KMS 키 관리 및 미사용 키 탐지
"""

CATEGORY = {
    "name": "kms",
    "display_name": "KMS",
    "description": "KMS 키 관리",
    "aliases": ["key", "cmk"],
}

TOOLS = [
    {
        "name": "미사용 KMS 키 분석",
        "description": "미사용/비활성화 CMK 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "CMK 사용처 분석",
        "description": "고객 관리 키(CMK)가 사용되는 AWS 리소스 매핑",
        "permission": "read",
        "module": "key_usage",
        "area": "search",
    },
    {
        "name": "KMS 감사 보고서",
        "description": "키 로테이션, 정책, Grants 보안 감사",
        "permission": "read",
        "module": "audit",
        "area": "security",
    },
]
