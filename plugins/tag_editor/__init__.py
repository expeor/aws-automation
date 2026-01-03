"""
plugins/tag_editor - 리소스 태그 관리 도구

MAP 2.0 마이그레이션 태그 분석 및 적용
"""

CATEGORY = {
    "name": "tag_editor",
    "display_name": "Tag Editor",
    "description": "리소스 태그 관리 및 MAP 2.0 마이그레이션 태그",
    "aliases": ["tag", "map", "migration", "tagging"],
}

TOOLS = [
    {
        "name": "MAP 태그 분석",
        "description": "MAP 2.0 마이그레이션 태그(map-migrated) 현황 분석",
        "permission": "read",
        "module": "map_audit",
        "area": "cost",
    },
    {
        "name": "MAP 태그 적용",
        "description": "리소스에 MAP 2.0 마이그레이션 태그 일괄 적용",
        "permission": "write",
        "module": "map_apply",
        "area": "cost",
    },
]
