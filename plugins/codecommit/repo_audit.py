"""
plugins/codecommit/repo_audit.py - CodeCommit 리포지토리 분석

모든 CodeCommit 리포지토리와 브랜치 정보를 조회합니다.

사용 케이스:
- 전체 리포지토리/브랜치 현황 파악
- 미사용/방치된 리포지토리 식별
- 멀티 계정 CodeCommit 사용 현황 감사

사용법:
    from plugins.codecommit.repo_audit import RepoAuditor

    auditor = RepoAuditor(session)
    result = auditor.audit()
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.tools.io.excel import ColumnDef, Workbook

logger = logging.getLogger(__name__)


@dataclass
class Repository:
    """CodeCommit 리포지토리 정보"""

    name: str
    description: str = ""
    clone_url_http: str = ""
    clone_url_ssh: str = ""
    arn: str = ""
    account_id: str = ""
    creation_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None
    default_branch: str = ""
    branches: List[str] = field(default_factory=list)

    @property
    def branch_count(self) -> int:
        return len(self.branches)

    @property
    def is_empty(self) -> bool:
        """브랜치가 없는 빈 리포지토리인지"""
        return self.branch_count == 0

    def to_dict(self) -> Dict[str, Any]:
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
    """리포지토리 감사 결과"""

    repositories: List[Repository] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_repos(self) -> int:
        return len(self.repositories)

    @property
    def total_branches(self) -> int:
        return sum(r.branch_count for r in self.repositories)

    @property
    def empty_repos(self) -> List[Repository]:
        """빈 리포지토리 목록"""
        return [r for r in self.repositories if r.is_empty]

    def get_repo_branch_pairs(self) -> List[Dict[str, str]]:
        """리포지토리-브랜치 쌍 목록"""
        pairs = []
        for repo in self.repositories:
            if repo.branches:
                for branch in repo.branches:
                    pairs.append({
                        "repository": repo.name,
                        "branch": branch,
                        "account_id": repo.account_id,
                    })
            else:
                pairs.append({
                    "repository": repo.name,
                    "branch": "(empty)",
                    "account_id": repo.account_id,
                })
        return pairs


class RepoAuditor:
    """CodeCommit 리포지토리 감사기

    모든 리포지토리와 브랜치 정보를 수집합니다.
    """

    def __init__(self, session, region: str = None):
        """초기화

        Args:
            session: boto3.Session 객체
            region: 리전 (기본: 세션 리전)
        """
        self.session = session
        self.region = region

    def audit(self) -> AuditResult:
        """리포지토리 감사 실행

        Returns:
            AuditResult 객체
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

    def _list_repositories(self, client) -> List[str]:
        """리포지토리 이름 목록 조회"""
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
        """리포지토리 상세 정보 조회"""
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

    def _list_branches(self, client, repo_name: str) -> List[str]:
        """브랜치 목록 조회"""
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
    """리포지토리 감사 결과 리포터"""

    def __init__(self, result: AuditResult):
        self.result = result

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "codecommit_repos",
    ) -> Path:
        """Excel 리포트 생성"""
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
        """요약 시트"""
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
        """리포지토리 시트"""
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

        sheet.add_summary_row([
            "합계",
            f"{self.result.total_repos}개",
            "",
            self.result.total_branches,
            "",
            "",
        ])

    def _create_branches_sheet(self, wb: Workbook) -> None:
        """브랜치 시트"""
        sheet = wb.new_sheet(name="Branches", columns=COLUMNS_BRANCHES)

        for repo in sorted(self.result.repositories, key=lambda r: r.name):
            if repo.branches:
                for branch in sorted(repo.branches):
                    sheet.add_row([repo.name, branch])
            else:
                sheet.add_row([repo.name, "(empty)"])

    def _create_empty_repos_sheet(self, wb: Workbook) -> None:
        """빈 리포지토리 시트"""
        columns = [
            ColumnDef(header="Repository", width=30, style="data"),
            ColumnDef(header="Created", width=12, style="date"),
            ColumnDef(header="Last Modified", width=12, style="date"),
        ]
        sheet = wb.new_sheet(name="Empty Repos", columns=columns)

        for repo in self.result.empty_repos:
            sheet.add_row([
                repo.name,
                repo.creation_date,
                repo.last_modified_date,
            ])

    def print_summary(self) -> None:
        """콘솔에 요약 출력"""
        print(f"\n=== CodeCommit 리포지토리 분석 결과 ===")
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
    """리포트 생성 (편의 함수)"""
    reporter = RepoAuditReporter(result)
    return reporter.generate_report(output_dir, file_prefix)
