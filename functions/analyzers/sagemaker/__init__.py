"""
plugins/sagemaker - SageMaker ML Resource Management Tools
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
