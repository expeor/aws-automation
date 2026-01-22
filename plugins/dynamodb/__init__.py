"""
plugins/dynamodb - DynamoDB Table Management Tools
"""

CATEGORY = {
    "name": "dynamodb",
    "display_name": "DynamoDB",
    "description": "DynamoDB 테이블 관리 및 분석",
    "description_en": "DynamoDB Table Management and Analysis",
    "aliases": ["ddb"],
}

TOOLS = [
    {
        "name": "미사용 DynamoDB 테이블 분석",
        "name_en": "Unused DynamoDB Table Analysis",
        "description": "유휴/저사용 DynamoDB 테이블 탐지 (CloudWatch 지표 기반)",
        "description_en": "Detect idle/underutilized DynamoDB tables (CloudWatch metrics)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "DynamoDB 용량 모드 분석",
        "name_en": "DynamoDB Capacity Mode Analysis",
        "description": "Provisioned vs On-Demand 용량 모드 최적화 분석",
        "description_en": "Provisioned vs On-Demand capacity mode optimization",
        "permission": "read",
        "module": "capacity_mode",
        "area": "cost",
    },
]
