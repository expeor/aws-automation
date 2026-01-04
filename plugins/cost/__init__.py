"""
plugins/cost - 비용 최적화 및 Cost Explorer 도구

비용 분석, 미사용 리소스 종합 보고서, 예산 관리 등
개별 미사용 리소스 분석은 각 서비스 카테고리에 위치 (vpc, ec2 등)
"""

CATEGORY = {
    "name": "cost",
    "display_name": "Cost Explorer",
    "description": "비용 최적화 및 Cost Explorer",
    "aliases": ["billing", "savings", "optimization"],
}

TOOLS = [
    {
        "name": "미사용 리소스 종합 분석",
        "description": "NAT, ENI, EBS, EIP, ELB, Snapshot, DynamoDB 등 미사용 리소스 종합 보고서",
        "permission": "read",
        "module": "unused_all",
        "area": "cost",
    },
    {
        "name": "Cost Optimization Hub 분석",
        "description": "AWS Cost Optimization Hub에서 모든 비용 최적화 권장사항 조회",
        "permission": "read",
        "module": "coh",
        "area": "cost",
    },
    {
        "name": "COH Rightsizing 분석",
        "description": "EC2, RDS, Lambda, ECS 등 리소스 라이트사이징 권장사항",
        "permission": "read",
        "module": "coh",
        "function": "run_rightsizing",
        "area": "cost",
    },
    {
        "name": "COH Idle Resources 분석",
        "description": "유휴/미사용 리소스 권장사항 (Stop, Delete)",
        "permission": "read",
        "module": "coh",
        "function": "run_idle_resources",
        "area": "cost",
    },
    {
        "name": "COH Commitment 분석",
        "description": "Savings Plans 및 Reserved Instances 권장사항",
        "permission": "read",
        "module": "coh",
        "function": "run_commitment",
        "area": "cost",
    },
]
