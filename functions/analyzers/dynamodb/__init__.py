"""
functions/analyzers/dynamodb - DynamoDB 테이블 관리 및 분석 도구

DynamoDB 테이블의 사용량을 CloudWatch 지표 기반으로 분석하고,
유휴/저사용 테이블을 탐지합니다. Provisioned vs On-Demand 용량 모드
최적화 분석도 제공합니다.

도구 목록:
    - unused: 유휴/저사용 DynamoDB 테이블 탐지 (CloudWatch 지표 기반)
    - capacity_mode: Provisioned vs On-Demand 용량 모드 최적화 분석
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
        "name": "미사용 DynamoDB 테이블 탐지",
        "name_en": "Unused DynamoDB Table Detection",
        "description": "유휴/저사용 DynamoDB 테이블 탐지 (CloudWatch 지표 기반)",
        "description_en": "Detect idle/underutilized DynamoDB tables (CloudWatch metrics)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "DynamoDB 용량 비용 최적화",
        "name_en": "DynamoDB Capacity Cost Optimization",
        "description": "Provisioned vs On-Demand 용량 모드 최적화 분석",
        "description_en": "Provisioned vs On-Demand capacity mode optimization",
        "permission": "read",
        "module": "capacity_mode",
        "area": "cost",
    },
]
