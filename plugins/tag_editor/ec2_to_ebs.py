"""
plugins/tag_editor/ec2_to_ebs.py - EC2 태그를 EBS 볼륨에 동기화

EC2 인스턴스의 태그를 연결된 EBS 볼륨에 일괄 적용합니다.

사용 케이스:
- EC2 생성 시 EBS에 태그가 안 붙는 경우
- 비용 할당 태그를 EBS에 적용하여 Cost Explorer 추적
- EC2 ↔ EBS 태그 일관성 유지

사용법:
    from plugins.tag_editor.ec2_to_ebs import sync_tags

    result = sync_tags(session, region="ap-northeast-2")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.tools.io.excel import ColumnDef, Workbook

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeInstances",
    ],
    "write": [
        "ec2:CreateTags",
    ],
}


@dataclass
class TagSyncResult:
    """태그 동기화 결과"""

    instance_id: str
    instance_name: str
    volume_ids: List[str]
    tags_applied: List[Dict[str, str]]
    status: str  # success, failed, skipped
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "volume_ids": self.volume_ids,
            "tags_applied": self.tags_applied,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class SyncSummary:
    """동기화 요약"""

    total_instances: int = 0
    total_volumes: int = 0
    total_tags_applied: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: List[TagSyncResult] = field(default_factory=list)


class EC2ToEBSTagSync:
    """EC2 태그를 EBS 볼륨에 동기화

    EC2 인스턴스의 모든 태그(aws: 접두사 제외)를
    연결된 EBS 볼륨에 적용합니다.
    """

    # 동기화 제외 태그 접두사
    EXCLUDED_PREFIXES = ["aws:", "elasticbeanstalk:"]

    def __init__(
        self,
        session,
        region: str = None,
        dry_run: bool = False,
    ):
        """초기화

        Args:
            session: boto3.Session
            region: 리전
            dry_run: True면 실제 적용하지 않고 시뮬레이션
        """
        self.session = session
        self.region = region
        self.dry_run = dry_run
        self.ec2 = session.client("ec2", region_name=region)

    def sync_all(
        self,
        instance_ids: Optional[List[str]] = None,
        tag_keys: Optional[List[str]] = None,
    ) -> SyncSummary:
        """모든 EC2 인스턴스의 태그를 EBS에 동기화

        Args:
            instance_ids: 특정 인스턴스만 처리 (None이면 전체)
            tag_keys: 특정 태그 키만 동기화 (None이면 전체)

        Returns:
            SyncSummary
        """
        summary = SyncSummary()

        try:
            # EC2 인스턴스 조회
            instances = self._get_instances(instance_ids)
            summary.total_instances = len(instances)

            logger.info(f"{len(instances)}개 인스턴스 처리 시작")

            for instance in instances:
                result = self._sync_instance(instance, tag_keys)
                summary.results.append(result)

                if result.status == "success":
                    summary.success_count += 1
                    summary.total_volumes += len(result.volume_ids)
                    summary.total_tags_applied += len(result.tags_applied)
                elif result.status == "failed":
                    summary.failed_count += 1
                else:
                    summary.skipped_count += 1

        except Exception as e:
            logger.error(f"태그 동기화 실패: {e}")

        return summary

    def _get_instances(
        self, instance_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """EC2 인스턴스 목록 조회"""
        instances = []

        try:
            params = {}
            if instance_ids:
                params["InstanceIds"] = instance_ids

            paginator = self.ec2.get_paginator("describe_instances")
            for page in paginator.paginate(**params):
                for reservation in page.get("Reservations", []):
                    instances.extend(reservation.get("Instances", []))

        except Exception as e:
            logger.error(f"인스턴스 조회 실패: {e}")

        return instances

    def _sync_instance(
        self,
        instance: Dict[str, Any],
        tag_keys: Optional[List[str]] = None,
    ) -> TagSyncResult:
        """단일 인스턴스의 태그를 EBS에 동기화"""
        instance_id = instance["InstanceId"]
        instance_name = self._get_instance_name(instance)

        # 연결된 볼륨 ID 추출
        volume_ids = []
        for mapping in instance.get("BlockDeviceMappings", []):
            ebs = mapping.get("Ebs", {})
            if ebs.get("VolumeId"):
                volume_ids.append(ebs["VolumeId"])

        if not volume_ids:
            return TagSyncResult(
                instance_id=instance_id,
                instance_name=instance_name,
                volume_ids=[],
                tags_applied=[],
                status="skipped",
                error="연결된 EBS 볼륨 없음",
            )

        # 동기화할 태그 필터링
        tags_to_apply = self._filter_tags(instance.get("Tags", []), tag_keys)

        if not tags_to_apply:
            return TagSyncResult(
                instance_id=instance_id,
                instance_name=instance_name,
                volume_ids=volume_ids,
                tags_applied=[],
                status="skipped",
                error="동기화할 태그 없음",
            )

        # 태그 적용
        try:
            if not self.dry_run:
                self.ec2.create_tags(
                    Resources=volume_ids,
                    Tags=tags_to_apply,
                )

            logger.info(
                f"{instance_id}: {len(volume_ids)}개 볼륨에 "
                f"{len(tags_to_apply)}개 태그 적용"
            )

            return TagSyncResult(
                instance_id=instance_id,
                instance_name=instance_name,
                volume_ids=volume_ids,
                tags_applied=tags_to_apply,
                status="success",
            )

        except Exception as e:
            logger.error(f"{instance_id} 태그 적용 실패: {e}")
            return TagSyncResult(
                instance_id=instance_id,
                instance_name=instance_name,
                volume_ids=volume_ids,
                tags_applied=[],
                status="failed",
                error=str(e),
            )

    def _filter_tags(
        self,
        tags: List[Dict[str, str]],
        tag_keys: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """동기화할 태그 필터링"""
        filtered = []

        for tag in tags:
            key = tag.get("Key", "")

            # 제외 접두사 확인
            if any(key.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
                continue

            # 특정 키만 동기화하는 경우
            if tag_keys and key not in tag_keys:
                continue

            filtered.append(tag)

        return filtered

    def _get_instance_name(self, instance: Dict[str, Any]) -> str:
        """인스턴스 Name 태그 추출"""
        for tag in instance.get("Tags", []):
            if tag.get("Key") == "Name":
                return tag.get("Value", "")
        return ""


# 리포트 컬럼 정의
COLUMNS_SYNC_RESULTS = [
    ColumnDef(header="Instance ID", width=20, style="data"),
    ColumnDef(header="Instance Name", width=25, style="data"),
    ColumnDef(header="Volume IDs", width=40, style="data"),
    ColumnDef(header="Tags Applied", width=10, style="center"),
    ColumnDef(header="Status", width=10, style="center"),
    ColumnDef(header="Error", width=30, style="data"),
]


class TagSyncReporter:
    """태그 동기화 결과 리포터"""

    def __init__(self, summary: SyncSummary):
        self.summary = summary

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "ec2_to_ebs_tags",
    ) -> Path:
        """Excel 리포트 생성"""
        wb = Workbook()

        # 요약 시트
        self._create_summary_sheet(wb)

        # 상세 결과 시트
        self._create_results_sheet(wb)

        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"리포트 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """요약 시트"""
        summary_sheet = wb.new_summary_sheet("동기화 요약")

        summary_sheet.add_title("EC2 → EBS 태그 동기화 결과")

        summary_sheet.add_section("처리 현황")
        summary_sheet.add_item("처리된 인스턴스", f"{self.summary.total_instances}개")
        summary_sheet.add_item("태그 적용된 볼륨", f"{self.summary.total_volumes}개")
        summary_sheet.add_item("적용된 태그 수", f"{self.summary.total_tags_applied}개")

        summary_sheet.add_blank_row()

        summary_sheet.add_section("결과 상태")
        summary_sheet.add_item(
            "성공",
            f"{self.summary.success_count}건",
            highlight="success" if self.summary.success_count > 0 else None,
        )
        summary_sheet.add_item(
            "실패",
            f"{self.summary.failed_count}건",
            highlight="danger" if self.summary.failed_count > 0 else None,
        )
        summary_sheet.add_item("건너뜀", f"{self.summary.skipped_count}건")

        summary_sheet.add_blank_row()

        summary_sheet.add_section("리포트 정보")
        summary_sheet.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _create_results_sheet(self, wb: Workbook) -> None:
        """결과 상세 시트"""
        sheet = wb.new_sheet(name="상세 결과", columns=COLUMNS_SYNC_RESULTS)

        for result in self.summary.results:
            row = [
                result.instance_id,
                result.instance_name,
                ", ".join(result.volume_ids),
                len(result.tags_applied),
                result.status,
                result.error,
            ]
            sheet.add_row(row)

    def print_summary(self) -> None:
        """콘솔에 요약 출력"""
        print(f"\n=== EC2 → EBS 태그 동기화 결과 ===")
        print(f"처리된 인스턴스: {self.summary.total_instances}개")
        print(f"태그 적용된 볼륨: {self.summary.total_volumes}개")
        print(f"적용된 태그 수: {self.summary.total_tags_applied}개")
        print(f"성공: {self.summary.success_count}건")
        print(f"실패: {self.summary.failed_count}건")
        print(f"건너뜀: {self.summary.skipped_count}건")


def sync_tags(
    session,
    region: str = None,
    instance_ids: Optional[List[str]] = None,
    tag_keys: Optional[List[str]] = None,
    dry_run: bool = False,
) -> SyncSummary:
    """EC2 태그를 EBS에 동기화 (편의 함수)

    Args:
        session: boto3.Session
        region: 리전
        instance_ids: 특정 인스턴스만 처리
        tag_keys: 특정 태그 키만 동기화
        dry_run: True면 시뮬레이션

    Returns:
        SyncSummary
    """
    syncer = EC2ToEBSTagSync(session, region, dry_run)
    return syncer.sync_all(instance_ids, tag_keys)


def run_sync(ctx) -> None:
    """EC2 태그를 EBS에 동기화 (CLI 진입점)"""
    from core.auth.session import get_context_session
    from core.tools.output import OutputPath

    # 옵션에서 파라미터 추출
    instance_ids = ctx.options.get("instance_ids")
    tag_keys = ctx.options.get("tag_keys")
    dry_run = ctx.options.get("dry_run", False)

    # 첫 번째 리전에서 세션 획득
    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)

    syncer = EC2ToEBSTagSync(session, region, dry_run)
    summary = syncer.sync_all(instance_ids, tag_keys)

    reporter = TagSyncReporter(summary)
    reporter.print_summary()

    if summary.results:
        identifier = ctx.profile_name or "default"
        output_dir = OutputPath(identifier).sub("tag_editor").with_date().build()

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
