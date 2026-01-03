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
        "description": "NAT, ENI, EBS, EIP, ELB, Snapshot 미사용 리소스 종합 보고서",
        "permission": "read",
        "module": "unused_all",
        "area": "cost",
    },
    # 향후 추가:
    # - Cost Explorer 분석
    # - 예산 현황
    # - 비용 트렌드
]
