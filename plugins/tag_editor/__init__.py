"""
plugins/tag_editor - Resource Tag Management Tools
"""

CATEGORY = {
    "name": "tag_editor",
    "display_name": "Tag Editor",
    "description": "리소스 태그 관리 및 MAP 2.0 마이그레이션 태그",
    "description_en": "Resource Tag Management and MAP 2.0 Migration Tags",
    "aliases": ["tag", "map", "migration", "tagging"],
}

TOOLS = [
    {
        "name": "MAP 태그 분석",
        "name_en": "MAP Tag Analysis",
        "description": "MAP 2.0 마이그레이션 태그(map-migrated) 현황 분석",
        "description_en": "MAP 2.0 migration tag (map-migrated) status analysis",
        "permission": "read",
        "module": "map_audit",
        "area": "audit",
    },
    {
        "name": "MAP 태그 적용",
        "name_en": "MAP Tag Application",
        "description": "리소스에 MAP 2.0 마이그레이션 태그 일괄 적용",
        "description_en": "Bulk apply MAP 2.0 migration tags to resources",
        "permission": "write",
        "module": "map_apply",
        "area": "tag",
    },
    {
        "name": "EC2→EBS 태그 동기화",
        "name_en": "EC2→EBS Tag Sync",
        "description": "EC2 인스턴스의 태그를 연결된 EBS 볼륨에 일괄 적용",
        "description_en": "Sync EC2 instance tags to attached EBS volumes",
        "permission": "write",
        "module": "ec2_to_ebs",
        "function": "run_sync",
        "area": "sync",
    },
]
