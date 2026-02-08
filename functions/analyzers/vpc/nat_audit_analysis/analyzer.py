"""
NAT Gateway 분석기

분석 항목:
1. 미사용 NAT Gateway 탐지 (14일간 트래픽 0)
2. 저사용 NAT Gateway 탐지 (일평균 트래픽 < 1GB)
3. 비용 최적화 기회 식별
4. 신뢰도 분류 (확실히 미사용 / 아마 미사용 / 검토 필요)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .collector import NATAuditData, NATGateway


class UsageStatus(Enum):
    """NAT Gateway의 사용 상태를 분류하는 열거형.

    CloudWatch 트래픽 메트릭 기반으로 판별한 사용 상태를 나타낸다.

    Attributes:
        UNUSED: 분석 기간 동안 아웃바운드 트래픽이 없는 NAT Gateway.
        LOW_USAGE: 일평균 트래픽이 임계치(1GB) 미만인 저사용 NAT Gateway.
        NORMAL: 정상 사용 중인 NAT Gateway.
        PENDING: 생성 직후이거나 상태가 안정화되지 않은 NAT Gateway.
        UNKNOWN: 메트릭 데이터를 수집할 수 없는 NAT Gateway.
    """

    UNUSED = "unused"
    LOW_USAGE = "low_usage"
    NORMAL = "normal"
    PENDING = "pending"
    UNKNOWN = "unknown"


class Confidence(Enum):
    """분석 결과의 판단 신뢰도를 나타내는 열거형.

    Attributes:
        HIGH: 확실한 판단으로 즉시 조치 가능.
        MEDIUM: 추가 검토가 필요한 수준.
        LOW: 데이터 부족으로 판단이 어려운 수준.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(Enum):
    """분석 결과의 심각도를 나타내는 열거형.

    Attributes:
        CRITICAL: 즉시 조치 필요 (미사용 + 고비용).
        HIGH: 빠른 조치 권장.
        MEDIUM: 검토 필요.
        LOW: 참고 수준.
        INFO: 정보 제공 목적.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class NATFinding:
    """개별 NAT Gateway에 대한 분석 결과.

    사용 상태, 신뢰도, 심각도, 비용 낭비 추정치 등을 포함한다.

    Attributes:
        nat: 분석 대상 NATGateway 인스턴스.
        usage_status: 판별된 사용 상태.
        confidence: 판단 신뢰도.
        severity: 심각도 등급.
        description: 분석 결과 설명 (한글).
        recommendation: 권장 조치 사항 (한글).
        monthly_waste: 월간 낭비 비용 추정 (USD).
        annual_savings: 연간 절감 가능 금액 (USD).
        details: 분석 세부 데이터 (바이트, 일수 등).
    """

    nat: NATGateway
    usage_status: UsageStatus
    confidence: Confidence
    severity: Severity
    description: str
    recommendation: str

    # 비용 관련
    monthly_waste: float = 0.0  # 월간 낭비 추정
    annual_savings: float = 0.0  # 연간 절감 가능액

    # 세부 정보
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class NATAnalysisResult:
    """계정/리전 단위 NAT Gateway 분석 결과 전체.

    개별 finding 목록과 함께 요약 통계(카운트, 비용)를 집계한다.

    Attributes:
        audit_data: 원본 감사 데이터.
        findings: 개별 NAT Gateway 분석 결과 목록.
        total_nat_count: 전체 NAT Gateway 수.
        unused_count: 미사용 NAT Gateway 수.
        low_usage_count: 저사용 NAT Gateway 수.
        normal_count: 정상 사용 NAT Gateway 수.
        pending_count: 대기 중 NAT Gateway 수.
        total_monthly_cost: 전체 월간 비용 합계 (USD).
        total_monthly_waste: 월간 낭비 비용 합계 (USD).
        total_annual_savings: 연간 절감 가능 금액 합계 (USD).
    """

    audit_data: NATAuditData
    findings: list[NATFinding] = field(default_factory=list)

    # 요약 통계
    total_nat_count: int = 0
    unused_count: int = 0
    low_usage_count: int = 0
    normal_count: int = 0
    pending_count: int = 0

    # 비용 요약
    total_monthly_cost: float = 0.0
    total_monthly_waste: float = 0.0
    total_annual_savings: float = 0.0


class NATAnalyzer:
    """NAT Gateway 미사용/저사용 분석기.

    CloudWatch 트래픽 메트릭과 NAT Gateway 메타데이터를 기반으로
    미사용/저사용 여부를 판별하고 비용 절감 기회를 식별한다.

    Args:
        audit_data: NATCollector가 수집한 감사 데이터.
    """

    # 저사용 기준: 일평균 1GB 미만
    LOW_USAGE_THRESHOLD_GB_PER_DAY = 1.0

    # 최소 생성 일수 (이보다 젊으면 PENDING)
    MIN_AGE_DAYS = 7

    def __init__(self, audit_data: NATAuditData):
        self.audit_data = audit_data

    def analyze(self) -> NATAnalysisResult:
        """모든 NAT Gateway에 대해 미사용/저사용 분석을 수행한다.

        Returns:
            통계 요약과 개별 Finding을 포함하는 NATAnalysisResult.
        """
        result = NATAnalysisResult(audit_data=self.audit_data)

        for nat in self.audit_data.nat_gateways:
            finding = self._analyze_nat(nat)
            result.findings.append(finding)

            # 통계 업데이트
            if finding.usage_status == UsageStatus.UNUSED:
                result.unused_count += 1
            elif finding.usage_status == UsageStatus.LOW_USAGE:
                result.low_usage_count += 1
            elif finding.usage_status == UsageStatus.NORMAL:
                result.normal_count += 1
            elif finding.usage_status == UsageStatus.PENDING:
                result.pending_count += 1

        # 전체 통계
        result.total_nat_count = len(self.audit_data.nat_gateways)
        result.total_monthly_cost = sum(f.nat.total_monthly_cost for f in result.findings)
        result.total_monthly_waste = sum(f.monthly_waste for f in result.findings)
        result.total_annual_savings = sum(f.annual_savings for f in result.findings)

        return result

    def _analyze_nat(self, nat: NATGateway) -> NATFinding:
        """개별 NAT Gateway의 사용 상태를 분석한다.

        Args:
            nat: 분석할 NAT Gateway 정보.

        Returns:
            사용 상태, 신뢰도, 심각도, 비용 절감 추정을 포함하는 NATFinding.
        """

        # 상태가 available이 아니면 PENDING
        if nat.state != "available":
            return NATFinding(
                nat=nat,
                usage_status=UsageStatus.PENDING,
                confidence=Confidence.HIGH,
                severity=Severity.INFO,
                description=f"NAT Gateway 상태: {nat.state}",
                recommendation="상태가 안정화될 때까지 대기하세요.",
            )

        # 생성된 지 7일 미만이면 PENDING
        if nat.age_days < self.MIN_AGE_DAYS:
            return NATFinding(
                nat=nat,
                usage_status=UsageStatus.PENDING,
                confidence=Confidence.MEDIUM,
                severity=Severity.INFO,
                description=f"최근 생성됨 ({nat.age_days}일 전)",
                recommendation="충분한 데이터 수집을 위해 7일 후 재확인하세요.",
            )

        # 트래픽 분석
        bytes_out = nat.bytes_out_total
        days_with_traffic = nat.days_with_traffic
        metric_days = self.audit_data.metric_period_days

        # 1. 완전 미사용 (14일간 트래픽 0)
        if bytes_out == 0:
            monthly_waste = nat.monthly_fixed_cost
            annual_savings = monthly_waste * 12

            return NATFinding(
                nat=nat,
                usage_status=UsageStatus.UNUSED,
                confidence=Confidence.HIGH,
                severity=Severity.CRITICAL,
                description=f"{metric_days}일간 아웃바운드 트래픽 없음",
                recommendation="삭제를 검토하세요. 사용되지 않는 NAT Gateway입니다.",
                monthly_waste=monthly_waste,
                annual_savings=annual_savings,
                details={
                    "bytes_out_total": 0,
                    "days_checked": metric_days,
                    "days_with_traffic": 0,
                },
            )

        # 2. 저사용 (일평균 < 1GB)
        daily_avg_gb = (bytes_out / (1024**3)) / metric_days

        if daily_avg_gb < self.LOW_USAGE_THRESHOLD_GB_PER_DAY:
            # 트래픽이 있는 날이 적으면 더 의심스러움
            if days_with_traffic <= 2:
                confidence = Confidence.HIGH
                severity = Severity.HIGH
                desc = f"거의 미사용: {days_with_traffic}일만 트래픽 발생"
            else:
                confidence = Confidence.MEDIUM
                severity = Severity.MEDIUM
                desc = f"저사용: 일평균 {daily_avg_gb:.2f} GB"

            # 저사용이면 고정비용의 일부를 낭비로 간주
            # (실제로는 데이터 비용이 거의 없으므로 고정비용 대비 효율이 낮음)
            efficiency = min(daily_avg_gb / self.LOW_USAGE_THRESHOLD_GB_PER_DAY, 1.0)
            monthly_waste = nat.monthly_fixed_cost * (1 - efficiency)
            annual_savings = monthly_waste * 12

            return NATFinding(
                nat=nat,
                usage_status=UsageStatus.LOW_USAGE,
                confidence=confidence,
                severity=severity,
                description=desc,
                recommendation="VPC Endpoint 또는 다른 대안을 검토하세요. NAT Gateway 비용 대비 효율이 낮습니다.",
                monthly_waste=round(monthly_waste, 2),
                annual_savings=round(annual_savings, 2),
                details={
                    "bytes_out_total": bytes_out,
                    "daily_avg_gb": round(daily_avg_gb, 3),
                    "days_with_traffic": days_with_traffic,
                    "days_checked": metric_days,
                },
            )

        # 3. 정상 사용
        return NATFinding(
            nat=nat,
            usage_status=UsageStatus.NORMAL,
            confidence=Confidence.HIGH,
            severity=Severity.INFO,
            description=f"정상 사용 중: 일평균 {daily_avg_gb:.2f} GB",
            recommendation="현재 정상적으로 사용 중입니다.",
            details={
                "bytes_out_total": bytes_out,
                "daily_avg_gb": round(daily_avg_gb, 3),
                "days_with_traffic": days_with_traffic,
                "days_checked": metric_days,
            },
        )

    def get_summary_stats(self) -> dict[str, Any]:
        """계정/리전별 요약 통계를 딕셔너리로 반환한다.

        Returns:
            계정명, 리전, NAT 수, 미사용 수, 비용 정보 등을 포함하는 딕셔너리.
        """
        result = self.analyze()

        return {
            "account_id": self.audit_data.account_id,
            "account_name": self.audit_data.account_name,
            "region": self.audit_data.region,
            "total_nat_count": result.total_nat_count,
            "unused_count": result.unused_count,
            "low_usage_count": result.low_usage_count,
            "normal_count": result.normal_count,
            "pending_count": result.pending_count,
            "total_monthly_cost": round(result.total_monthly_cost, 2),
            "total_monthly_waste": round(result.total_monthly_waste, 2),
            "total_annual_savings": round(result.total_annual_savings, 2),
            "metric_period_days": self.audit_data.metric_period_days,
        }
