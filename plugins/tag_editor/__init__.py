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


def run_sync(
    session,
    region: str = None,
    instance_ids: list = None,
    tag_keys: list = None,
    dry_run: bool = False,
    output_dir: str = "./reports",
    **kwargs,
):
    """EC2 태그를 EBS에 동기화

    Args:
        session: boto3.Session
        region: 리전
        instance_ids: 특정 인스턴스만 처리
        tag_keys: 특정 태그 키만 동기화
        dry_run: True면 시뮬레이션
        output_dir: 리포트 출력 디렉토리
    """
    syncer = EC2ToEBSTagSync(session, region, dry_run)
    summary = syncer.sync_all(instance_ids, tag_keys)

    reporter = TagSyncReporter(summary)
    reporter.print_summary()

    if summary.results:
        output_path = reporter.generate_report(
            output_dir=output_dir,
            file_prefix="ec2_to_ebs_tags",
        )
        return {
            "total_instances": summary.total_instances,
            "total_volumes": summary.total_volumes,
            "total_tags_applied": summary.total_tags_applied,
            "success": summary.success_count,
            "failed": summary.failed_count,
            "skipped": summary.skipped_count,
            "report_path": str(output_path),
        }

    return {
        "total_instances": summary.total_instances,
        "message": "No tags synced",
    }
