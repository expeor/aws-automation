"""
Security Group 분석기

분석 항목:
- SG 미사용 판단 (ENI 기반 + 참조 여부)
- SGR Stale 판단 (참조 SG 존재/미사용 여부)
- 사실 기반 표시 (0.0.0.0/0, ::/0, ALL 포트 등)
- Risk Level 판단 (AWS Trusted Advisor 복합 조건 기반)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set

from .collector import SecurityGroup, SGRule
from .critical_ports import (
    ALL_RISKY_PORTS,
    PORT_INFO,
    WEB_PORTS,
    CriticalPort,
    check_port_range,
    is_risky_port,
    is_web_port,
)


class SGStatus(Enum):
    """Security Group 상태"""

    ACTIVE = "Active"
    UNUSED = "Unused"
    DEFAULT_SG = "Default SG (cannot delete)"


class RuleStatus(Enum):
    """Security Group Rule 상태"""

    ACTIVE = "Active"
    STALE_SG_DELETED = "Stale (referenced SG not found)"
    STALE_SG_UNUSED = "Stale (referenced SG has no ENI)"


@dataclass
class SGAnalysisResult:
    """SG 분석 결과"""

    sg: SecurityGroup
    status: SGStatus
    unused_reasons: List[str]
    action_recommendation: str


@dataclass
class RuleAnalysisResult:
    """Rule 분석 결과"""

    sg_id: str
    sg_name: str
    account_id: str
    account_name: str
    region: str
    rule: SGRule
    status: RuleStatus
    stale_reason: str
    # 사실 기반 표시
    is_open_to_world: bool  # 0.0.0.0/0 or ::/0
    is_wide_cidr: bool  # /24 미만 (넓은 범위)
    cidr_prefix: int  # CIDR prefix 길이 (0-128, -1 if not CIDR)
    is_all_ports: bool  # ALL ports
    is_all_protocols: bool  # ALL protocols
    # Risk Level (AWS Trusted Advisor 복합 조건 기반)
    exposed_critical_ports: List[CriticalPort] = field(default_factory=list)
    risk_level: str = ""  # HIGH / MEDIUM / LOW / ""
    # 추가 위험 요소
    is_egress_all_open: bool = False  # Egress ALL + 0.0.0.0/0 (데이터 유출 위험)
    is_self_all_ports: bool = False  # Self 참조 + ALL 포트 (횡이동 위험)
    is_cross_account: bool = False  # Cross-account SG 참조
    cross_account_id: str = ""  # 참조된 계정 ID
    has_no_description: bool = False  # Description 없음
    hidden_risky_ports: List[CriticalPort] = field(
        default_factory=list
    )  # 넓은 범위에 숨은 위험 포트
    # 추가 경고 메시지
    warnings: List[str] = field(default_factory=list)


class SGAnalyzer:
    """Security Group 분석기"""

    def __init__(self, security_groups: List[SecurityGroup]):
        self.security_groups = security_groups
        self.sg_map: Dict[str, SecurityGroup] = {sg.sg_id: sg for sg in security_groups}

    def analyze(self) -> tuple[List[SGAnalysisResult], List[RuleAnalysisResult]]:
        """전체 분석 실행"""
        sg_results = []
        rule_results = []

        for sg in self.security_groups:
            # SG 분석
            sg_result = self._analyze_sg(sg)
            sg_results.append(sg_result)

            # Rule 분석
            for rule in sg.inbound_rules + sg.outbound_rules:
                rule_result = self._analyze_rule(sg, rule)
                rule_results.append(rule_result)

        return sg_results, rule_results

    def _analyze_sg(self, sg: SecurityGroup) -> SGAnalysisResult:
        """단일 SG 분석"""
        unused_reasons = []
        status = SGStatus.ACTIVE

        # Default SG는 삭제 불가
        if sg.is_default_sg:
            status = SGStatus.DEFAULT_SG
            action = "Default SG - 삭제 불가, 규칙 정리만 가능"
            if sg.is_default_vpc:
                action += " (Default VPC 삭제 시 같이 정리됨)"
            return SGAnalysisResult(
                sg=sg,
                status=status,
                unused_reasons=[],
                action_recommendation=action,
            )

        # ENI 연결 확인
        if sg.eni_count == 0:
            unused_reasons.append("ENI 연결 없음")

        # 다른 SG에서 참조 확인
        if not sg.referenced_by_sgs:
            unused_reasons.append("다른 SG에서 참조되지 않음")

        # 미사용 판단
        if sg.eni_count == 0 and not sg.referenced_by_sgs:
            status = SGStatus.UNUSED

            if sg.is_default_vpc:
                action = "미사용 - Default VPC 삭제 검토 (SG도 같이 정리됨)"
            else:
                action = "미사용 - 삭제 검토"
        else:
            if sg.eni_count > 0:
                action = f"사용 중 (ENI {sg.eni_count}개 연결)"
            else:
                refs = ", ".join(list(sg.referenced_by_sgs)[:3])
                action = f"다른 SG에서 참조됨 ({refs})"

        return SGAnalysisResult(
            sg=sg,
            status=status,
            unused_reasons=unused_reasons,
            action_recommendation=action,
        )

    def _analyze_rule(self, sg: SecurityGroup, rule: SGRule) -> RuleAnalysisResult:
        """단일 Rule 분석"""
        status = RuleStatus.ACTIVE
        stale_reason = ""
        warnings: List[str] = []

        # SG 참조 규칙인 경우 Stale 체크
        if rule.source_dest_type == "sg" and rule.referenced_sg_id:
            ref_sg_id = rule.referenced_sg_id

            if ref_sg_id not in self.sg_map:
                # 참조하는 SG가 존재하지 않음
                status = RuleStatus.STALE_SG_DELETED
                stale_reason = f"참조된 SG {ref_sg_id}가 존재하지 않음"
            else:
                ref_sg = self.sg_map[ref_sg_id]
                if ref_sg.eni_count == 0 and not ref_sg.is_default_sg:
                    # 참조하는 SG가 미사용
                    status = RuleStatus.STALE_SG_UNUSED
                    stale_reason = f"참조된 SG {ref_sg_id}에 ENI 연결 없음"

        # 사실 기반 표시
        is_open_to_world = rule.source_dest in ("0.0.0.0/0", "::/0")
        is_all_ports = rule.port_range == "ALL"
        is_all_protocols = rule.protocol == "ALL"

        # CIDR prefix 분석
        cidr_prefix = self._get_cidr_prefix(rule.source_dest)
        is_wide_cidr = cidr_prefix != -1 and cidr_prefix < 24

        # Risk Level 분석 (인바운드 + 넓은 범위인 경우만)
        exposed_critical_ports: List[CriticalPort] = []
        risk_level = ""

        # 인바운드 + (0.0.0.0/0 또는 넓은 CIDR)인 경우 위험도 평가
        if rule.direction == "inbound" and (is_open_to_world or is_wide_cidr):
            risk_level, exposed_critical_ports = self._evaluate_risk_level(
                rule, is_open_to_world, is_wide_cidr
            )

        # === 추가 위험 요소 분석 ===

        # 1. Egress ALL + 0.0.0.0/0 → 데이터 유출 위험
        is_egress_all_open = (
            rule.direction == "outbound"
            and is_open_to_world
            and (is_all_ports or is_all_protocols)
        )
        if is_egress_all_open:
            warnings.append("Egress ALL 허용 - 데이터 유출 통제 불가")

        # 2. Self 참조 + ALL 포트 → 횡이동 위험
        is_self_all_ports = rule.is_self_reference and (
            is_all_ports or is_all_protocols
        )
        if is_self_all_ports:
            warnings.append("Self 참조 ALL 포트 - 같은 SG 내 횡이동 가능")

        # 3. Cross-account 참조
        is_cross_account = rule.is_cross_account
        cross_account_id = rule.referenced_account_id or ""
        if is_cross_account:
            warnings.append(f"Cross-account 참조 ({cross_account_id}) - 외부 계정 의존")

        # 4. Description 없음
        has_no_description = not rule.description or rule.description.strip() == ""

        # 5. 넓은 포트 범위 내 숨겨진 위험 포트 탐지
        hidden_risky_ports = self._get_hidden_risky_ports(rule)
        if hidden_risky_ports and is_open_to_world:
            port_names = ", ".join([p.name for p in hidden_risky_ports[:3]])
            warnings.append(f"넓은 범위에 위험 포트 포함: {port_names}")
            # hidden risky ports가 있으면 risk_level 업그레이드
            if not risk_level or risk_level == "MEDIUM":
                risk_level = "HIGH"
                exposed_critical_ports = hidden_risky_ports

        return RuleAnalysisResult(
            sg_id=sg.sg_id,
            sg_name=sg.sg_name,
            account_id=sg.account_id,
            account_name=sg.account_name,
            region=sg.region,
            rule=rule,
            status=status,
            stale_reason=stale_reason,
            is_open_to_world=is_open_to_world,
            is_wide_cidr=is_wide_cidr,
            cidr_prefix=cidr_prefix,
            is_all_ports=is_all_ports,
            is_all_protocols=is_all_protocols,
            exposed_critical_ports=exposed_critical_ports,
            risk_level=risk_level,
            is_egress_all_open=is_egress_all_open,
            is_self_all_ports=is_self_all_ports,
            is_cross_account=is_cross_account,
            cross_account_id=cross_account_id,
            has_no_description=has_no_description,
            hidden_risky_ports=hidden_risky_ports,
            warnings=warnings,
        )

    def _evaluate_risk_level(
        self, rule: SGRule, is_open_to_world: bool, is_wide_cidr: bool
    ) -> tuple[str, List[CriticalPort]]:
        """
        AWS Trusted Advisor 복합 조건 기반 Risk Level 평가

        HIGH: 위험 포트 + (0.0.0.0/0 OR 넓은 CIDR)
        MEDIUM: 일반 포트 + (0.0.0.0/0 OR 넓은 CIDR) - 웹 포트 제외
        LOW: 웹 포트 + 0.0.0.0/0 (일반적으로 허용, 참고용)
        """
        # 규칙에서 노출되는 포트 범위 분석
        exposed_risky_ports = self._get_exposed_risky_ports(rule)
        exposed_web_only = self._is_web_ports_only(rule)

        # HIGH: 위험 포트가 노출된 경우
        if exposed_risky_ports:
            return "HIGH", exposed_risky_ports

        # ALL 포트/프로토콜인 경우 모든 위험 포트 노출로 판단 → HIGH
        if rule.port_range == "ALL" or rule.protocol == "ALL":
            all_risky = [PORT_INFO[p] for p in ALL_RISKY_PORTS if p in PORT_INFO]
            return "HIGH", all_risky

        # LOW: 웹 포트만 노출된 경우 (0.0.0.0/0인 경우만)
        if exposed_web_only and is_open_to_world:
            web_ports_exposed = self._get_exposed_web_ports(rule)
            return "LOW", web_ports_exposed

        # MEDIUM: 그 외 포트가 0.0.0.0/0 또는 넓은 CIDR에 노출된 경우
        # (웹 포트가 아니고 위험 포트도 아닌 일반 포트)
        if is_open_to_world or is_wide_cidr:
            return "MEDIUM", []

        return "", []

    def _get_exposed_risky_ports(self, rule: SGRule) -> List[CriticalPort]:
        """규칙에서 노출된 위험 포트 조회 (Trusted Advisor RED + 추가 위험 포트)"""
        # ALL 포트인 경우 모든 위험 포트 노출
        if rule.port_range == "ALL":
            return [PORT_INFO[p] for p in ALL_RISKY_PORTS if p in PORT_INFO]

        # 단일 포트
        if "-" not in rule.port_range:
            try:
                port = int(rule.port_range)
                if is_risky_port(port) and port in PORT_INFO:
                    return [PORT_INFO[port]]
            except ValueError:
                pass
            return []

        # 포트 범위
        try:
            parts = rule.port_range.split("-")
            from_port = int(parts[0])
            to_port = int(parts[1])
            return check_port_range(from_port, to_port)
        except (ValueError, IndexError):
            return []

    def _get_exposed_web_ports(self, rule: SGRule) -> List[CriticalPort]:
        """규칙에서 노출된 웹 포트 조회"""
        result = []

        # ALL 포트인 경우 모든 웹 포트
        if rule.port_range == "ALL":
            return [PORT_INFO[p] for p in WEB_PORTS if p in PORT_INFO]

        # 단일 포트
        if "-" not in rule.port_range:
            try:
                port = int(rule.port_range)
                if is_web_port(port) and port in PORT_INFO:
                    return [PORT_INFO[port]]
            except ValueError:
                pass
            return []

        # 포트 범위
        try:
            parts = rule.port_range.split("-")
            from_port = int(parts[0])
            to_port = int(parts[1])
            for port in WEB_PORTS:
                if from_port <= port <= to_port and port in PORT_INFO:
                    result.append(PORT_INFO[port])
            return result
        except (ValueError, IndexError):
            return []

    def _is_web_ports_only(self, rule: SGRule) -> bool:
        """규칙이 웹 포트만 노출하는지 확인"""
        # ALL 포트인 경우 웹 포트만이 아님
        if rule.port_range == "ALL":
            return False

        # 단일 포트
        if "-" not in rule.port_range:
            try:
                port = int(rule.port_range)
                return is_web_port(port)
            except ValueError:
                return False

        # 포트 범위 - 범위 내 모든 포트가 웹 포트인지 확인
        try:
            parts = rule.port_range.split("-")
            from_port = int(parts[0])
            to_port = int(parts[1])

            # 범위가 웹 포트 집합에 완전히 포함되는지
            # (실제로는 범위가 넓으면 웹 포트만이 아님)
            range_ports = set(range(from_port, to_port + 1))
            return range_ports.issubset(WEB_PORTS)
        except (ValueError, IndexError):
            return False

    def _get_hidden_risky_ports(self, rule: SGRule) -> List[CriticalPort]:
        """
        넓은 포트 범위 내 숨겨진 위험 포트 탐지

        예: 1024-65535 범위에는 MySQL(3306), Redis(6379) 등이 포함됨
        단, ALL 포트나 좁은 범위(10개 미만)는 제외
        """
        # ALL 포트는 이미 별도 처리됨
        if rule.port_range in ("ALL", "N/A"):
            return []

        # 단일 포트는 숨겨진 게 아님
        if "-" not in rule.port_range:
            return []

        try:
            parts = rule.port_range.split("-")
            from_port = int(parts[0])
            to_port = int(parts[1])

            # 10개 미만 범위는 "숨겨진" 게 아님 (명시적)
            if to_port - from_port < 10:
                return []

            # 범위 내 위험 포트 찾기
            return check_port_range(from_port, to_port)

        except (ValueError, IndexError):
            return []

    def _get_cidr_prefix(self, source_dest: str) -> int:
        """CIDR prefix 길이 추출 (CIDR이 아니면 -1)"""
        if "/" not in source_dest:
            return -1
        try:
            prefix = int(source_dest.split("/")[1])
            return prefix
        except (ValueError, IndexError):
            return -1

    def get_summary(
        self, sg_results: List[SGAnalysisResult]
    ) -> Dict[str, Dict[str, Any]]:
        """계정/리전별 요약 통계"""
        summary: Dict[str, Dict[str, Any]] = {}

        for result in sg_results:
            sg = result.sg
            key = f"{sg.account_id}/{sg.region}"

            if key not in summary:
                summary[key] = {
                    "account_id": sg.account_id,
                    "account_name": sg.account_name,
                    "region": sg.region,
                    "total": 0,
                    "active": 0,
                    "unused": 0,
                    "default_sg": 0,
                    "in_default_vpc": 0,
                }

            summary[key]["total"] += 1

            if result.status == SGStatus.ACTIVE:
                summary[key]["active"] += 1
            elif result.status == SGStatus.UNUSED:
                summary[key]["unused"] += 1
            elif result.status == SGStatus.DEFAULT_SG:
                summary[key]["default_sg"] += 1

            if sg.is_default_vpc:
                summary[key]["in_default_vpc"] += 1

        return summary
