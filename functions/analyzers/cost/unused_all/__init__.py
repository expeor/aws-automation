"""
functions/analyzers/cost/unused_all - 미사용 리소스 종합 분석 (병렬 처리)

35개 이상의 AWS 리소스 타입에 대해 미사용/유휴 리소스를 일괄 분석하고,
종합 Excel 보고서를 생성합니다.

분석 대상 리소스:
    - Compute: AMI, EBS, EBS Snapshot, EIP, ENI, EC2 Instance
    - Networking: NAT Gateway, VPC Endpoint
    - Load Balancing: ELB, Target Group
    - Database: DynamoDB, ElastiCache, Redshift, OpenSearch, RDS, RDS Snapshot
    - Storage: ECR, EFS, S3, FSx
    - Serverless: API Gateway, EventBridge, Lambda
    - ML: SageMaker Endpoint
    - Messaging: SNS, SQS
    - Security: ACM, KMS, Secrets Manager, Security Group
    - Monitoring: CloudWatch Alarm, Log Group
    - DNS: Route53
    - Analytics: Kinesis, Glue
    - File Transfer: Transfer Family

병렬 처리 전략:
    1. 계정/리전 레벨: parallel_collect로 멀티 계정/리전 병렬 처리
    2. 리소스 타입 레벨: ThreadPoolExecutor로 단일 세션 내 병렬 수집
    3. 글로벌 서비스: 계정당 한 번만 수집 (thread-safe 동기화)

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
