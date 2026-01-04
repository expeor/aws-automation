"""
plugins/cloudformation/resource_finder.py - CloudFormation Stack 리소스 검색기

모든 CloudFormation Stack에서 Physical ID 또는 Resource Type으로 리소스를 검색합니다.

사용 케이스:
- 특정 리소스가 어떤 Stack에서 생성되었는지 확인
- 리소스 삭제 전 CloudFormation 의존성 확인
- 수동 생성 vs CFN 관리 리소스 구분

사용법:
    from plugins.cloudformation.resource_finder import ResourceFinder

    finder = ResourceFinder(session)
    results = finder.search(physical_id="i-1234567890abcdef0")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.tools.io.excel import ColumnDef, Workbook

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "cloudformation:DescribeStacks",
        "cloudformation:ListStackResources",
    ],
}


@dataclass
class StackResource:
    """CloudFormation Stack 리소스 정보"""

    stack_name: str
    stack_status: str
    logical_id: str
    physical_id: str
    resource_type: str
    resource_status: str
    region: str
    account_id: str = ""
    account_name: str = ""
    stack_creation_time: datetime | None = None
    last_updated_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "region": self.region,
            "stack_name": self.stack_name,
            "stack_status": self.stack_status,
            "logical_id": self.logical_id,
            "physical_id": self.physical_id,
            "resource_type": self.resource_type,
            "resource_status": self.resource_status,
            "stack_creation_time": self.stack_creation_time,
            "last_updated_time": self.last_updated_time,
        }


@dataclass
class SearchResult:
    """검색 결과"""

    resources: list[StackResource] = field(default_factory=list)
    total_stacks_searched: int = 0
    regions_searched: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.resources)

    def get_by_stack(self) -> dict[str, list[StackResource]]:
        """Stack별로 그룹화"""
        grouped: dict[str, list[StackResource]] = {}
        for res in self.resources:
            key = f"{res.account_name}/{res.region}/{res.stack_name}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(res)
        return grouped

    def get_by_resource_type(self) -> dict[str, list[StackResource]]:
        """Resource Type별로 그룹화"""
        grouped: dict[str, list[StackResource]] = {}
        for res in self.resources:
            if res.resource_type not in grouped:
                grouped[res.resource_type] = []
            grouped[res.resource_type].append(res)
        return grouped


class ResourceFinder:
    """CloudFormation Stack 리소스 검색기

    모든 Stack에서 Physical ID 또는 Resource Type으로 리소스를 검색합니다.
    """

    def __init__(
        self,
        session,
        regions: list[str] | None = None,
        max_workers: int = 5,
    ):
        """초기화

        Args:
            session: boto3.Session 객체
            regions: 검색할 리전 리스트 (기본: ap-northeast-2)
            max_workers: 병렬 처리 워커 수
        """
        self.session = session
        self.regions = regions or ["ap-northeast-2"]
        self.max_workers = max_workers

    def search(
        self,
        physical_id: str | None = None,
        resource_type: str | None = None,
        stack_name_filter: str | None = None,
    ) -> SearchResult:
        """리소스 검색

        Args:
            physical_id: 검색할 Physical ID (부분 일치)
            resource_type: 검색할 Resource Type (부분 일치)
            stack_name_filter: Stack 이름 필터 (부분 일치)

        Returns:
            SearchResult 객체
        """
        all_resources = []
        total_stacks = 0

        for region in self.regions:
            resources, stack_count = self._search_in_region(
                region=region,
                physical_id=physical_id,
                resource_type=resource_type,
                stack_name_filter=stack_name_filter,
            )
            all_resources.extend(resources)
            total_stacks += stack_count

        logger.info(f"검색 완료: {len(all_resources)}개 리소스 발견 ({total_stacks}개 Stack 검색)")

        return SearchResult(
            resources=all_resources,
            total_stacks_searched=total_stacks,
            regions_searched=self.regions,
        )

    def _search_in_region(
        self,
        region: str,
        physical_id: str | None = None,
        resource_type: str | None = None,
        stack_name_filter: str | None = None,
    ) -> tuple[list[StackResource], int]:
        """특정 리전에서 검색"""
        matched_resources = []
        stack_count = 0

        try:
            cfn = self.session.client("cloudformation", region_name=region)

            # 모든 Stack 조회
            stacks = self._get_all_stacks(cfn, stack_name_filter)
            stack_count = len(stacks)

            logger.debug(f"{region}: {stack_count}개 Stack 발견")

            # 각 Stack의 리소스 검색
            for stack in stacks:
                resources = self._get_stack_resources(cfn, stack, region)

                for res in resources:
                    # Physical ID 필터링
                    if physical_id and physical_id.lower() not in res.physical_id.lower():
                        continue

                    # Resource Type 필터링
                    if resource_type and resource_type.lower() not in res.resource_type.lower():
                        continue

                    matched_resources.append(res)

        except Exception as e:
            logger.error(f"{region} 검색 실패: {e}")

        return matched_resources, stack_count

    def _get_all_stacks(
        self,
        cfn,
        name_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """모든 Stack 조회"""
        stacks = []

        try:
            paginator = cfn.get_paginator("describe_stacks")
            for page in paginator.paginate():
                for stack in page["Stacks"]:
                    # DELETE_COMPLETE 제외
                    if stack["StackStatus"] == "DELETE_COMPLETE":
                        continue

                    # 이름 필터
                    if name_filter and name_filter.lower() not in stack["StackName"].lower():
                        continue

                    stacks.append(stack)

        except Exception as e:
            logger.error(f"Stack 조회 실패: {e}")

        return stacks

    def _get_stack_resources(
        self,
        cfn,
        stack: dict[str, Any],
        region: str,
    ) -> list[StackResource]:
        """Stack의 모든 리소스 조회"""
        resources = []
        stack_name = stack["StackName"]

        try:
            paginator = cfn.get_paginator("list_stack_resources")
            for page in paginator.paginate(StackName=stack_name):
                for res in page["StackResourceSummaries"]:
                    resources.append(
                        StackResource(
                            stack_name=stack_name,
                            stack_status=stack["StackStatus"],
                            logical_id=res["LogicalResourceId"],
                            physical_id=res.get("PhysicalResourceId", "N/A"),
                            resource_type=res["ResourceType"],
                            resource_status=res["ResourceStatus"],
                            region=region,
                            stack_creation_time=stack.get("CreationTime"),
                            last_updated_time=res.get("LastUpdatedTimestamp"),
                        )
                    )

        except Exception as e:
            logger.warning(f"Stack {stack_name} 리소스 조회 실패: {e}")

        return resources

    def search_by_physical_id(self, physical_id: str) -> SearchResult:
        """Physical ID로 검색 (편의 메서드)"""
        return self.search(physical_id=physical_id)

    def search_by_resource_type(self, resource_type: str) -> SearchResult:
        """Resource Type으로 검색 (편의 메서드)"""
        return self.search(resource_type=resource_type)


# 리포트 컬럼 정의
COLUMNS_RESOURCES = [
    ColumnDef(header="Region", width=15, style="center"),
    ColumnDef(header="Stack Name", width=30, style="data"),
    ColumnDef(header="Stack Status", width=18, style="center"),
    ColumnDef(header="Logical ID", width=30, style="data"),
    ColumnDef(header="Physical ID", width=40, style="data"),
    ColumnDef(header="Resource Type", width=30, style="data"),
    ColumnDef(header="Resource Status", width=18, style="center"),
]


class ResourceFinderReporter:
    """리소스 검색 결과 리포터"""

    def __init__(self, result: SearchResult):
        self.result = result

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "cfn_resource_search",
    ) -> Path:
        """Excel 리포트 생성"""
        wb = Workbook()

        # 요약 시트
        self._create_summary_sheet(wb)

        # 전체 리소스 시트
        self._create_resources_sheet(wb)

        # Resource Type별 시트
        self._create_by_type_sheets(wb)

        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"리포트 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """요약 시트"""
        summary = wb.new_summary_sheet("검색 결과 요약")

        summary.add_title("CloudFormation 리소스 검색 결과")

        summary.add_section("검색 현황")
        summary.add_item("검색된 리소스", f"{self.result.count}개")
        summary.add_item("검색된 Stack", f"{self.result.total_stacks_searched}개")
        summary.add_item("검색 리전", ", ".join(self.result.regions_searched))

        summary.add_blank_row()

        # Resource Type별 현황
        summary.add_section("Resource Type별 현황")
        by_type = self.result.get_by_resource_type()
        sorted_types = sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True)

        for res_type, resources in sorted_types[:10]:
            summary.add_item(res_type, f"{len(resources)}개")

        summary.add_blank_row()

        summary.add_section("리포트 정보")
        summary.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _create_resources_sheet(self, wb: Workbook) -> None:
        """전체 리소스 시트"""
        sheet = wb.new_sheet(name="All Resources", columns=COLUMNS_RESOURCES)

        for res in self.result.resources:
            row = [
                res.region,
                res.stack_name,
                res.stack_status,
                res.logical_id,
                res.physical_id,
                res.resource_type,
                res.resource_status,
            ]
            sheet.add_row(row)

        sheet.add_summary_row(
            [
                "합계",
                f"{self.result.count}개",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    def _create_by_type_sheets(self, wb: Workbook) -> None:
        """Resource Type별 시트 (상위 5개만)"""
        by_type = self.result.get_by_resource_type()
        sorted_types = sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True)

        for res_type, resources in sorted_types[:5]:
            # 시트 이름은 31자 제한
            sheet_name = res_type.replace("AWS::", "")[:31]
            sheet = wb.new_sheet(name=sheet_name, columns=COLUMNS_RESOURCES)

            for res in resources:
                row = [
                    res.region,
                    res.stack_name,
                    res.stack_status,
                    res.logical_id,
                    res.physical_id,
                    res.resource_type,
                    res.resource_status,
                ]
                sheet.add_row(row)

    def print_summary(self) -> None:
        """콘솔에 요약 출력"""
        print("\n=== CloudFormation 리소스 검색 결과 ===")
        print(f"검색된 리소스: {self.result.count}개")
        print(f"검색된 Stack: {self.result.total_stacks_searched}개")
        print(f"검색 리전: {', '.join(self.result.regions_searched)}")

        if self.result.resources:
            print("\n발견된 리소스:")
            for res in self.result.resources[:10]:
                print(f"  [{res.resource_type}] {res.physical_id}")
                print(f"    Stack: {res.stack_name} ({res.region})")

            if self.result.count > 10:
                print(f"  ... 외 {self.result.count - 10}개")


def generate_report(
    result: SearchResult,
    output_dir: str,
    file_prefix: str = "cfn_resource_search",
) -> Path:
    """리포트 생성 (편의 함수)"""
    reporter = ResourceFinderReporter(result)
    return reporter.generate_report(output_dir, file_prefix)


# =============================================================================
# CLI 진입점 함수
# =============================================================================


def run_search(ctx) -> dict[str, Any] | None:
    """CloudFormation 리소스 검색"""
    from core.auth.session import get_context_session
    from core.tools.output import OutputPath

    # 첫 번째 리전에서 세션 획득
    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)

    # 옵션에서 검색어 가져오기
    physical_id = ctx.options.get("physical_id")
    resource_type = ctx.options.get("resource_type")

    finder = ResourceFinder(
        session=session,
        regions=ctx.regions or [region],
    )

    result = finder.search(
        physical_id=physical_id,
        resource_type=resource_type,
    )

    reporter = ResourceFinderReporter(result)
    reporter.print_summary()

    if result.count > 0:
        identifier = ctx.profile_name or "default"
        output_dir = OutputPath(identifier).sub("cloudformation").with_date().build()

        output_path = reporter.generate_report(
            output_dir=output_dir,
            file_prefix="cfn_resource_search",
        )
        return {
            "count": result.count,
            "stacks_searched": result.total_stacks_searched,
            "report_path": str(output_path),
        }

    return {
        "count": 0,
        "stacks_searched": result.total_stacks_searched,
        "message": "No matching resources found",
    }


def run_search_by_physical_id(ctx) -> dict[str, Any] | None:
    """Physical ID로 Stack 검색"""
    physical_id = ctx.options.get("physical_id")
    if not physical_id:
        print("physical_id가 필요합니다.")
        return {"error": "physical_id is required"}

    return run_search(ctx)
