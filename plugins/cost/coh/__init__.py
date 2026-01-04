"""
plugins/cost/coh - AWS Cost Optimization Hub 플러그인

AWS Cost Optimization Hub에서 비용 최적화 권장사항을 조회하고 분석합니다.

## 지원하는 권장사항 유형

### Resource Optimization
- **Rightsize**: EC2, RDS, Lambda, ECS, EBS 등 리소스 크기 조정
- **Stop**: 유휴 리소스 중지 (EC2, RDS)
- **Delete**: 미사용 리소스 삭제 (EBS, ECS, Aurora)
- **Scale In**: Auto Scaling Group 축소
- **Upgrade**: 최신 세대로 업그레이드 (EC2, EBS, RDS)
- **Migrate to Graviton**: ARM 기반 Graviton으로 마이그레이션

### Commitment-based Savings
- **Purchase Savings Plans**: Compute, EC2 Instance, SageMaker Savings Plans
- **Purchase Reserved Instances**: EC2, RDS, Redshift, OpenSearch, ElastiCache, MemoryDB, DynamoDB

## AWS 문서 참조
- Getting Started: https://docs.aws.amazon.com/cost-management/latest/userguide/cost-optimization-hub-getting-started.html
- Understanding Strategies: https://docs.aws.amazon.com/cost-management/latest/userguide/coh-strategies.html
- Prioritizing Opportunities: https://docs.aws.amazon.com/cost-management/latest/userguide/coh-prioritizing.html
- Cost Efficiency Metric: https://docs.aws.amazon.com/cost-management/latest/userguide/cost-efficiency-metric.html
- API Reference: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_Operations_Cost_Optimization_Hub.html

## Note
- Cost Optimization Hub는 us-east-1 리전에서만 사용 가능
- Organizations 관리 계정 또는 위임된 관리자 계정에서 전체 조직 권장사항 조회 가능
- 권장사항은 매일 새로고침됨 (전일 사용량 기준)
"""

# CLI 도구 정의
TOOLS = [
    {
        "name": "Cost Optimization Hub 분석",
        "description": "AWS Cost Optimization Hub에서 모든 비용 최적화 권장사항 조회 (Rightsizing, Idle, Savings Plans 등)",
        "permission": "read",
        "module": "coh",
        "function": "run_analysis",
        "area": "cost",
    },
    {
        "name": "Cost Optimization Hub - Rightsizing",
        "description": "EC2, RDS, Lambda, ECS 등 리소스 라이트사이징 권장사항",
        "permission": "read",
        "module": "coh",
        "function": "run_rightsizing",
        "area": "cost",
    },
    {
        "name": "Cost Optimization Hub - Idle Resources",
        "description": "유휴/미사용 리소스 권장사항 (Stop, Delete)",
        "permission": "read",
        "module": "coh",
        "function": "run_idle_resources",
        "area": "cost",
    },
    {
        "name": "Cost Optimization Hub - Commitment",
        "description": "Savings Plans 및 Reserved Instances 권장사항",
        "permission": "read",
        "module": "coh",
        "function": "run_commitment",
        "area": "cost",
    },
]
