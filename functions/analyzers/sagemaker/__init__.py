"""
functions/analyzers/sagemaker - SageMaker ML 리소스 관리 도구

SageMaker Endpoint의 사용 현황을 CloudWatch 지표 기반으로 분석하고
유휴/미사용 엔드포인트를 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 SageMaker Endpoint 탐지 (CloudWatch 기반)
"""

CATEGORY = {
    "name": "sagemaker",
    "display_name": "SageMaker",
    "description": "SageMaker ML 리소스 관리",
    "description_en": "SageMaker ML Resource Management",
    "aliases": ["ml", "sage"],
}

TOOLS = [
    {
        "name": "미사용 SageMaker Endpoint 탐지",
        "name_en": "Unused SageMaker Endpoint Detection",
        "description": "유휴/미사용 SageMaker Endpoint 탐지 (CloudWatch 기반)",
        "description_en": "Detect idle/unused SageMaker Endpoints (CloudWatch metrics)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
