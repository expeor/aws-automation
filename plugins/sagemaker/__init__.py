"""
plugins/sagemaker - SageMaker 관련 분석 도구

SageMaker Endpoint, Notebook 등 ML 리소스 분석
"""

CATEGORY = {
    "name": "sagemaker",
    "display_name": "SageMaker",
    "description": "SageMaker ML 리소스 관리",
    "aliases": ["ml", "sage"],
}

TOOLS = [
    {
        "name": "SageMaker Endpoint 미사용 분석",
        "description": "유휴/미사용 SageMaker Endpoint 탐지 (CloudWatch 기반)",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
