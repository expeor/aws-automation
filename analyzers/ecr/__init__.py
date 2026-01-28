"""
plugins/ecr - ECR Container Registry Tools
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
