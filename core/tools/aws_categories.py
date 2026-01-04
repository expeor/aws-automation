"""
core/tools/aws_categories.py - AWS 서비스 카테고리 매핑

AWS 공식 문서 기반 서비스 그룹 분류
참조: https://docs.aws.amazon.com/whitepapers/latest/aws-overview/
"""

# AWS 서비스 카테고리 정의 (AWS 공식 분류 기준)
# services 리스트는 각 서비스 폴더의 CATEGORY["name"] 값과 매칭
# 폴더 구조: plugins/{service}/ (예: plugins/rds/, plugins/ec2/)
AWS_SERVICE_CATEGORIES: dict[str, dict] = {
    # =========================================================================
    # Compute
    # =========================================================================
    "compute": {
        "name": "Compute",
        "name_ko": "컴퓨팅",
        "services": [
            "ec2",
            "lambda",
            "elasticbeanstalk",
        ],
    },
    # =========================================================================
    # Containers
    # =========================================================================
    "containers": {
        "name": "Containers",
        "name_ko": "컨테이너",
        "services": [
            "ecr",
            "ecs",
            "eks",
        ],
    },
    # =========================================================================
    # Storage
    # =========================================================================
    "storage": {
        "name": "Storage",
        "name_ko": "스토리지",
        "services": [
            "s3",
            "ebs",
            "efs",
            "fsx",
            "aws_backup",
        ],
    },
    # =========================================================================
    # Database
    # =========================================================================
    "database": {
        "name": "Database",
        "name_ko": "데이터베이스",
        "services": [
            "rds",
            "dynamodb",
            "docdb",
            "elasticache",
            "opensearch",
        ],
    },
    # =========================================================================
    # Networking & Content Delivery
    # =========================================================================
    "networking": {
        "name": "Networking & Content Delivery",
        "name_ko": "네트워킹 및 콘텐츠 전송",
        "services": [
            "vpc",
            "elb",
            "route53",
            "cloudfront",
            "apigateway",
        ],
    },
    # =========================================================================
    # Security, Identity & Compliance
    # =========================================================================
    "security": {
        "name": "Security, Identity & Compliance",
        "name_ko": "보안, 자격 증명 및 규정 준수",
        "services": [
            "iam",
            "kms",
            "waf",
            "guardduty",
            "secretsmanager",
            "acm",
            "cognito",
            "sso",
        ],
    },
    # =========================================================================
    # Management & Governance
    # =========================================================================
    "management": {
        "name": "Management & Governance",
        "name_ko": "관리 및 거버넌스",
        "services": [
            "cloudwatch",
            "cloudtrail",
            "config",
            "ssm",
            "servicecatalog",
            "organizations",
            "tag",
        ],
    },
    # =========================================================================
    # Analytics
    # =========================================================================
    "analytics": {
        "name": "Analytics",
        "name_ko": "분석",
        "services": [
            "kinesis",
            "glue",
            "athena",
            "redshift",
            "emr",
            "log",
        ],
    },
    # =========================================================================
    # Application Integration
    # =========================================================================
    "application_integration": {
        "name": "Application Integration",
        "name_ko": "애플리케이션 통합",
        "services": [
            "sns",
            "sqs",
            "eventbridge",
            "stepfunctions",
        ],
    },
    # =========================================================================
    # Developer Tools
    # =========================================================================
    "developer_tools": {
        "name": "Developer Tools",
        "name_ko": "개발자 도구",
        "services": [
            "codecommit",
            "codebuild",
            "codepipeline",
            "cfn",
        ],
    },
    # =========================================================================
    # Machine Learning
    # =========================================================================
    "machine_learning": {
        "name": "Machine Learning",
        "name_ko": "기계 학습",
        "services": [
            "bedrock",
            "sagemaker",
        ],
    },
    # =========================================================================
    # Cloud Financial Management
    # =========================================================================
    "cost_management": {
        "name": "Cloud Financial Management",
        "name_ko": "클라우드 비용 관리",
        "services": [
            "ce",
            "cost",
        ],
    },
    # =========================================================================
    # Migration & Transfer
    # =========================================================================
    "migration": {
        "name": "Migration & Transfer",
        "name_ko": "마이그레이션 및 전송",
        "services": [],
    },
    # =========================================================================
    # Media Services
    # =========================================================================
    "media": {
        "name": "Media Services",
        "name_ko": "미디어 서비스",
        "services": [],
    },
    # =========================================================================
    # Internet of Things
    # =========================================================================
    "iot": {
        "name": "Internet of Things",
        "name_ko": "사물 인터넷",
        "services": [],
    },
    # =========================================================================
    # Game Tech
    # =========================================================================
    "game_tech": {
        "name": "Game Tech",
        "name_ko": "게임 기술",
        "services": [],
    },
    # =========================================================================
    # Satellite
    # =========================================================================
    "satellite": {
        "name": "Satellite",
        "name_ko": "위성",
        "services": [],
    },
    # =========================================================================
    # Quantum Technologies
    # =========================================================================
    "quantum": {
        "name": "Quantum Technologies",
        "name_ko": "양자 기술",
        "services": [],
    },
    # =========================================================================
    # End User Computing
    # =========================================================================
    "end_user_computing": {
        "name": "End User Computing",
        "name_ko": "최종 사용자 컴퓨팅",
        "services": [],
    },
    # =========================================================================
    # Business Applications
    # =========================================================================
    "business_apps": {
        "name": "Business Applications",
        "name_ko": "비즈니스 애플리케이션",
        "services": [],
    },
    # =========================================================================
    # Frontend Web & Mobile
    # =========================================================================
    "frontend_mobile": {
        "name": "Frontend Web & Mobile",
        "name_ko": "프론트엔드 웹 및 모바일",
        "services": [],
    },
    # =========================================================================
    # Customer Enablement
    # =========================================================================
    "customer_enablement": {
        "name": "Customer Enablement",
        "name_ko": "고객 지원",
        "services": [],
    },
    # =========================================================================
    # Blockchain
    # =========================================================================
    "blockchain": {
        "name": "Blockchain",
        "name_ko": "블록체인",
        "services": [],
    },
}

# 서비스 → AWS 카테고리 역매핑 (첫 번째 매칭만 저장)
SERVICE_TO_CATEGORY: dict[str, str] = {}
for cat_key, cat_info in AWS_SERVICE_CATEGORIES.items():
    for service in cat_info["services"]:
        if service not in SERVICE_TO_CATEGORY:
            SERVICE_TO_CATEGORY[service] = cat_key


def get_aws_categories() -> list[dict]:
    """AWS 서비스 카테고리 목록 반환 (도구가 있는 카테고리만)

    Returns:
        [
            {
                "key": "compute",
                "name": "Compute",
                "name_ko": "컴퓨팅",
                "services": ["ec2", "lambda", ...]
            },
            ...
        ]
    """
    result = []
    for key, info in AWS_SERVICE_CATEGORIES.items():
        if info["services"]:
            result.append({"key": key, **info})
    return result


def get_services_by_aws_category(category_key: str) -> list[str]:
    """특정 AWS 카테고리에 속한 서비스 목록 반환

    Args:
        category_key: AWS 카테고리 키 (예: "compute", "storage")

    Returns:
        서비스 이름 목록
    """
    if category_key in AWS_SERVICE_CATEGORIES:
        services: list[str] = AWS_SERVICE_CATEGORIES[category_key]["services"]
        return services
    return []


def get_aws_category_for_service(service_name: str) -> str:
    """서비스가 속한 AWS 카테고리 반환

    Args:
        service_name: 서비스 이름 (예: "ec2", "s3")

    Returns:
        AWS 카테고리 키 또는 "other"
    """
    return SERVICE_TO_CATEGORY.get(service_name, "other")


def get_aws_category_view() -> list[dict]:
    """AWS 카테고리별로 플러그인을 그룹핑하여 반환

    discovery에서 발견된 플러그인을 AWS 공식 카테고리로 그룹핑합니다.
    플러그인이 있는 카테고리만 반환합니다.

    Returns:
        [
            {
                "key": "compute",
                "name": "Compute",
                "name_ko": "컴퓨팅",
                "plugins": [<ec2 카테고리>, <lambda 카테고리>, ...],
                "tool_count": 15
            },
            ...
        ]
    """
    from core.tools.discovery import discover_categories

    all_plugins = discover_categories(include_aws_services=True)
    plugin_map = {p.get("name", ""): p for p in all_plugins}

    result = []
    for cat_key, cat_info in AWS_SERVICE_CATEGORIES.items():
        services_in_cat = cat_info.get("services", [])
        matched_plugins = []

        for service_name in services_in_cat:
            if service_name in plugin_map:
                matched_plugins.append(plugin_map[service_name])

        if matched_plugins:
            result.append(
                {
                    "key": cat_key,
                    "name": cat_info["name"],
                    "name_ko": cat_info["name_ko"],
                    "plugins": matched_plugins,
                    "tool_count": sum(len(p.get("tools", [])) for p in matched_plugins),
                }
            )

    return result
