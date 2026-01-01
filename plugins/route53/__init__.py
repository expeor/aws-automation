"""
plugins/route53 - Route 53 DNS 관리 도구

Hosted Zone, 레코드셋, 헬스체크 등 DNS 리소스 분석

도구 목록:
    - 빈 Hosted Zone: 레코드가 없는 빈 Zone 탐지
"""

CATEGORY = {
    "name": "route53",
    "description": "Route 53 DNS 관리",
    "aliases": ["dns", "domain", "r53"],
}

TOOLS = [
    {
        "name": "빈 Hosted Zone 분석",
        "description": "레코드가 없는 빈 Hosted Zone 탐지",
        "permission": "read",
        "module": "empty_zone",
        "area": "cost",
    },
]
