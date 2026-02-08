"""
functions/analyzers/fsx - Amazon FSx 파일 시스템 분석 도구

FSx(Windows, Lustre, ONTAP, OpenZFS) 파일 시스템의 사용 현황을
분석하고 유휴/미사용 파일 시스템을 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 FSx 파일 시스템 탐지
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
