"""
plugins/vpc - VPC 관련 분석 도구

Security Group, VPC, Subnet, NAT Gateway 등 네트워크 리소스 분석
"""

CATEGORY = {
    "name": "vpc",
    "display_name": "VPC",
    "description": "VPC 및 네트워크 리소스 관리",
    "aliases": ["network", "sg", "security-group", "nat"],
}

TOOLS = [
    {
        "name": "IP 검색",
        "description": "공인/사설 IP 검색 (AWS, GCP, Azure, Oracle + ENI 캐시)",
        "permission": "read",
        "module": "ip_search",  # ip_search/ 폴더
        "area": "security",
    },
    {
        "name": "Security Group 감사",
        "description": "SG 현황 및 미사용 SG/규칙 분석",
        "permission": "read",
        "module": "sg_audit",
        "area": "security",
    },
    {
        "name": "NAT Gateway 미사용 분석",
        "description": "미사용/저사용 NAT Gateway 탐지 및 비용 절감 기회 식별",
        "permission": "read",
        "module": "nat_audit",
        "area": "cost",
    },
    {
        "name": "ENI 미사용 분석",
        "description": "미사용 ENI (Elastic Network Interface) 탐지",
        "permission": "read",
        "module": "eni_audit",
        "area": "cost",
    },
    {
        "name": "VPC Endpoint 분석",
        "description": "VPC Endpoint 현황 및 비용 분석",
        "permission": "read",
        "module": "endpoint_audit",
        "area": "cost",
    },
]
