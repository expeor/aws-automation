"""
plugins/dynamodb - DynamoDB 분석 도구

DynamoDB 테이블 관리, 미사용 리소스 탐지, 용량 모드 분석

CLI 사용법:
    aa dynamodb  → DynamoDB 도구
"""

CATEGORY = {
    "name": "dynamodb",
    "display_name": "DynamoDB",
    "description": "DynamoDB 테이블 관리 및 분석",
    "aliases": ["ddb"],
}

TOOLS = [
    {
        "name": "미사용 DynamoDB 테이블 분석",
        "description": "유휴/저사용 DynamoDB 테이블 탐지 (CloudWatch 지표 기반)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
    {
        "name": "DynamoDB 용량 모드 분석",
        "description": "Provisioned vs On-Demand 용량 모드 최적화 분석",
        "permission": "read",
        "module": "capacity_mode",
        "area": "cost",
    },
]
