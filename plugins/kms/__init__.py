"""
plugins/kms - KMS 분석 도구

KMS 키 관리 및 미사용 키 탐지
"""

CATEGORY = {
    "name": "kms",
    "description": "KMS 키 관리",
    "aliases": ["key", "cmk"],
}

TOOLS = [
    {
        "name": "미사용 KMS 키 분석",
        "description": "미사용/비활성화 CMK 탐지",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
]
