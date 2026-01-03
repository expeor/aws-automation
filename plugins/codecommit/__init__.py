"""
plugins/codecommit - CodeCommit 리포지토리 관리 도구

CodeCommit 리포지토리 및 브랜치 현황 분석
빈 리포지토리 탐지
"""

from .unused import (
    AuditResult,
    CodeCommitAnalysisResult,
    RepoAuditor,
    RepoAuditReporter,
    Repository,
    analyze_repos,
    collect_repos,
    generate_report,
)

__all__ = [
    "RepoAuditor",
    "RepoAuditReporter",
    "AuditResult",
    "Repository",
    "generate_report",
    # unused_all 연동
    "collect_repos",
    "analyze_repos",
    "CodeCommitAnalysisResult",
]

CATEGORY = {
    "name": "codecommit",
    "display_name": "CodeCommit",
    "description": "CodeCommit 리포지토리 관리 및 분석",
    "aliases": ["cc", "repo"],
}

TOOLS = [
    {
        "name": "리포지토리 분석",
        "description": "CodeCommit 리포지토리 및 브랜치 현황 분석",
        "permission": "read",
        "module": "unused",
        "function": "run_audit",
        "area": "management",
    },
    {
        "name": "빈 리포지토리 조회",
        "description": "브랜치가 없는 빈 리포지토리 목록 조회",
        "permission": "read",
        "module": "unused",
        "function": "run_empty_repos",
        "area": "cost",
    },
]


# CLI 진입점 함수들
def run_audit(
    session,
    region: str = None,
    output_dir: str = "./reports",
    **kwargs,
):
    """CodeCommit 리포지토리 분석"""
    auditor = RepoAuditor(session=session, region=region)
    result = auditor.audit()

    reporter = RepoAuditReporter(result)
    reporter.print_summary()

    if result.total_repos > 0:
        output_path = reporter.generate_report(
            output_dir=output_dir,
            file_prefix="codecommit_repos",
        )
        return {
            "total_repos": result.total_repos,
            "total_branches": result.total_branches,
            "empty_repos": len(result.empty_repos),
            "report_path": str(output_path),
        }

    return {
        "total_repos": 0,
        "message": "No CodeCommit repositories found",
    }


def run_empty_repos(
    session,
    region: str = None,
    **kwargs,
):
    """빈 리포지토리 조회"""
    auditor = RepoAuditor(session=session, region=region)
    result = auditor.audit()

    empty = result.empty_repos

    if not empty:
        print("빈 리포지토리가 없습니다.")
        return {"empty_repos": []}

    print(f"\n빈 리포지토리 {len(empty)}개:")
    for repo in empty:
        created = repo.creation_date.strftime("%Y-%m-%d") if repo.creation_date else "N/A"
        print(f"  {repo.name} (생성: {created})")

    return {
        "empty_repos": [r.name for r in empty],
        "count": len(empty),
    }
