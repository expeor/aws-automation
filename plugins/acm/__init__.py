"""
plugins/acm - ACM 분석 도구

AWS Certificate Manager 인증서 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "acm",
    "display_name": "ACM",
    "description": "ACM 인증서 관리",
    "aliases": ["cert", "certificate", "ssl", "tls"],
}

TOOLS = [
    {
        "name": "미사용 ACM 인증서 분석",
        "description": "미사용/만료 임박 인증서 탐지",
        "permission": "read",
        "module": "unused",
        "area": "cost",
    },
]
