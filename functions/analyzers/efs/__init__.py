"""
functions/analyzers/efs - EFS 파일시스템 관리 도구

EFS 파일시스템의 사용 현황을 분석하고
유휴 또는 미사용 파일시스템을 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 EFS 파일시스템 탐지
"""

CATEGORY = {
    "name": "efs",
    "display_name": "EFS",
    "description": "EFS 파일시스템 관리",
    "description_en": "EFS File System Management",
    "aliases": ["filesystem", "nfs"],
}

TOOLS = [
    {
        "name": "미사용 EFS 파일시스템 탐지",
        "name_en": "Unused EFS File System Detection",
        "description": "유휴/미사용 EFS 파일시스템 탐지",
        "description_en": "Detect idle/unused EFS file systems",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
