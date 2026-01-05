"""
plugins/efs - EFS 분석 도구

EFS 파일시스템 관리 및 미사용 리소스 탐지
"""

CATEGORY = {
    "name": "efs",
    "display_name": "EFS",
    "description": "EFS 파일시스템 관리",
    "aliases": ["filesystem", "nfs"],
}

TOOLS = [
    {
        "name": "미사용 EFS 파일시스템 분석",
        "description": "유휴/미사용 EFS 파일시스템 탐지",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
