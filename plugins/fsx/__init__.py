"""
plugins/fsx/__init__.py - Amazon FSx 플러그인

FSx 파일 시스템 관리 및 분석
"""

CATEGORY = {
    "name": "fsx",
    "display_name": "FSx",
    "description": "Amazon FSx 파일 시스템 분석",
    "description_en": "Amazon FSx file system analysis",
    "aliases": ["fsx-windows", "fsx-lustre", "fsx-ontap", "fsx-openzfs"],
}

TOOLS = [
    {
        "name": "미사용 파일시스템",
        "name_en": "Unused File Systems",
        "description": "유휴/미사용 FSx 파일 시스템 탐지",
        "description_en": "Detect idle/unused FSx file systems",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
