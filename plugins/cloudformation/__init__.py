"""
plugins/cloudformation - CloudFormation 관리 도구

CloudFormation Stack 리소스 검색, 분석 등

## 사용 케이스
- 특정 리소스가 어떤 Stack에서 생성되었는지 확인
- 리소스 삭제 전 CloudFormation 의존성 확인
- 수동 생성 vs CFN 관리 리소스 구분
"""

from .resource_finder import (
    ResourceFinder,
    ResourceFinderReporter,
    SearchResult,
    StackResource,
    generate_report,
)

__all__ = [
    "ResourceFinder",
    "ResourceFinderReporter",
    "SearchResult",
    "StackResource",
    "generate_report",
]

CATEGORY = {
    "name": "cloudformation",
    "display_name": "CloudFormation",
    "description": "CloudFormation Stack 관리 및 분석",
    "aliases": ["cfn", "stack"],
}

TOOLS = [
    {
        "name": "CFN 리소스 검색",
        "description": "Physical ID 또는 Resource Type으로 CloudFormation Stack 리소스 검색",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search",
        "area": "management",
    },
    {
        "name": "CFN Physical ID 검색",
        "description": "Physical ID로 해당 리소스가 속한 CloudFormation Stack 찾기",
        "permission": "read",
        "module": "resource_finder",
        "function": "run_search_by_physical_id",
        "area": "management",
    },
]


# CLI 진입점 함수들
def run_search(
    session,
    physical_id: str = None,
    resource_type: str = None,
    regions: list = None,
    output_dir: str = "./reports",
    **kwargs,
):
    """CloudFormation 리소스 검색

    Args:
        session: boto3.Session
        physical_id: 검색할 Physical ID (부분 일치)
        resource_type: 검색할 Resource Type (부분 일치)
        regions: 검색할 리전 리스트
        output_dir: 리포트 출력 디렉토리
    """
    finder = ResourceFinder(
        session=session,
        regions=regions or ["ap-northeast-2"],
    )

    result = finder.search(
        physical_id=physical_id,
        resource_type=resource_type,
    )

    reporter = ResourceFinderReporter(result)
    reporter.print_summary()

    if result.count > 0:
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


def run_search_by_physical_id(
    session,
    physical_id: str,
    regions: list = None,
    output_dir: str = "./reports",
    **kwargs,
):
    """Physical ID로 Stack 검색

    Args:
        session: boto3.Session
        physical_id: 검색할 Physical ID
        regions: 검색할 리전 리스트
        output_dir: 리포트 출력 디렉토리
    """
    if not physical_id:
        return {"error": "physical_id is required"}

    return run_search(
        session=session,
        physical_id=physical_id,
        regions=regions,
        output_dir=output_dir,
    )
