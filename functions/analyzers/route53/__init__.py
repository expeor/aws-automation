"""
plugins/route53 - Route 53 DNS Management Tools
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
