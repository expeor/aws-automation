"""
core/tools/aws_categories.py - AWS 서비스 카테고리 매핑

AWS 공식 문서 기반 서비스 그룹 분류
참조: https://docs.aws.amazon.com/whitepapers/latest/aws-overview/
"""

from typing import Dict, List

# AWS 서비스 카테고리 정의 (AWS 공식 분류 기준)
# services 리스트는 각 서비스 폴더의 CATEGORY["name"] 값과 매칭
# 폴더 구조: plugins/{service}/ (예: plugins/rds/, plugins/ec2/)
AWS_SERVICE_CATEGORIES: Dict[str, Dict] = {
    # =========================================================================
    # Compute
    # =========================================================================
    "compute": {
        "name": "Compute",
        "name_ko": "컴퓨팅",
        "icon": "🖥️",
        "services": [
            "ec2",  # Amazon EC2
            "lambda",  # AWS Lambda
            "elasticbeanstalk",  # AWS Elastic Beanstalk
            # lightsail, batch, outposts, wavelength 등은 미구현
        ],
    },
    # =========================================================================
    # Containers
    # =========================================================================
    "containers": {
        "name": "Containers",
        "name_ko": "컨테이너",
        "icon": "📦",
        "services": [
            "ecr",  # Amazon ECR
            "ecs",  # Amazon ECS
            "eks",  # Amazon EKS
            # fargate, app_runner 등은 미구현
        ],
    },
    # =========================================================================
    # Storage
    # =========================================================================
    "storage": {
        "name": "Storage",
        "name_ko": "스토리지",
        "icon": "💾",
        "services": [
            "s3",  # Amazon S3
            "ebs",  # Amazon EBS
            "efs",  # Amazon EFS
            "fsx",  # Amazon FSx
            "aws_backup",  # AWS Backup
            # glacier, storage_gateway 등은 미구현
        ],
    },
    # =========================================================================
    # Database
    # =========================================================================
    "database": {
        "name": "Database",
        "name_ko": "데이터베이스",
        "icon": "🗄️",
        "services": [
            "rds",  # Amazon RDS
            "dynamodb",  # Amazon DynamoDB
            "docdb",  # Amazon DocumentDB
            "elasticache",  # Amazon ElastiCache
            "opensearch",  # Amazon OpenSearch Service
            # aurora, neptune, redshift, keyspaces, timestream, qldb, memorydb 등
        ],
    },
    # =========================================================================
    # Networking & Content Delivery
    # =========================================================================
    "networking": {
        "name": "Networking & Content Delivery",
        "name_ko": "네트워킹 및 콘텐츠 전송",
        "icon": "🌐",
        "services": [
            "vpc",  # Amazon VPC
            "elb",  # Elastic Load Balancing
            "route53",  # Amazon Route 53
            "apigateway",  # Amazon API Gateway
            "securitygroup",  # Security Groups (VPC 관련)
            "ip",  # IP 관리 도구
            # cloudfront, direct_connect, global_accelerator, transit_gateway 등
        ],
    },
    # =========================================================================
    # Security, Identity & Compliance
    # =========================================================================
    "security": {
        "name": "Security, Identity & Compliance",
        "name_ko": "보안, 자격 증명 및 규정 준수",
        "icon": "🔒",
        "services": [
            "iam",  # AWS IAM
            "kms",  # AWS KMS
            "waf",  # AWS WAF
            "guardduty",  # Amazon GuardDuty
            "secretsmanager",  # AWS Secrets Manager
            "acm",  # AWS Certificate Manager
            "cognito",  # Amazon Cognito
            # shield, inspector, macie, detective, security_hub, sso 등
        ],
    },
    # =========================================================================
    # Management & Governance
    # =========================================================================
    "management": {
        "name": "Management & Governance",
        "name_ko": "관리 및 거버넌스",
        "icon": "⚙️",
        "services": [
            "cloudwatch",  # Amazon CloudWatch
            "cloudtrail",  # AWS CloudTrail
            "config",  # AWS Config
            "ssm",  # AWS Systems Manager
            "servicecatalog",  # AWS Service Catalog
            "tag",  # 태그 관리
            "ce",  # AWS Cost Explorer
            # organizations, control_tower, trusted_advisor, license_manager 등
        ],
    },
    # =========================================================================
    # Analytics
    # =========================================================================
    "analytics": {
        "name": "Analytics",
        "name_ko": "분석",
        "icon": "📊",
        "services": [
            "kinesis",  # Amazon Kinesis
            "glue",  # AWS Glue
            "log",  # 로그 분석 도구
            # athena, redshift, emr, quicksight, data_pipeline, msk, lake_formation 등
        ],
    },
    # =========================================================================
    # Application Integration
    # =========================================================================
    "application_integration": {
        "name": "Application Integration",
        "name_ko": "애플리케이션 통합",
        "icon": "🔗",
        "services": [
            "sns",  # Amazon SNS
            "sqs",  # Amazon SQS
            "eventbridge",  # Amazon EventBridge
            "stepfunctions",  # AWS Step Functions
            # appsync, mq 등
        ],
    },
    # =========================================================================
    # Developer Tools
    # =========================================================================
    "developer_tools": {
        "name": "Developer Tools",
        "name_ko": "개발자 도구",
        "icon": "🛠️",
        "services": [
            "codecommit",  # AWS CodeCommit
            "cfn",  # AWS CloudFormation
            # codebuild, codedeploy, codepipeline, codestar, cloud9, x_ray 등
        ],
    },
    # =========================================================================
    # Machine Learning
    # =========================================================================
    "machine_learning": {
        "name": "Machine Learning",
        "name_ko": "기계 학습",
        "icon": "🤖",
        "services": [
            "bedrock",  # Amazon Bedrock
            # sagemaker, rekognition, comprehend, polly, transcribe, translate,
            # lex, personalize, forecast, textract, kendra 등
        ],
    },
    # =========================================================================
    # 기타 카테고리 (AWS 공식 분류에 맞춤)
    # =========================================================================
    # Cloud Financial Management
    "cost_management": {
        "name": "Cloud Financial Management",
        "name_ko": "클라우드 비용 관리",
        "icon": "💰",
        "services": [
            "ce",  # AWS Cost Explorer (management에도 포함)
            # budgets, cost_anomaly_detection 등
        ],
    },
    # Migration & Transfer (마이그레이션)
    "migration": {
        "name": "Migration & Transfer",
        "name_ko": "마이그레이션 및 전송",
        "icon": "🚚",
        "services": [
            # dms, sct, migration_hub, datasync, transfer_family, snow_family 등
        ],
    },
    # Media Services
    "media": {
        "name": "Media Services",
        "name_ko": "미디어 서비스",
        "icon": "🎬",
        "services": [
            # mediaconvert, mediaconnect, medialive, mediapackage, ivs 등
        ],
    },
    # IoT
    "iot": {
        "name": "Internet of Things",
        "name_ko": "사물 인터넷",
        "icon": "📡",
        "services": [
            # iot_core, iot_greengrass, iot_analytics, iot_events 등
        ],
    },
    # Game Tech
    "game_tech": {
        "name": "Game Tech",
        "name_ko": "게임 기술",
        "icon": "🎮",
        "services": [
            # gamelift, gamesparks 등
        ],
    },
    # Satellite
    "satellite": {
        "name": "Satellite",
        "name_ko": "위성",
        "icon": "🛰️",
        "services": [
            # ground_station 등
        ],
    },
    # Quantum Technologies
    "quantum": {
        "name": "Quantum Technologies",
        "name_ko": "양자 기술",
        "icon": "⚛️",
        "services": [
            # braket 등
        ],
    },
    # End User Computing
    "end_user_computing": {
        "name": "End User Computing",
        "name_ko": "최종 사용자 컴퓨팅",
        "icon": "🖥️",
        "services": [
            # workspaces, appstream 등
        ],
    },
    # Business Applications
    "business_apps": {
        "name": "Business Applications",
        "name_ko": "비즈니스 애플리케이션",
        "icon": "💼",
        "services": [
            # connect, chime, ses, pinpoint, workmail 등
        ],
    },
    # Frontend Web & Mobile
    "frontend_mobile": {
        "name": "Frontend Web & Mobile",
        "name_ko": "프론트엔드 웹 및 모바일",
        "icon": "📱",
        "services": [
            "cognito",  # Amazon Cognito (security에도 포함)
            # amplify, location_service, device_farm 등
        ],
    },
    # Customer Enablement
    "customer_enablement": {
        "name": "Customer Enablement",
        "name_ko": "고객 지원",
        "icon": "🤝",
        "services": [
            # iq, managed_services, support, training 등
        ],
    },
    # Blockchain
    "blockchain": {
        "name": "Blockchain",
        "name_ko": "블록체인",
        "icon": "🔗",
        "services": [
            # managed_blockchain, qldb 등
        ],
    },
}

# 서비스 → AWS 카테고리 역매핑 (첫 번째 매칭만 저장)
SERVICE_TO_CATEGORY: Dict[str, str] = {}
for cat_key, cat_info in AWS_SERVICE_CATEGORIES.items():
    for service in cat_info["services"]:
        if service not in SERVICE_TO_CATEGORY:
            SERVICE_TO_CATEGORY[service] = cat_key


def get_aws_categories() -> List[Dict]:
    """AWS 서비스 카테고리 목록 반환 (도구가 있는 카테고리만)

    Returns:
        [
            {
                "key": "compute",
                "name": "Compute",
                "name_ko": "컴퓨팅",
                "icon": "🖥️",
                "services": ["ec2", "lambda", ...]
            },
            ...
        ]
    """
    result = []
    for key, info in AWS_SERVICE_CATEGORIES.items():
        # 서비스가 있는 카테고리만 반환
        if info["services"]:
            result.append({"key": key, **info})
    return result


def get_services_by_aws_category(category_key: str) -> List[str]:
    """특정 AWS 카테고리에 속한 서비스 목록 반환

    Args:
        category_key: AWS 카테고리 키 (예: "compute", "storage")

    Returns:
        서비스 이름 목록
    """
    if category_key in AWS_SERVICE_CATEGORIES:
        return AWS_SERVICE_CATEGORIES[category_key]["services"]
    return []


def get_aws_category_for_service(service_name: str) -> str:
    """서비스가 속한 AWS 카테고리 반환

    Args:
        service_name: 서비스 이름 (예: "ec2", "s3")

    Returns:
        AWS 카테고리 키 또는 "other"
    """
    return SERVICE_TO_CATEGORY.get(service_name, "other")
