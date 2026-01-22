"""
plugins/vpc - VPC Analysis Tools

Security Group, VPC, Subnet, NAT Gateway and network resource analysis
"""

CATEGORY = {
    "name": "vpc",
    "display_name": "VPC",
    "description": "VPC 및 네트워크 리소스 관리",
    "description_en": "VPC and Network Resource Management",
    "aliases": ["network", "sg", "security-group", "nat"],
}

TOOLS = [
    {
        "name": "IP 검색",
        "name_en": "IP Search",
        "description": "공인/사설 IP 검색 (AWS, GCP, Azure, Oracle + ENI 캐시)",
        "description_en": "Public/Private IP search (AWS, GCP, Azure, Oracle + ENI cache)",
        "permission": "read",
        "module": "ip_search",  # ip_search/ folder
        "area": "security",
    },
    {
        "name": "Security Group 감사",
        "name_en": "Security Group Audit",
        "description": "SG 현황 및 미사용 SG/규칙 분석",
        "description_en": "SG inventory and unused SG/rules analysis",
        "permission": "read",
        "module": "sg_audit",
        "area": "security",
    },
    {
        "name": "네트워크 리소스 분석",
        "name_en": "Network Resource Analysis",
        "description": "미사용 NAT/Endpoint/ENI 통합 분석",
        "description_en": "Consolidated analysis of unused NAT/Endpoint/ENI",
        "permission": "read",
        "module": "network_analysis",
        "area": "unused",
    },
    # Legacy tools (deprecated - use network_analysis instead)
    {
        "name": "NAT Gateway 미사용 분석",
        "name_en": "Unused NAT Gateway Analysis",
        "description": "미사용/저사용 NAT Gateway 탐지 (→ 네트워크 리소스 분석 권장)",
        "description_en": "Detect unused NAT Gateways (use Network Resource Analysis)",
        "permission": "read",
        "module": "nat_audit",
        "area": "unused",
        "deprecated": True,
    },
    {
        "name": "ENI 미사용 분석",
        "name_en": "Unused ENI Analysis",
        "description": "미사용 ENI 탐지 (→ 네트워크 리소스 분석 권장)",
        "description_en": "Detect unused ENIs (use Network Resource Analysis)",
        "permission": "read",
        "module": "eni_audit",
        "area": "unused",
        "deprecated": True,
    },
    {
        "name": "VPC Endpoint 분석",
        "name_en": "VPC Endpoint Analysis",
        "description": "VPC Endpoint 분석 (→ 네트워크 리소스 분석 권장)",
        "description_en": "VPC Endpoint analysis (use Network Resource Analysis)",
        "permission": "read",
        "module": "endpoint_audit",
        "area": "cost",
        "deprecated": True,
    },
]
