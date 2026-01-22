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
    # Search tools
    {
        "name": "클라우드 IP 대역 조회",
        "name_en": "Cloud IP Range Lookup",
        "description": "IP가 어느 클라우드(AWS, GCP, Azure, Oracle) 소속인지 확인",
        "description_en": "Check which cloud provider owns an IP (AWS, GCP, Azure, Oracle)",
        "permission": "read",
        "module": "ip_search.public_ip",
        "area": "search",
        "require_session": False,
    },
    {
        "name": "내부 IP 리소스 조회",
        "name_en": "Internal IP Resource Lookup",
        "description": "내부 IP가 어떤 AWS 리소스(EC2, Lambda, ECS 등)에 할당되어 있는지 확인",
        "description_en": "Find which AWS resource (EC2, Lambda, ECS, etc.) an internal IP belongs to",
        "permission": "read",
        "module": "ip_search.private_ip",
        "area": "search",
        "require_session": False,
    },
    # Security tools
    {
        "name": "Security Group 보안 점검",
        "name_en": "Security Group Security Check",
        "description": "위험한 인바운드 규칙, 미사용 SG/규칙 탐지",
        "description_en": "Detect risky inbound rules, unused SGs/rules",
        "permission": "read",
        "module": "sg_audit",
        "area": "security",
    },
    # Unused resource detection
    {
        "name": "미사용 네트워크 리소스 탐지",
        "name_en": "Unused Network Resource Detection",
        "description": "미사용 NAT Gateway, VPC Endpoint, ENI 통합 탐지",
        "description_en": "Detect unused NAT Gateway, VPC Endpoint, ENI",
        "permission": "read",
        "module": "network_analysis",
        "area": "unused",
    },
]
