"""
plugins/tag_editor - 리소스 태그 관리 도구

MAP 2.0 마이그레이션 태그 분석 및 적용
EC2 인스턴스 태그를 EBS 볼륨에 동기화
"""

from .ec2_to_ebs import (
    EC2ToEBSTagSync,
    SyncSummary,
    TagSyncReporter,
    TagSyncResult,
    sync_tags,
)

__all__ = [
    "EC2ToEBSTagSync",
    "SyncSummary",
    "TagSyncReporter",
    "TagSyncResult",
    "sync_tags",
]

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
    {
        "name": "EC2→EBS 태그 동기화",
        "description": "EC2 인스턴스의 태그를 연결된 EBS 볼륨에 일괄 적용",
        "permission": "write",
        "module": "ec2_to_ebs",
        "function": "run_sync",
        "area": "management",
    },
]
