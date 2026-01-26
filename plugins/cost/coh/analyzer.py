"""
plugins/cost/coh/analyzer.py - Cost Optimization Hub 분석기

AWS Cost Optimization Hub에서 모든 비용 최적화 권장사항을 조회합니다.
- Rightsizing, Stop, Delete, ScaleIn, Upgrade
- Savings Plans, Reserved Instances
- Graviton Migration

Note:
    Cost Optimization Hub는 us-east-1에서만 사용 가능합니다.
    Organizations 관리 계정 또는 위임된 관리자 계정에서 전체 조직 권장사항 조회 가능.

사용법:
    from plugins.cost.coh.analyzer import CostOptimizationAnalyzer

    analyzer = CostOptimizationAnalyzer(session)
    recommendations = analyzer.get_recommendations(
        action_types=["Rightsize", "Stop"],
        resource_types=["Ec2Instance", "RdsDbInstance"],
    )
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Cost Optimization Hub는 us-east-1에서만 사용 가능
COH_REGION = "us-east-1"

# 월간 평균 시간 (AWS 기준)
HOURS_PER_MONTH = 730


@dataclass
class RecommendationFilter:
    """Cost Optimization Hub 권장사항 필터"""

    action_types: list[str] = field(default_factory=list)
    resource_types: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    account_ids: list[str] = field(default_factory=list)
    implementation_efforts: list[str] = field(default_factory=list)
    restart_needed: bool | None = None
    rollback_possible: bool | None = None
    lookback_periods: list[int] = field(default_factory=list)

    # 지원되는 Action Types (AWS 문서 기준)
    VALID_ACTION_TYPES = [
        "Rightsize",
        "Stop",
        "Delete",
        "ScaleIn",
        "Upgrade",
        "PurchaseSavingsPlans",
        "PurchaseReservedInstances",
        "MigrateToGraviton",
    ]

    # 지원되는 Resource Types (AWS 문서 기준)
    VALID_RESOURCE_TYPES = [
        # EC2 관련
        "Ec2Instance",
        "Ec2AutoScalingGroup",
        "EbsVolume",
        # 컨테이너/서버리스
        "EcsService",
        "LambdaFunction",
        # 데이터베이스
        "RdsDbInstance",
        "RdsDbInstanceStorage",
        "AuroraDbClusterStorage",
        # Savings Plans
        "ComputeSavingsPlans",
        "Ec2InstanceSavingsPlans",
        "SageMakerSavingsPlans",
        # Reserved Instances
        "Ec2ReservedInstances",
        "RdsReservedInstances",
        "RedshiftReservedNodes",
        "OpenSearchReservedInstances",
        "ElastiCacheReservedNodes",
        "MemoryDbReservedInstances",
        "DynamoDbReservedCapacity",
    ]

    VALID_IMPLEMENTATION_EFFORTS = [
        "VeryLow",
        "Low",
        "Medium",
        "High",
        "VeryHigh",
    ]

    # Optimizable Services (Cost Efficiency 계산에 포함되는 서비스)
    OPTIMIZABLE_SERVICES = [
        "Amazon EC2",
        "Amazon ECS",
        "Amazon EKS",
        "Amazon EBS",
        "Amazon RDS",
        "Amazon SageMaker",
        "Amazon Redshift",
        "AWS Lambda",
        "OpenSearch",
        "MemoryDB",
        "DynamoDB",
        "ElastiCache",
    ]

    def to_api_filter(self) -> dict[str, Any]:
        """AWS API 필터 형식으로 변환"""
        api_filter: dict[str, Any] = {}

        if self.action_types:
            api_filter["actionTypes"] = self.action_types
        if self.resource_types:
            api_filter["resourceTypes"] = self.resource_types
        if self.regions:
            api_filter["regions"] = self.regions
        if self.account_ids:
            api_filter["accountIds"] = self.account_ids
        if self.implementation_efforts:
            api_filter["implementationEfforts"] = self.implementation_efforts
        if self.restart_needed is not None:
            api_filter["restartNeeded"] = self.restart_needed
        if self.rollback_possible is not None:
            api_filter["rollbackPossible"] = self.rollback_possible

        return api_filter


@dataclass
class Recommendation:
    """Cost Optimization Hub 권장사항"""

    recommendation_id: str
    account_id: str
    region: str
    resource_id: str
    resource_arn: str
    current_resource_type: str
    recommended_resource_type: str
    current_resource_summary: str
    recommended_resource_summary: str
    action_type: str
    estimated_monthly_cost: float
    estimated_monthly_savings: float
    estimated_savings_percentage: float
    implementation_effort: str
    restart_needed: bool
    rollback_possible: bool
    lookback_period_days: int
    tags: dict[str, str]
    source: str
    last_refresh_timestamp: str | None = None

    @classmethod
    def from_api_response(cls, item: dict[str, Any]) -> Recommendation:
        """API 응답에서 Recommendation 객체 생성"""
        tags_list = item.get("tags", [])
        tags_dict = {tag["key"]: tag["value"] for tag in tags_list}

        return cls(
            recommendation_id=item.get("recommendationId", ""),
            account_id=item.get("accountId", ""),
            region=item.get("region", ""),
            resource_id=item.get("resourceId", ""),
            resource_arn=item.get("resourceArn", ""),
            current_resource_type=item.get("currentResourceType", ""),
            recommended_resource_type=item.get("recommendedResourceType", ""),
            current_resource_summary=item.get("currentResourceSummary", ""),
            recommended_resource_summary=item.get("recommendedResourceSummary", ""),
            action_type=item.get("actionType", ""),
            estimated_monthly_cost=float(item.get("estimatedMonthlyCost", 0)),
            estimated_monthly_savings=float(item.get("estimatedMonthlySavings", 0)),
            estimated_savings_percentage=float(item.get("estimatedSavingsPercentage", 0)),
            implementation_effort=item.get("implementationEffort", ""),
            restart_needed=item.get("restartNeeded", False),
            rollback_possible=item.get("rollbackPossible", False),
            lookback_period_days=item.get("recommendationLookbackPeriodInDays", 0),
            tags=tags_dict,
            source=item.get("source", ""),
            last_refresh_timestamp=item.get("lastRefreshTimestamp"),
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (리포트용)"""
        return {
            "recommendation_id": self.recommendation_id,
            "account_id": self.account_id,
            "region": self.region,
            "resource_id": self.resource_id,
            "resource_arn": self.resource_arn,
            "current_resource_type": self.current_resource_type,
            "recommended_resource_type": self.recommended_resource_type,
            "current_resource_summary": self.current_resource_summary,
            "recommended_resource_summary": self.recommended_resource_summary,
            "action_type": self.action_type,
            "estimated_monthly_cost": self.estimated_monthly_cost,
            "estimated_monthly_savings": self.estimated_monthly_savings,
            "estimated_savings_percentage": self.estimated_savings_percentage,
            "implementation_effort": self.implementation_effort,
            "restart_needed": self.restart_needed,
            "rollback_possible": self.rollback_possible,
            "lookback_period_days": self.lookback_period_days,
            "tags": self.tags,
            "source": self.source,
        }


class CostOptimizationAnalyzer:
    """AWS Cost Optimization Hub 분석기

    Cost Optimization Hub API를 호출하여 모든 비용 최적화 권장사항을 조회합니다.

    Attributes:
        session: boto3 Session 객체
        client: cost-optimization-hub 클라이언트

    Example:
        analyzer = CostOptimizationAnalyzer(session)

        # 모든 권장사항 조회
        all_recs = analyzer.get_recommendations()

        # 라이트사이징만 조회
        rightsizing = analyzer.get_recommendations(
            action_types=["Rightsize"],
            resource_types=["Ec2Instance", "RdsDbInstance"],
        )

        # 유휴 리소스 조회
        idle = analyzer.get_recommendations(
            action_types=["Stop", "Delete"],
        )

        # 요약 통계
        summary = analyzer.get_summary()
    """

    def __init__(self, session):
        """초기화

        Args:
            session: boto3.Session 객체
        """
        self.session = session
        self.client = session.client("cost-optimization-hub", region_name=COH_REGION)

    def get_recommendations(
        self,
        action_types: list[str] | None = None,
        resource_types: list[str] | None = None,
        regions: list[str] | None = None,
        account_ids: list[str] | None = None,
        lookback_periods: list[int] | None = None,
        include_all: bool = True,
        page_size: int = 100,
    ) -> list[Recommendation]:
        """비용 최적화 권장사항 조회

        Args:
            action_types: 액션 유형 필터 (Rightsize, Stop, Delete, Upgrade 등)
            resource_types: 리소스 유형 필터 (Ec2Instance, RdsDbInstance 등)
            regions: 리전 필터
            account_ids: 계정 ID 필터
            lookback_periods: lookback 기간 필터 (일 단위, 예: [14, 32])
            include_all: 모든 권장사항 포함 여부
            page_size: 페이지당 항목 수

        Returns:
            Recommendation 객체 리스트
        """
        rec_filter = RecommendationFilter(
            action_types=action_types or [],
            resource_types=resource_types or [],
            regions=regions or [],
            account_ids=account_ids or [],
            lookback_periods=lookback_periods or [],
        )

        recommendations = []

        for item in self._paginate_recommendations(rec_filter, include_all, page_size):
            # lookback_periods 필터 적용 (API에서 지원하지 않으므로 클라이언트에서 필터링)
            if rec_filter.lookback_periods:
                lookback = item.get("recommendationLookbackPeriodInDays", 0)
                if lookback not in rec_filter.lookback_periods:
                    continue

            rec = Recommendation.from_api_response(item)
            recommendations.append(rec)

        logger.info(f"총 {len(recommendations)}개의 권장사항 조회됨")
        return recommendations

    def _paginate_recommendations(
        self,
        rec_filter: RecommendationFilter,
        include_all: bool,
        page_size: int,
    ) -> Iterator[dict[str, Any]]:
        """권장사항 페이지네이션 처리"""
        try:
            paginator = self.client.get_paginator("list_recommendations")

            api_filter = rec_filter.to_api_filter()

            paginate_params = {
                "includeAllRecommendations": include_all,
                "PaginationConfig": {"PageSize": page_size},
            }

            if api_filter:
                paginate_params["filter"] = api_filter

            page_iterator = paginator.paginate(**paginate_params)

            for page in page_iterator:
                items = page.get("items", [])
                logger.debug(f"페이지에서 {len(items)}개 권장사항 조회")
                yield from items

        except Exception as e:
            logger.error(f"권장사항 조회 실패: {e}")
            raise

    def get_summary(
        self,
        group_by: str = "resource_type",
        recommendations: list[Recommendation] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """권장사항 요약 통계

        Args:
            group_by: 그룹화 기준 (resource_type, action_type, region, account_id)
            recommendations: 이미 조회된 권장사항 (없으면 새로 조회)

        Returns:
            그룹별 요약 {그룹명: {"count": N, "savings": $, "cost": $}}
        """
        if recommendations is None:
            recommendations = self.get_recommendations()

        summary = {}

        for rec in recommendations:
            if group_by == "resource_type":
                key = rec.current_resource_type
            elif group_by == "action_type":
                key = rec.action_type
            elif group_by == "region":
                key = rec.region
            elif group_by == "account_id":
                key = rec.account_id
            else:
                key = "all"

            if key not in summary:
                summary[key] = {"count": 0, "savings": 0.0, "cost": 0.0}

            summary[key]["count"] += 1
            summary[key]["savings"] += rec.estimated_monthly_savings
            summary[key]["cost"] += rec.estimated_monthly_cost

        # 소수점 정리
        for key in summary:
            summary[key]["savings"] = round(summary[key]["savings"], 2)
            summary[key]["cost"] = round(summary[key]["cost"], 2)

        return summary

    def get_total_savings(self, recommendations: list[Recommendation] | None = None) -> float:
        """총 잠재적 월간 절약액 계산

        Args:
            recommendations: 이미 조회된 권장사항 (없으면 새로 조회)

        Returns:
            총 월간 절약액 (USD)
        """
        if recommendations is None:
            recommendations = self.get_recommendations()

        return round(sum(rec.estimated_monthly_savings for rec in recommendations), 2)

    def get_enrollment_status(self) -> dict[str, Any]:
        """Cost Optimization Hub 등록 상태 확인

        Returns:
            등록 상태 정보 딕셔너리
        """
        try:
            response = self.client.list_enrollment_statuses()
            return {
                "items": response.get("items", []),
                "include_member_accounts": response.get("includeMemberAccounts", False),
            }
        except Exception as e:
            logger.error(f"등록 상태 조회 실패: {e}")
            return {"items": [], "include_member_accounts": False}

    def get_preferences(self) -> dict[str, Any]:
        """Cost Optimization Hub 설정 조회

        Returns:
            설정 정보 (savings_estimation_mode, preferred_commitment 등)
        """
        try:
            response = self.client.get_preferences()
            return {
                "savings_estimation_mode": response.get("savingsEstimationMode", ""),
                "member_account_discount_visibility": response.get("memberAccountDiscountVisibility", ""),
            }
        except Exception as e:
            logger.error(f"설정 조회 실패: {e}")
            return {}
