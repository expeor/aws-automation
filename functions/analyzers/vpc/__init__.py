"""
functions/analyzers/vpc - VPC 및 네트워크 리소스 분석 도구

Security Group, NAT Gateway, VPC Endpoint, ENI 등 네트워크 리소스를
분석합니다. 보안 점검, 미사용 리소스 탐지, 인벤토리 기능을 제공합니다.

도구 목록:
    - sg_audit: 위험한 인바운드 규칙, 미사용 SG/규칙 탐지
    - sg_inventory: 모든 Security Group의 인바운드/아웃바운드 규칙 전체 목록 추출
    - network_analysis: 미사용 NAT Gateway, VPC Endpoint, ENI 통합 탐지
    - inventory: ENI, NAT Gateway, VPC Endpoint 현황 조회
"""

CATEGORY = {
    "name": "vpc",
    "display_name": "VPC",
    "description": "VPC 및 네트워크 리소스 관리",
    "description_en": "VPC and Network Resource Management",
    "aliases": ["network", "sg", "security-group", "nat"],
}

TOOLS = [
    # NOTE: IP search tools moved to reports/ip_search
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
    {
        "name": "Security Group 정책 내역",
        "name_en": "Security Group Policy Inventory",
        "description": "모든 Security Group의 인바운드/아웃바운드 규칙 전체 목록 추출",
        "description_en": "Export all Security Group inbound/outbound rules",
        "permission": "read",
        "module": "sg_inventory",
        "area": "inventory",
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
    # Inventory
    {
        "name": "VPC 리소스 인벤토리",
        "name_en": "VPC Resource Inventory",
        "description": "ENI, NAT Gateway, VPC Endpoint 현황 조회",
        "description_en": "List ENIs, NAT Gateways, VPC Endpoints",
        "permission": "read",
        "module": "inventory",
        "area": "inventory",
    },
]
