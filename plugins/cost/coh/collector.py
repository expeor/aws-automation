"""
plugins/cost/coh/collector.py - Cost Optimization Hub 권장사항 수집기

Cost Optimization Hub에서 권장사항을 수집하고 필터링합니다.
- 모든 권장사항 유형 지원 (Rightsizing, Idle, Commitment 등)
- 계정별 필터링 지원 (환경변수 또는 직접 지정)

사용법:
    from plugins.cost.coh.collector import CostOptimizationCollector

    collector = CostOptimizationCollector(session)
    results = collector.collect(
        action_types=["Rightsize"],
        exclude_account_ids=["123456789012"],
    )

환경변수:
    AA_COH_EXCLUDE_ACCOUNT_IDS: 제외할 계정 ID 목록 (쉼표 구분)
    AA_COH_EXCLUDE_ACCOUNT_NAMES: 제외할 계정 이름 목록 (쉼표 구분)
    AA_COH_EXCLUDE_ACCOUNT_NAME_REGEX: 제외할 계정 이름 정규식
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .analyzer import CostOptimizationAnalyzer, Recommendation

logger = logging.getLogger(__name__)


@dataclass
class AccountFilter:
    """계정 필터링 설정"""

    exclude_ids: set[str] = field(default_factory=set)
    exclude_names: set[str] = field(default_factory=set)
    exclude_name_patterns: list[str] = field(default_factory=list)
    include_ids: set[str] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> AccountFilter:
        """환경변수에서 AccountFilter 생성"""
        exclude_ids = set()
        exclude_names = set()
        exclude_patterns = []

        ids_env = os.getenv("AA_COH_EXCLUDE_ACCOUNT_IDS", "").strip()
        if ids_env:
            exclude_ids = {x.strip() for x in re.split(r"[,|]", ids_env) if x.strip()}

        names_env = os.getenv("AA_COH_EXCLUDE_ACCOUNT_NAMES", "").strip()
        if names_env:
            exclude_names = {x.strip() for x in re.split(r"[,|]", names_env) if x.strip()}

        regex_env = os.getenv("AA_COH_EXCLUDE_ACCOUNT_NAME_REGEX", "").strip()
        if regex_env:
            exclude_patterns = [x.strip() for x in re.split(r"[,|]", regex_env) if x.strip()]

        return cls(
            exclude_ids=exclude_ids,
            exclude_names=exclude_names,
            exclude_name_patterns=exclude_patterns,
        )

    def should_exclude(
        self,
        account_id: str,
        account_name: str | None = None,
    ) -> bool:
        """계정을 제외해야 하는지 확인"""
        if self.include_ids and account_id not in self.include_ids:
            return True

        if account_id in self.exclude_ids:
            return True

        if account_name:
            if account_name in self.exclude_names:
                return True
            if account_name.lower() in {n.lower() for n in self.exclude_names}:
                return True
            for pattern in self.exclude_name_patterns:
                if re.search(pattern, account_name, re.IGNORECASE):
                    return True

        return False


@dataclass
class CollectionResult:
    """권장사항 수집 결과"""

    recommendations: list[Recommendation]
    total_count: int
    filtered_count: int
    excluded_accounts: set[str]
    summary_by_resource: dict[str, dict[str, Any]]
    summary_by_action: dict[str, dict[str, Any]]

    @property
    def total_savings(self) -> float:
        """총 잠재적 월간 절약액"""
        return round(sum(r.estimated_monthly_savings for r in self.recommendations), 2)

    @property
    def total_cost(self) -> float:
        """총 월간 비용"""
        return round(sum(r.estimated_monthly_cost for r in self.recommendations), 2)

    def get_by_action_type(self) -> dict[str, list[Recommendation]]:
        """액션 타입별 권장사항 그룹화"""
        grouped: dict[str, list[Recommendation]] = {}
        for rec in self.recommendations:
            if rec.action_type not in grouped:
                grouped[rec.action_type] = []
            grouped[rec.action_type].append(rec)
        return grouped

    def get_by_resource_type(self) -> dict[str, list[Recommendation]]:
        """리소스 타입별 권장사항 그룹화"""
        grouped: dict[str, list[Recommendation]] = {}
        for rec in self.recommendations:
            if rec.current_resource_type not in grouped:
                grouped[rec.current_resource_type] = []
            grouped[rec.current_resource_type].append(rec)
        return grouped

    def get_by_account(self) -> dict[str, list[Recommendation]]:
        """계정별 권장사항 그룹화"""
        grouped: dict[str, list[Recommendation]] = {}
        for rec in self.recommendations:
            if rec.account_id not in grouped:
                grouped[rec.account_id] = []
            grouped[rec.account_id].append(rec)
        return grouped


class CostOptimizationCollector:
    """Cost Optimization Hub 권장사항 수집기

    권장사항을 수집하고 계정/리소스 타입별로 필터링합니다.
    """

    def __init__(
        self,
        session,
        account_filter: AccountFilter | None = None,
        account_name_resolver: Callable[[str], str | None] | None = None,
    ):
        """초기화

        Args:
            session: boto3.Session 객체
            account_filter: 계정 필터 (None이면 환경변수에서 로드)
            account_name_resolver: 계정 ID → 이름 변환 함수 (optional)
        """
        self.session = session
        self.analyzer = CostOptimizationAnalyzer(session)
        self.account_filter = account_filter or AccountFilter.from_env()
        self.account_name_resolver = account_name_resolver
        self._account_name_cache: dict[str, str] = {}

    def collect(
        self,
        action_types: list[str] | None = None,
        resource_types: list[str] | None = None,
        regions: list[str] | None = None,
        lookback_periods: list[int] | None = None,
        exclude_account_ids: list[str] | None = None,
        include_account_ids: list[str] | None = None,
        include_all: bool = True,
    ) -> CollectionResult:
        """권장사항 수집 및 필터링

        Args:
            action_types: 액션 유형 필터
            resource_types: 리소스 유형 필터
            regions: 리전 필터
            lookback_periods: lookback 기간 필터 (일 단위)
            exclude_account_ids: 추가로 제외할 계정 ID
            include_account_ids: 포함할 계정 ID (지정 시 해당 계정만)
            include_all: 모든 권장사항 포함 여부

        Returns:
            CollectionResult 객체
        """
        if exclude_account_ids:
            self.account_filter.exclude_ids.update(exclude_account_ids)
        if include_account_ids:
            self.account_filter.include_ids.update(include_account_ids)

        all_recommendations = self.analyzer.get_recommendations(
            action_types=action_types,
            resource_types=resource_types,
            regions=regions,
            lookback_periods=lookback_periods,
            include_all=include_all,
        )

        total_count = len(all_recommendations)

        filtered_recommendations = []
        excluded_accounts = set()

        for rec in all_recommendations:
            account_name = self._resolve_account_name(rec.account_id)

            if self.account_filter.should_exclude(rec.account_id, account_name):
                excluded_accounts.add(rec.account_id)
                continue

            filtered_recommendations.append(rec)

        filtered_count = len(filtered_recommendations)

        logger.info(
            f"권장사항 수집 완료: 전체 {total_count}개, "
            f"필터링 후 {filtered_count}개, "
            f"제외된 계정 {len(excluded_accounts)}개"
        )

        summary_by_resource = self.analyzer.get_summary(
            recommendations=filtered_recommendations,
            group_by="resource_type",
        )
        summary_by_action = self.analyzer.get_summary(
            recommendations=filtered_recommendations,
            group_by="action_type",
        )

        return CollectionResult(
            recommendations=filtered_recommendations,
            total_count=total_count,
            filtered_count=filtered_count,
            excluded_accounts=excluded_accounts,
            summary_by_resource=summary_by_resource,
            summary_by_action=summary_by_action,
        )

    def collect_all(
        self,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """모든 권장사항 수집 (편의 메서드)"""
        return self.collect(exclude_account_ids=exclude_account_ids)

    def collect_rightsizing(
        self,
        resource_types: list[str] | None = None,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """라이트사이징 권장사항만 수집"""
        default_resource_types = [
            "Ec2Instance",
            "RdsDbInstance",
            "LambdaFunction",
            "EcsService",
            "EbsVolume",
        ]
        return self.collect(
            action_types=["Rightsize"],
            resource_types=resource_types or default_resource_types,
            exclude_account_ids=exclude_account_ids,
        )

    def collect_idle_resources(
        self,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """유휴 리소스 권장사항 수집 (Stop, Delete)"""
        return self.collect(
            action_types=["Stop", "Delete"],
            exclude_account_ids=exclude_account_ids,
        )

    def collect_commitment_opportunities(
        self,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """Savings Plans/Reserved Instances 권장사항 수집"""
        return self.collect(
            action_types=["PurchaseSavingsPlans", "PurchaseReservedInstances"],
            exclude_account_ids=exclude_account_ids,
        )

    def collect_graviton_migration(
        self,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """Graviton 마이그레이션 권장사항 수집"""
        return self.collect(
            action_types=["MigrateToGraviton"],
            exclude_account_ids=exclude_account_ids,
        )

    def collect_upgrades(
        self,
        exclude_account_ids: list[str] | None = None,
    ) -> CollectionResult:
        """업그레이드 권장사항 수집"""
        return self.collect(
            action_types=["Upgrade"],
            exclude_account_ids=exclude_account_ids,
        )

    def _resolve_account_name(self, account_id: str) -> str | None:
        """계정 ID에서 이름 조회 (캐시 사용)"""
        if account_id in self._account_name_cache:
            return self._account_name_cache[account_id]

        if self.account_name_resolver:
            name = self.account_name_resolver(account_id)
            if name:
                self._account_name_cache[account_id] = name
                return name

        return None

    def set_account_names(self, account_map: dict[str, str]) -> None:
        """계정 ID → 이름 매핑 설정"""
        self._account_name_cache.update(account_map)
