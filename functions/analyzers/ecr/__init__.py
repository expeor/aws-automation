"""
functions/analyzers/ecr - ECR 컨테이너 레지스트리 관리 도구

ECR 리포지토리의 이미지 사용 현황을 분석하고
오래된/미사용 컨테이너 이미지를 탐지합니다.

도구 목록:
    - unused: 오래된/미사용 ECR 이미지 탐지
"""

CATEGORY = {
    "name": "ecr",
    "display_name": "ECR",
    "description": "ECR 컨테이너 레지스트리 관리",
    "description_en": "ECR Container Registry Management",
    "aliases": ["container", "docker"],
}

TOOLS = [
    {
        "name": "미사용 ECR 이미지 탐지",
        "name_en": "Unused ECR Image Detection",
        "description": "오래된/미사용 ECR 이미지 탐지",
        "description_en": "Detect old/unused ECR images",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
