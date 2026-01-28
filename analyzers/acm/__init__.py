"""
plugins/acm - ACM Certificate Management Tools
"""

CATEGORY = {
    "name": "acm",
    "display_name": "ACM",
    "description": "ACM 인증서 관리",
    "description_en": "ACM Certificate Management",
    "aliases": ["cert", "certificate", "ssl", "tls"],
}

TOOLS = [
    {
        "name": "미사용 ACM 인증서 탐지",
        "name_en": "Unused ACM Certificate Detection",
        "description": "미사용/만료 임박 인증서 탐지",
        "description_en": "Detect unused/expiring certificates",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
