"""functions/reports/cost_dashboard/__init__.py - 미사용 리소스 종합 분석 패키지.

AWS 전 서비스에 걸쳐 미사용 리소스를 병렬로 수집하고 분석하여 종합 Excel 보고서를 생성합니다.

지원 리소스:
    - 네트워크: NAT Gateway, ENI, EIP, VPC Endpoint
    - 스토리지: EBS Volume/Snapshot, AMI, RDS Snapshot, ECR, S3, EFS
    - 컴퓨팅: Lambda, ElastiCache, RDS Instance, DynamoDB
    - 로드밸런싱: ELB, Target Group
    - 보안/관리: KMS, Secrets Manager, ACM
    - 모니터링: CloudWatch Log Group, CloudWatch Alarm
    - 기타: Route53, API Gateway, EventBridge, SQS, SNS

병렬 처리 전략:
    1. 계정/리전 레벨: ``parallel_collect``로 멀티 계정/리전 병렬 처리
    2. 리소스 타입 레벨: ``ThreadPoolExecutor``로 리소스 유형별 병렬 수집

플러그인 규약:
    - ``run(ctx)``: 필수. 도구 실행 엔트리포인트.
    - ``collect_options(ctx)``: 선택. 실행 전 사용자 입력 수집.
"""

# 카테고리 정의 (Discovery용)
CATEGORY = {
    "name": "cost_dashboard",
    "display_name": "Cost Dashboard",
    "description": "미사용 리소스 종합 분석 대시보드",
    "description_en": "Comprehensive Unused Resources Dashboard",
    "aliases": ["unused_all", "cost_report", "waste"],
}

TOOLS = [
    {
        "name": "미사용 리소스 종합 탐지",
        "name_en": "Comprehensive Unused Resources Detection",
        "description": "NAT, ENI, EBS, EIP, ELB, Snapshot, DynamoDB 등 미사용 리소스 종합 보고서",
        "description_en": "Comprehensive unused resources report (NAT, ENI, EBS, EIP, ELB, Snapshot, DynamoDB)",
        "permission": "read",
        "module": "orchestrator",
        "area": "cost",
        "timeline_phases": ["리소스 수집", "보고서"],
    },
]

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
    # Discovery 메타데이터
    "CATEGORY",
    "TOOLS",
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
