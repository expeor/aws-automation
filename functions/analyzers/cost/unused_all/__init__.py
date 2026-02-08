"""
plugins/cost/unused_all - 미사용 리소스 종합 분석 (병렬 처리)

모든 미사용 리소스 종합 보고서:
- NAT Gateway, ENI, EBS, EIP, ELB, Target Group
- EBS Snapshot, AMI, RDS Snapshot
- CloudWatch Log Group
- VPC Endpoint, Secrets Manager, KMS
- ECR, Route53, S3
- Lambda, ElastiCache, RDS Instance
- EFS, SQS, SNS, ACM
- API Gateway, EventBridge, CloudWatch Alarm
- DynamoDB

병렬 처리 전략:
1. 계정/리전 레벨: parallel_collect로 병렬 처리
2. 리소스 타입 레벨: ThreadPoolExecutor로 병렬 수집

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 옵션. 사용자 입력 수집.
"""

# 메인 진입점
from .orchestrator import collect_options, run

# 리포트 생성 (외부 호출 가능)
from .report import generate_report

# 타입 (외부 사용 가능)
from .types import (
    RESOURCE_FIELD_MAP,
    WASTE_FIELDS,
    SessionCollectionResult,
    UnusedAllResult,
    UnusedResourceSummary,
)

__all__: list[str] = [
    # 메인 진입점
    "run",
    "collect_options",
    # 타입
    "UnusedResourceSummary",
    "SessionCollectionResult",
    "UnusedAllResult",
    "RESOURCE_FIELD_MAP",
    "WASTE_FIELDS",
    # 리포트
    "generate_report",
]
