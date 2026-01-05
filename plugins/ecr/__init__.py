"""
plugins/ecr - ECR 분석 도구

ECR 리포지토리 및 이미지 관리
"""

CATEGORY = {
    "name": "ecr",
    "display_name": "ECR",
    "description": "ECR 컨테이너 레지스트리 관리",
    "aliases": ["container", "docker"],
}

TOOLS = [
    {
        "name": "미사용 이미지 분석",
        "description": "오래된/미사용 ECR 이미지 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
