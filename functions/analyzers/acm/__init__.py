"""
functions/analyzers/acm - ACM 인증서 관리 도구

AWS Certificate Manager(ACM) 인증서의 사용 현황을 분석하고
미사용 또는 만료 임박 인증서를 탐지합니다.

도구 목록:
    - unused: 미사용/만료 임박 인증서 탐지
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
