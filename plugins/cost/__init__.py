"""
plugins/cost - Cost Optimization and Cost Explorer Tools

Cost analysis, unused resources report, budget management
Individual unused resource analysis is in each service category (vpc, ec2, etc.)
"""

CATEGORY = {
    "name": "cost",
    "display_name": "Cost Explorer",
    "description": "비용 최적화 및 Cost Explorer",
    "description_en": "Cost Optimization and Cost Explorer",
    "aliases": ["billing", "savings", "optimization"],
}

TOOLS = [
    {
        "name": "미사용 리소스 종합 탐지",
        "name_en": "Comprehensive Unused Resources Detection",
        "description": "NAT, ENI, EBS, EIP, ELB, Snapshot, DynamoDB 등 미사용 리소스 종합 보고서",
        "description_en": "Comprehensive unused resources report (NAT, ENI, EBS, EIP, ELB, Snapshot, DynamoDB)",
        "permission": "read",
        "module": "unused_all",
        "area": "cost",
    },
    {
        "name": "Cost Optimization Hub 현황",
        "name_en": "Cost Optimization Hub Inventory",
        "description": "AWS Cost Optimization Hub에서 모든 비용 최적화 권장사항 조회",
        "description_en": "Retrieve all cost optimization recommendations from AWS Cost Optimization Hub",
        "permission": "read",
        "module": "coh",
        "area": "cost",
    },
    {
        "name": "COH Rightsizing 권장사항",
        "name_en": "COH Rightsizing Recommendations",
        "description": "EC2, RDS, Lambda, ECS 등 리소스 라이트사이징 권장사항",
        "description_en": "Rightsizing recommendations for EC2, RDS, Lambda, ECS resources",
        "permission": "read",
        "module": "coh",
        "function": "run_rightsizing",
        "area": "cost",
    },
    {
        "name": "COH Idle Resources 권장사항",
        "name_en": "COH Idle Resources Recommendations",
        "description": "유휴/미사용 리소스 권장사항 (Stop, Delete)",
        "description_en": "Idle/unused resource recommendations (Stop, Delete)",
        "permission": "read",
        "module": "coh",
        "function": "run_idle_resources",
        "area": "cost",
    },
    {
        "name": "COH Commitment 권장사항",
        "name_en": "COH Commitment Recommendations",
        "description": "Savings Plans 및 Reserved Instances 권장사항",
        "description_en": "Savings Plans and Reserved Instances recommendations",
        "permission": "read",
        "module": "coh",
        "function": "run_commitment",
        "area": "cost",
    },
]
