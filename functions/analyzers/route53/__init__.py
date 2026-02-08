"""
functions/analyzers/route53 - Route 53 DNS 관리 도구

Route 53 Hosted Zone의 사용 현황을 분석하고
레코드가 없는 빈 Hosted Zone을 탐지합니다.

도구 목록:
    - empty_zone: 레코드가 없는 빈 Hosted Zone 탐지
"""

CATEGORY = {
    "name": "route53",
    "display_name": "Route 53",
    "description": "Route 53 DNS 관리",
    "description_en": "Route 53 DNS Management",
    "aliases": ["dns", "domain", "r53"],
}

TOOLS = [
    {
        "name": "미사용 Hosted Zone 탐지",
        "name_en": "Unused Hosted Zone Detection",
        "description": "레코드가 없는 빈 Hosted Zone 탐지",
        "description_en": "Detect empty Hosted Zones with no records",
        "permission": "read",
        "module": "empty_zone",
        "area": "unused",
    },
]
