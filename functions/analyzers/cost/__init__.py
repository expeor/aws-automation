"""
functions/analyzers/cost - 비용 최적화 및 Cost Explorer 도구

AWS Cost Optimization Hub를 통해 비용 최적화 권장사항(Rightsizing,
Idle Resources, Commitment)을 조회하고 분석합니다.
개별 서비스의 미사용 리소스 분석은 각 서비스 카테고리(ec2, vpc 등)에 있습니다.

도구 목록:
    - coh: Cost Optimization Hub 전체 권장사항 조회
    - coh (run_rightsizing): EC2, RDS, Lambda, ECS 등 라이트사이징 권장사항
    - coh (run_idle_resources): 유휴/미사용 리소스 권장사항 (Stop, Delete)
    - coh (run_commitment): Savings Plans 및 Reserved Instances 권장사항
"""

CATEGORY = {
    "name": "cost",
    "display_name": "Cost Explorer",
    "description": "비용 최적화 및 Cost Explorer",
    "description_en": "Cost Optimization and Cost Explorer",
    "aliases": ["billing", "savings", "optimization"],
}

TOOLS = [
    # NOTE: "미사용 리소스 종합 탐지" moved to reports/cost_dashboard
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
