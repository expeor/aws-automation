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
        "name": "빈 Hosted Zone 분석",
        "name_en": "Empty Hosted Zone Analysis",
        "description": "레코드가 없는 빈 Hosted Zone 탐지",
        "description_en": "Detect empty Hosted Zones with no records",
        "permission": "read",
        "module": "empty_zone",
        "area": "cost",
    },
]
