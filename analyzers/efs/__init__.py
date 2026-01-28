"""
plugins/efs - EFS File System Management Tools
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
