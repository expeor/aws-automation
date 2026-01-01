"""
NAT Gateway 분석기

분석 항목:
1. 미사용 NAT Gateway 탐지 (14일간 트래픽 0)
2. 저사용 NAT Gateway 탐지 (일평균 트래픽 < 1GB)
3. 비용 최적화 기회 식별
4. 신뢰도 분류 (확실히 미사용 / 아마 미사용 / 검토 필요)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .collector import NATGateway, NATAuditData


class UsageStatus(Enum):
    """사용 상태"""

    UNUSED = "unused"           # 확실히 미사용 (트래픽 0)
    LOW_USAGE = "low_usage"     # 저사용 (일평균 < 1GB)
    NORMAL = "normal"           # 정상 사용
    PENDING = "pending"         # 생성 중/보류 중
    UNKNOWN = "unknown"         # 메트릭 없음


class Confidence(Enum):
    """판단 신뢰도"""

    HIGH = "high"       # 확실함 - 바로 조치 가능
    MEDIUM = "medium"   # 검토 필요
    LOW = "low"         # 판단 불가


class Severity(Enum):
    """심각도"""

    CRITICAL = "critical"  # 즉시 조치 (미사용 + 고비용)
    HIGH = "high"          # 빠른 조치 권장
    MEDIUM = "medium"      # 검토 필요
    LOW = "low"            # 참고
    INFO = "info"          # 정보성


@dataclass
class NATFinding:
    """NAT Gateway 분석 결과"""

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
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NATAnalysisResult:
    """전체 분석 결과"""

    audit_data: NATAuditData
    findings: List[NATFinding] = field(default_factory=list)

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
    """NAT Gateway 분석기"""

    # 저사용 기준: 일평균 1GB 미만
    LOW_USAGE_THRESHOLD_GB_PER_DAY = 1.0

    # 최소 생성 일수 (이보다 젊으면 PENDING)
    MIN_AGE_DAYS = 7

    def __init__(self, audit_data: NATAuditData):
        self.audit_data = audit_data

    def analyze(self) -> NATAnalysisResult:
        """전체 분석 수행"""
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
        """개별 NAT Gateway 분석"""

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
        daily_avg_gb = (bytes_out / (1024 ** 3)) / metric_days

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

    def get_summary_stats(self) -> Dict[str, Any]:
        """요약 통계 반환"""
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
