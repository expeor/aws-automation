"""
functions/analyzers/codecommit/unused.py - CodeCommit 미사용 리포지토리 분석

빈 리포지토리(브랜치 없음) 탐지

사용법:
    from functions.analyzers.codecommit.unused import collect_repos, analyze_repos

    repos = collect_repos(session, account_id, account_name, region)
    result = analyze_repos(repos, account_id, account_name, region)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.shared.io.excel import ColumnDef, Workbook

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "codecommit:ListRepositories",
        "codecommit:GetRepository",
        "codecommit:ListBranches",
    ],
}


@dataclass
class Repository:
    """CodeCommit 리포지토리 정보.

    리포지토리 메타데이터와 브랜치 목록을 보관한다.

    Attributes:
        name: 리포지토리 이름.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 리전.
        description: 리포지토리 설명.
        clone_url_http: HTTPS 클론 URL.
        clone_url_ssh: SSH 클론 URL.
        arn: 리포지토리 ARN.
        creation_date: 생성 일시.
        last_modified_date: 마지막 수정 일시.
        default_branch: 기본 브랜치 이름.
        branches: 브랜치 이름 목록.
    """

    name: str
    account_id: str = ""
    account_name: str = ""
    region: str = ""
    description: str = ""
    clone_url_http: str = ""
    clone_url_ssh: str = ""
    arn: str = ""
    creation_date: datetime | None = None
    last_modified_date: datetime | None = None
    default_branch: str = ""
    branches: list[str] = field(default_factory=list)

    @property
    def branch_count(self) -> int:
        """브랜치 수.

        Returns:
            리포지토리의 브랜치 개수.
        """
        return len(self.branches)

    @property
    def is_empty(self) -> bool:
        """브랜치가 없는 빈 리포지토리인지 판단한다.

        Returns:
            브랜치가 하나도 없으면 True.
        """
        return self.branch_count == 0

    def to_dict(self) -> dict[str, Any]:
        """인스턴스를 딕셔너리로 변환한다.

        Returns:
            모든 필드를 포함하는 딕셔너리.
        """
        return {
            "name": self.name,
            "description": self.description,
            "arn": self.arn,
            "account_id": self.account_id,
            "creation_date": self.creation_date,
            "last_modified_date": self.last_modified_date,
            "default_branch": self.default_branch,
            "branch_count": self.branch_count,
            "branches": self.branches,
        }


@dataclass
class AuditResult:
    """리포지토리 감사 결과.

    수집된 리포지토리 목록과 감사 중 발생한 오류를 보관한다.

    Attributes:
        repositories: 수집된 리포지토리 목록.
        errors: 감사 중 발생한 오류 메시지 목록.
    """

    repositories: list[Repository] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_repos(self) -> int:
        """총 리포지토리 수.

        Returns:
            수집된 리포지토리 개수.
        """
        return len(self.repositories)

    @property
    def total_branches(self) -> int:
        """모든 리포지토리의 브랜치 총 수.

        Returns:
            전체 브랜치 개수 합계.
        """
        return sum(r.branch_count for r in self.repositories)

    @property
    def empty_repos(self) -> list[Repository]:
        """빈 리포지토리 목록.

        Returns:
            브랜치가 없는 리포지토리 목록.
        """
        return [r for r in self.repositories if r.is_empty]

    def get_repo_branch_pairs(self) -> list[dict[str, str]]:
        """리포지토리-브랜치 쌍 목록을 생성한다.

        빈 리포지토리는 branch가 "(empty)"로 표시된다.

        Returns:
            repository, branch, account_id 키를 가진 딕셔너리 목록.
        """
        pairs = []
        for repo in self.repositories:
            if repo.branches:
                for branch in repo.branches:
                    pairs.append(
                        {
                            "repository": repo.name,
                            "branch": branch,
                            "account_id": repo.account_id,
                        }
                    )
            else:
                pairs.append(
                    {
                        "repository": repo.name,
                        "branch": "(empty)",
                        "account_id": repo.account_id,
                    }
                )
        return pairs


class RepoAuditor:
    """CodeCommit 리포지토리 감사기.

    모든 리포지토리와 브랜치 정보를 수집하여 빈 리포지토리를 탐지한다.
    """

    def __init__(self, session, region: str | None = None):
        """RepoAuditor를 초기화한다.

        Args:
            session: boto3 Session 객체.
            region: 리전. 미지정 시 세션의 기본 리전을 사용한다.
        """
        self.session = session
        self.region = region

    def audit(self) -> AuditResult:
        """리포지토리 감사를 실행한다.

        모든 리포지토리를 조회하고 각 리포지토리의 브랜치 정보를 수집한다.

        Returns:
            감사 결과를 담은 AuditResult 객체.
        """
        repositories = []
        errors = []

        try:
            codecommit = self.session.client(
                "codecommit",
                region_name=self.region,
            )

            # 리포지토리 목록 조회
            repo_names = self._list_repositories(codecommit)
            logger.info(f"{len(repo_names)}개 리포지토리 발견")

            # 각 리포지토리 상세 정보 조회
            for repo_name in repo_names:
                try:
                    repo = self._get_repository_info(codecommit, repo_name)
                    repositories.append(repo)
                except Exception as e:
                    error_msg = f"리포지토리 {repo_name} 조회 실패: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"CodeCommit 접근 실패: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        return AuditResult(repositories=repositories, errors=errors)

    def _list_repositories(self, client) -> list[str]:
        """리포지토리 이름 목록을 조회한다.

        Args:
            client: CodeCommit boto3 클라이언트.

        Returns:
            리포지토리 이름 문자열 목록.
        """
        repo_names = []

        try:
            paginator = client.get_paginator("list_repositories")
            for page in paginator.paginate():
                for repo in page.get("repositories", []):
                    repo_names.append(repo["repositoryName"])
        except Exception as e:
            logger.error(f"리포지토리 목록 조회 실패: {e}")

        return repo_names

    def _get_repository_info(self, client, repo_name: str) -> Repository:
        """리포지토리 상세 정보(메타데이터 + 브랜치 목록)를 조회한다.

        Args:
            client: CodeCommit boto3 클라이언트.
            repo_name: 리포지토리 이름.

        Returns:
            Repository 객체.
        """
        # 리포지토리 메타데이터
        response = client.get_repository(repositoryName=repo_name)
        metadata = response.get("repositoryMetadata", {})

        # 브랜치 목록
        branches = self._list_branches(client, repo_name)

        return Repository(
            name=repo_name,
            description=metadata.get("repositoryDescription", ""),
            clone_url_http=metadata.get("cloneUrlHttp", ""),
            clone_url_ssh=metadata.get("cloneUrlSsh", ""),
            arn=metadata.get("Arn", ""),
            account_id=metadata.get("accountId", ""),
            creation_date=metadata.get("creationDate"),
            last_modified_date=metadata.get("lastModifiedDate"),
            default_branch=metadata.get("defaultBranch", ""),
            branches=branches,
        )

    def _list_branches(self, client, repo_name: str) -> list[str]:
        """리포지토리의 브랜치 목록을 조회한다.

        Args:
            client: CodeCommit boto3 클라이언트.
            repo_name: 리포지토리 이름.

        Returns:
            브랜치 이름 문자열 목록.
        """
        branches = []

        try:
            paginator = client.get_paginator("list_branches")
            for page in paginator.paginate(repositoryName=repo_name):
                branches.extend(page.get("branches", []))
        except Exception as e:
            logger.warning(f"리포지토리 {repo_name} 브랜치 조회 실패: {e}")

        return branches


# 리포트 컬럼 정의
COLUMNS_REPOS = [
    ColumnDef(header="Repository", width=30, style="data"),
    ColumnDef(header="Description", width=40, style="data"),
    ColumnDef(header="Default Branch", width=15, style="center"),
    ColumnDef(header="Branch Count", width=12, style="center"),
    ColumnDef(header="Created", width=12, style="date"),
    ColumnDef(header="Last Modified", width=12, style="date"),
]

COLUMNS_BRANCHES = [
    ColumnDef(header="Repository", width=30, style="data"),
    ColumnDef(header="Branch", width=30, style="data"),
]


class RepoAuditReporter:
    """CodeCommit 리포지토리 감사 결과 리포터.

    AuditResult를 콘솔 요약 또는 Excel 보고서로 출력한다.
    """

    def __init__(self, result: AuditResult):
        """RepoAuditReporter를 초기화한다.

        Args:
            result: 리포지토리 감사 결과 객체.
        """
        self.result = result

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "codecommit_repos",
    ) -> Path:
        """감사 결과를 Excel 보고서로 생성한다.

        분석 요약, Repositories, Branches, Empty Repos(해당 시) 시트를 포함한다.

        Args:
            output_dir: 보고서 저장 디렉토리 경로.
            file_prefix: 파일명 접두사.

        Returns:
            생성된 Excel 파일 경로.
        """
        wb = Workbook()

        # 요약 시트
        self._create_summary_sheet(wb)

        # 리포지토리 시트
        self._create_repos_sheet(wb)

        # 브랜치 시트
        self._create_branches_sheet(wb)

        # 빈 리포지토리 시트
        if self.result.empty_repos:
            self._create_empty_repos_sheet(wb)

        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"리포트 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """분석 요약 시트를 생성한다.

        전체 현황(리포지토리 수, 브랜치 수, 빈 리포지토리 수)과 오류 정보를 포함한다.

        Args:
            wb: Workbook 객체.
        """
        summary = wb.new_summary_sheet("분석 요약")

        summary.add_title("CodeCommit 리포지토리 분석 결과")

        summary.add_section("전체 현황")
        summary.add_item("총 리포지토리", f"{self.result.total_repos}개")
        summary.add_item("총 브랜치", f"{self.result.total_branches}개")
        summary.add_item(
            "빈 리포지토리",
            f"{len(self.result.empty_repos)}개",
            highlight="warning" if self.result.empty_repos else None,
        )

        if self.result.errors:
            summary.add_blank_row()
            summary.add_section("오류")
            for error in self.result.errors[:5]:
                summary.add_item("", error)

        summary.add_blank_row()
        summary.add_section("리포트 정보")
        summary.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _create_repos_sheet(self, wb: Workbook) -> None:
        """리포지토리 목록 시트를 생성한다.

        이름 순으로 정렬하여 각 리포지토리의 상세 정보를 출력한다.

        Args:
            wb: Workbook 객체.
        """
        sheet = wb.new_sheet(name="Repositories", columns=COLUMNS_REPOS)

        for repo in sorted(self.result.repositories, key=lambda r: r.name):
            row = [
                repo.name,
                repo.description,
                repo.default_branch,
                repo.branch_count,
                repo.creation_date,
                repo.last_modified_date,
            ]
            sheet.add_row(row)

        sheet.add_summary_row(
            [
                "합계",
                f"{self.result.total_repos}개",
                "",
                self.result.total_branches,
                "",
                "",
            ]
        )

    def _create_branches_sheet(self, wb: Workbook) -> None:
        """리포지토리-브랜치 쌍 시트를 생성한다.

        빈 리포지토리는 "(empty)"로 표시한다.

        Args:
            wb: Workbook 객체.
        """
        sheet = wb.new_sheet(name="Branches", columns=COLUMNS_BRANCHES)

        for repo in sorted(self.result.repositories, key=lambda r: r.name):
            if repo.branches:
                for branch in sorted(repo.branches):
                    sheet.add_row([repo.name, branch])
            else:
                sheet.add_row([repo.name, "(empty)"])

    def _create_empty_repos_sheet(self, wb: Workbook) -> None:
        """빈 리포지토리(브랜치 없음) 전용 시트를 생성한다.

        Args:
            wb: Workbook 객체.
        """
        columns = [
            ColumnDef(header="Repository", width=30, style="data"),
            ColumnDef(header="Created", width=12, style="date"),
            ColumnDef(header="Last Modified", width=12, style="date"),
        ]
        sheet = wb.new_sheet(name="Empty Repos", columns=columns)

        for repo in self.result.empty_repos:
            sheet.add_row(
                [
                    repo.name,
                    repo.creation_date,
                    repo.last_modified_date,
                ]
            )

    def print_summary(self) -> None:
        """감사 결과 요약을 콘솔에 출력한다.

        리포지토리 수, 브랜치 수, 빈 리포지토리 수와 함께 상위 10개 리포지토리를 표시한다.
        """
        print("\n=== CodeCommit 리포지토리 분석 결과 ===")
        print(f"총 리포지토리: {self.result.total_repos}개")
        print(f"총 브랜치: {self.result.total_branches}개")
        print(f"빈 리포지토리: {len(self.result.empty_repos)}개")

        if self.result.repositories:
            print("\n리포지토리 목록:")
            for repo in self.result.repositories[:10]:
                print(f"  {repo.name} ({repo.branch_count} branches)")

            if self.result.total_repos > 10:
                print(f"  ... 외 {self.result.total_repos - 10}개")


def generate_report(
    result: AuditResult,
    output_dir: str,
    file_prefix: str = "codecommit_repos",
) -> Path:
    """감사 결과를 Excel 보고서로 생성하는 편의 함수.

    내부적으로 RepoAuditReporter를 생성하여 위임한다.

    Args:
        result: 리포지토리 감사 결과 객체.
        output_dir: 보고서 저장 디렉토리 경로.
        file_prefix: 파일명 접두사.

    Returns:
        생성된 Excel 파일 경로.
    """
    reporter = RepoAuditReporter(result)
    return reporter.generate_report(output_dir, file_prefix)


# =============================================================================
# unused_all 연동용 함수 (collect_*, analyze_* 패턴)
# =============================================================================


@dataclass
class CodeCommitAnalysisResult:
    """CodeCommit 분석 결과 (unused_all 연동용).

    미사용 리소스 종합 분석(unused_all)과의 연동을 위한 결과 데이터.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 리전.
        total_repos: 총 리포지토리 수.
        empty_repos: 빈 리포지토리 수.
        total_branches: 전체 브랜치 수.
        repos: 수집된 리포지토리 목록.
        empty_repo_list: 빈 리포지토리 목록.
        unused_monthly_cost: 미사용 리소스 월 예상 비용. 빈 리포지토리는 무료이므로 항상 0.
    """

    account_id: str
    account_name: str
    region: str
    total_repos: int = 0
    empty_repos: int = 0
    total_branches: int = 0
    repos: list[Repository] = field(default_factory=list)
    empty_repo_list: list[Repository] = field(default_factory=list)

    # 비용 없음 (CodeCommit은 저장량 기반 과금, 빈 리포지토리는 무료)
    unused_monthly_cost: float = 0.0


def collect_repos(
    session,
    account_id: str,
    account_name: str,
    region: str,
) -> list[Repository]:
    """CodeCommit 리포지토리를 수집한다.

    리포지토리 목록을 조회한 뒤, 각 리포지토리의 메타데이터와 브랜치 정보를 수집한다.

    Args:
        session: boto3 Session 객체.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 조회 대상 리전.

    Returns:
        수집된 Repository 목록.
    """
    repos = []

    try:
        client = session.client("codecommit", region_name=region)

        # 리포지토리 목록 조회
        paginator = client.get_paginator("list_repositories")
        for page in paginator.paginate():
            for repo_info in page.get("repositories", []):
                repo_name = repo_info["repositoryName"]

                try:
                    # 리포지토리 상세 정보
                    response = client.get_repository(repositoryName=repo_name)
                    metadata = response.get("repositoryMetadata", {})

                    # 브랜치 목록
                    branches = _list_branches(client, repo_name)

                    repos.append(
                        Repository(
                            name=repo_name,
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            description=metadata.get("repositoryDescription", ""),
                            clone_url_http=metadata.get("cloneUrlHttp", ""),
                            clone_url_ssh=metadata.get("cloneUrlSsh", ""),
                            arn=metadata.get("Arn", ""),
                            creation_date=metadata.get("creationDate"),
                            last_modified_date=metadata.get("lastModifiedDate"),
                            default_branch=metadata.get("defaultBranch", ""),
                            branches=branches,
                        )
                    )
                except Exception as e:
                    logger.warning(f"리포지토리 {repo_name} 조회 실패: {e}")

    except Exception as e:
        logger.error(f"CodeCommit 리포지토리 수집 실패: {e}")

    return repos


def _list_branches(client, repo_name: str) -> list[str]:
    """리포지토리의 브랜치 목록을 조회한다.

    Args:
        client: CodeCommit boto3 클라이언트.
        repo_name: 리포지토리 이름.

    Returns:
        브랜치 이름 문자열 목록.
    """
    branches = []

    try:
        paginator = client.get_paginator("list_branches")
        for page in paginator.paginate(repositoryName=repo_name):
            branches.extend(page.get("branches", []))
    except Exception as e:
        logger.warning(f"리포지토리 {repo_name} 브랜치 조회 실패: {e}")

    return branches


def analyze_repos(
    repos: list[Repository],
    account_id: str,
    account_name: str,
    region: str,
) -> CodeCommitAnalysisResult:
    """수집된 CodeCommit 리포지토리를 분석한다.

    빈 리포지토리(브랜치 없음)를 식별하고 통계를 집계한다.

    Args:
        repos: 수집된 Repository 목록.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 리전.

    Returns:
        분석 결과를 담은 CodeCommitAnalysisResult 객체.
    """
    empty_repos = [r for r in repos if r.is_empty]
    total_branches = sum(r.branch_count for r in repos)

    return CodeCommitAnalysisResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_repos=len(repos),
        empty_repos=len(empty_repos),
        total_branches=total_branches,
        repos=repos,
        empty_repo_list=empty_repos,
        unused_monthly_cost=0.0,  # 빈 리포지토리는 비용 없음
    )


# =============================================================================
# CLI 진입점 함수
# =============================================================================


def run_audit(ctx) -> dict[str, Any]:
    """CodeCommit 리포지토리 분석 도구의 메인 실행 함수.

    모든 리포지토리를 감사하고, 결과를 콘솔에 출력한 뒤 Excel 보고서를 생성한다.

    Args:
        ctx: 실행 컨텍스트. 리전, 프로파일 등을 포함한다.

    Returns:
        분석 결과 요약 딕셔너리. total_repos, total_branches, empty_repos, report_path 등을 포함한다.
    """
    from core.auth.session import get_context_session
    from core.shared.io.output import OutputPath

    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)

    auditor = RepoAuditor(session=session, region=region)
    result = auditor.audit()

    reporter = RepoAuditReporter(result)
    reporter.print_summary()

    if result.total_repos > 0:
        identifier = ctx.profile_name or "default"
        output_dir = OutputPath(identifier).sub("codecommit", "unused").with_date().build()

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


def run_empty_repos(ctx) -> dict[str, Any]:
    """빈 리포지토리(브랜치 없음)만 조회하는 실행 함수.

    감사 결과에서 빈 리포지토리만 필터링하여 콘솔에 출력한다.

    Args:
        ctx: 실행 컨텍스트. 리전, 프로파일 등을 포함한다.

    Returns:
        빈 리포지토리 이름 목록과 개수를 포함하는 딕셔너리.
    """
    from core.auth.session import get_context_session

    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)

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
