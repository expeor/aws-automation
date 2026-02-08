"""AWS 서비스 카테고리 매핑.

AWS 공식 문서 기반 서비스 그룹 분류 체계를 정의합니다.
Compute, Storage, Database 등 AWS 공식 카테고리로 서비스를 그룹핑하며,
서비스 이름과 카테고리 간 역매핑, 글로벌 서비스 목록 등을 제공합니다.

참조: https://docs.aws.amazon.com/whitepapers/latest/aws-overview/

Attributes:
    AWS_SERVICE_CATEGORIES: AWS 서비스 카테고리 정의 딕셔너리.
        키는 카테고리 slug (예: "compute"), 값은 name, name_ko, services 포함 딕셔너리.
    SERVICE_TO_CATEGORY: 서비스명 -> 카테고리 키 역매핑 딕셔너리.
    GLOBAL_SERVICES: 리전 선택이 불필요한 글로벌 서비스 이름 집합.
"""

# AWS 서비스 카테고리 정의 (AWS 공식 분류 기준)
# services 리스트는 각 서비스 폴더의 CATEGORY["name"] 값과 매칭
# 폴더 구조: analyzers/{service}/ (예: analyzers/rds/, analyzers/ec2/)
AWS_SERVICE_CATEGORIES: dict[str, dict] = {
    # =========================================================================
    # Compute
    # =========================================================================
    "compute": {
        "name": "Compute",
        "name_ko": "컴퓨팅",
        "services": [
            "ec2",
            "fn",
            "lightsail",
            "batch",
            "app_runner",
            "outposts",
            "elasticbeanstalk",
            "ec2_image_builder",
            "evs",
            "wavelength",
            "serverless_repo",
            "local_zones",
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
            "fargate",
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
            "backup",
            "efs",
            "fsx",
            "elastic_disaster_recovery",
            "storage_gateway",
            "file_cache",
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
            "aurora",
            "keyspaces",
            "memorydb",
            "neptune",
            "opensearch",
            "timestream",
            "redshift",
            "oracle_db_aws",
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
            "direct_connect",
            "global_accelerator",
            "privatelink",
            "transit_gateway",
            "vpc_lattice",
            "verified_access",
            "cloud_map",
            "cloud_wan",
            "client_vpn",
            "site_to_site_vpn",
            "nat_gateway",
            "app_mesh",
            "network_manager",
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
            "detective",
            "inspector",
            "macie",
            "security_lake",
            "verified_permissions",
            "audit_manager",
            "cloudhsm",
            "directory_service",
            "firewall_manager",
            "network_firewall",
            "ram",
            "security_hub",
            "shield",
            "signer",
            "payment_cryptography",
            "private_ca",
            "wickr",
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
            "tag_editor",
            "health",
            "auto_scaling",
            "appconfig",
            "compute_optimizer",
            "control_tower",
            "launch_wizard",
            "license_manager",
            "managed_grafana",
            "managed_prometheus",
            "resilience_hub",
            "resource_groups",
            "service_quotas",
            "trusted_advisor",
            "well_architected",
            "opsworks",
        ],
    },
    # =========================================================================
    # Analytics
    # =========================================================================
    "analytics": {
        "name": "Analytics",
        "name_ko": "분석",
        "services": [
            "athena",
            "emr",
            "kinesis",
            "kinesis_video",
            "firehose",
            "glue",
            "lakeformation",
            "msk",
            "managed_flink",
            "datazone",
            "quicksight",
            "cleanrooms",
            "dataexchange",
            "datapipeline",
            "entity_resolution",
            "cloudsearch",
            "finspace",
        ],
    },
    # =========================================================================
    # Application Integration
    # =========================================================================
    "application_integration": {
        "name": "Application Integration",
        "name_ko": "애플리케이션 통합",
        "services": [
            "stepfunctions",
            "appflow",
            "b2b_data_interchange",
            "eventbridge",
            "mwaa",
            "mq",
            "sns",
            "sqs",
            "swf",
        ],
    },
    # =========================================================================
    # Developer Tools
    # =========================================================================
    "developer_tools": {
        "name": "Developer Tools",
        "name_ko": "개발자 도구",
        "services": [
            "cloudformation",
            "codecommit",
            "codebuild",
            "codepipeline",
            "codedeploy",
            "codeartifact",
            "codecatalyst",
            "cloud9",
            "cloudshell",
            "infrastructure_composer",
            "corretto",
            "fis",
            "xray",
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
            "comprehend",
            "kendra",
            "lex",
            "personalize",
            "rekognition",
            "textract",
            "transcribe",
            "translate",
            "q_developer",
            "q_business",
            "augmented_ai",
            "codeguru",
            "devops_guru",
            "forecast",
            "fraud_detector",
            "comprehend_medical",
            "lookout_equipment",
            "lookout_metrics",
            "lookout_vision",
            "monitron",
            "partyrock",
            "polly",
            "deepcomposer",
            "deepracer",
            "healthlake",
            "panorama",
        ],
    },
    # =========================================================================
    # Cloud Financial Management
    # =========================================================================
    "cost_management": {
        "name": "Cloud Financial Management",
        "name_ko": "클라우드 비용 관리",
        "services": [
            "cost",
            "ce",
            "billing_conductor",
            "budgets",
            "cur",
            "savings_plans",
        ],
    },
    # =========================================================================
    # Migration & Transfer
    # =========================================================================
    "migration": {
        "name": "Migration & Transfer",
        "name_ko": "마이그레이션 및 전송",
        "services": [
            "transfer",
            "dms",
            "application_migration",
            "migration_hub",
            "datasync",
            "mainframe_modernization",
            "snow_family",
        ],
    },
    # =========================================================================
    # Media Services
    # =========================================================================
    "media": {
        "name": "Media Services",
        "name_ko": "미디어 서비스",
        "services": [
            "mediaconnect",
            "mediaconvert",
            "medialive",
            "mediapackage",
            "mediatailor",
            "elastic_transcoder",
            "ivs",
            "deadline_cloud",
        ],
    },
    # =========================================================================
    # Internet of Things
    # =========================================================================
    "iot": {
        "name": "Internet of Things",
        "name_ko": "사물 인터넷",
        "services": [
            "iot_core",
            "iot_device_defender",
            "iot_device_management",
            "iot_greengrass",
            "iot_sitewise",
            "iot_fleetwise",
            "iot_twinmaker",
        ],
    },
    # =========================================================================
    # Game Tech
    # =========================================================================
    "game_tech": {
        "name": "Game Tech",
        "name_ko": "게임 기술",
        "services": [
            "gamelift",
        ],
    },
    # =========================================================================
    # Satellite
    # =========================================================================
    "satellite": {
        "name": "Satellite",
        "name_ko": "위성",
        "services": [
            "ground_station",
        ],
    },
    # =========================================================================
    # Quantum Technologies
    # =========================================================================
    "quantum": {
        "name": "Quantum Technologies",
        "name_ko": "양자 기술",
        "services": [
            "braket",
        ],
    },
    # =========================================================================
    # End User Computing
    # =========================================================================
    "end_user_computing": {
        "name": "End User Computing",
        "name_ko": "최종 사용자 컴퓨팅",
        "services": [
            "workspaces",
            "workspaces_web",
            "appstream",
        ],
    },
    # =========================================================================
    # Business Applications
    # =========================================================================
    "business_apps": {
        "name": "Business Applications",
        "name_ko": "비즈니스 애플리케이션",
        "services": [
            "connect",
            "chime_sdk",
            "ses",
            "pinpoint",
            "end_user_messaging",
            "workmail",
        ],
    },
    # =========================================================================
    # Frontend Web & Mobile
    # =========================================================================
    "frontend_mobile": {
        "name": "Frontend Web & Mobile",
        "name_ko": "프론트엔드 웹 및 모바일",
        "services": [
            "amplify",
            "appsync",
            "device_farm",
            "location",
        ],
    },
    # =========================================================================
    # Customer Enablement
    # =========================================================================
    "customer_enablement": {
        "name": "Customer Enablement",
        "name_ko": "고객 지원",
        "services": [
            "managed_services",
            "repost",
        ],
    },
    # =========================================================================
    # Blockchain
    # =========================================================================
    "blockchain": {
        "name": "Blockchain",
        "name_ko": "블록체인",
        "services": [
            "managed_blockchain",
        ],
    },
}

# 서비스 → AWS 카테고리 역매핑 (첫 번째 매칭만 저장)
SERVICE_TO_CATEGORY: dict[str, str] = {}
for cat_key, cat_info in AWS_SERVICE_CATEGORIES.items():
    for service in cat_info["services"]:
        if service not in SERVICE_TO_CATEGORY:
            SERVICE_TO_CATEGORY[service] = cat_key

# AWS 글로벌 서비스 목록 (리전 선택이 불필요한 서비스)
# 참조: https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/global-services.html
GLOBAL_SERVICES: set[str] = {
    "iam",
    "organizations",
    "route53",
    "cloudfront",
    "waf",
    "acm",
    "global_accelerator",
    "shield",
    "sso",
    "sts",
}


def get_aws_categories() -> list[dict]:
    """AWS 서비스 카테고리 목록 반환 (도구가 있는 카테고리만)

    Returns:
        [
            {
                "key": "compute",
                "name": "Compute",
                "name_ko": "컴퓨팅",
                "services": ["ec2", "fn", ...]
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


def get_aws_category_view(include_empty: bool = True) -> list[dict]:
    """AWS 카테고리별로 플러그인을 그룹핑하여 반환

    discovery에서 발견된 플러그인을 AWS 공식 카테고리로 그룹핑합니다.

    Args:
        include_empty: True면 도구가 없는 카테고리도 포함 (기본값: True)

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

        # include_empty=True면 빈 카테고리도 포함, 아니면 도구가 있는 것만
        if include_empty or matched_plugins:
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
