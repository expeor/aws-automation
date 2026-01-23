"""
plugins/elb/listener_rules.py - ALB Listener Rules Analyzer

ALB 리스너 규칙을 분석하여 복잡도, 우선순위 문제, 최적화 기회를 탐지합니다.

분석 항목:
    - 규칙 복잡도: 조건 수, 액션 타입별 분석
    - 우선순위 문제: 중복/겹치는 규칙, 사용되지 않는 규칙
    - 최적화 기회: 통합 가능한 규칙, 간소화 가능한 조건
    - 베스트 프랙티스: 기본 규칙, 헬스체크 규칙 등

Usage:
    from plugins.elb.listener_rules import run
    run(ctx)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.parallel import get_client
from core.tools.base import BaseToolRunner
from core.tools.io.excel import save_dict_list_to_excel
from core.tools.output import OutputPath

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeRules",
    ],
}


class FindingSeverity(str, Enum):
    """발견 항목 심각도"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategory(str, Enum):
    """발견 항목 카테고리"""

    COMPLEXITY = "복잡도"
    PRIORITY = "우선순위"
    OPTIMIZATION = "최적화"
    BEST_PRACTICE = "베스트 프랙티스"
    PERFORMANCE = "성능"


@dataclass
class RuleFinding:
    """규칙 분석 발견 항목"""

    severity: FindingSeverity
    category: FindingCategory
    title: str
    description: str
    rule_arn: str | None = None
    rule_priority: int | None = None
    recommendation: str = ""


@dataclass
class RuleAnalysis:
    """단일 규칙 분석 결과"""

    rule_arn: str
    priority: int
    conditions: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    is_default: bool = False

    # 분석 결과
    condition_count: int = 0
    action_count: int = 0
    condition_types: list[str] = field(default_factory=list)
    action_types: list[str] = field(default_factory=list)
    complexity_score: float = 0.0

    # 조건 세부 정보
    host_headers: list[str] = field(default_factory=list)
    path_patterns: list[str] = field(default_factory=list)
    http_methods: list[str] = field(default_factory=list)
    source_ips: list[str] = field(default_factory=list)
    query_strings: list[dict] = field(default_factory=list)
    headers: list[dict] = field(default_factory=list)


@dataclass
class ListenerAnalysis:
    """리스너 분석 결과"""

    listener_arn: str
    lb_arn: str
    lb_name: str
    protocol: str
    port: int
    rules: list[RuleAnalysis]
    findings: list[RuleFinding]

    # 통계
    total_rules: int = 0
    default_rule_exists: bool = False
    avg_complexity: float = 0.0
    max_complexity: float = 0.0


# =============================================================================
# 복잡도 가중치
# =============================================================================

# 조건 타입별 복잡도 가중치
CONDITION_COMPLEXITY_WEIGHTS = {
    "host-header": 1.0,
    "path-pattern": 1.5,
    "http-request-method": 0.5,
    "source-ip": 1.0,
    "http-header": 2.0,  # 헤더 조건은 복잡
    "query-string": 2.5,  # 쿼리 스트링은 가장 복잡
}

# 액션 타입별 복잡도 가중치
ACTION_COMPLEXITY_WEIGHTS = {
    "forward": 1.0,
    "redirect": 1.5,
    "fixed-response": 0.5,
    "authenticate-cognito": 3.0,
    "authenticate-oidc": 3.0,
}

# 복잡도 임계값
COMPLEXITY_THRESHOLDS = {
    "low": 3.0,
    "medium": 6.0,
    "high": 10.0,
    "critical": 15.0,
}


class ListenerRulesAnalyzer:
    """ALB Listener Rules 분석기"""

    def __init__(self, elbv2_client):
        self.elbv2 = elbv2_client

    def analyze_load_balancer(self, lb: dict[str, Any]) -> list[ListenerAnalysis]:
        """로드밸런서의 모든 리스너 분석"""
        lb_arn = lb["LoadBalancerArn"]
        lb_name = lb["LoadBalancerName"]
        results: list[ListenerAnalysis] = []

        # 리스너 조회
        try:
            listeners_resp = self.elbv2.describe_listeners(LoadBalancerArn=lb_arn)
            listeners = listeners_resp.get("Listeners", [])
        except Exception:
            return results

        for listener in listeners:
            analysis = self._analyze_listener(listener, lb_name)
            if analysis:
                results.append(analysis)

        return results

    def _analyze_listener(self, listener: dict[str, Any], lb_name: str) -> ListenerAnalysis | None:
        """단일 리스너 분석"""
        listener_arn = listener["ListenerArn"]
        lb_arn = listener["LoadBalancerArn"]
        protocol = listener.get("Protocol", "")
        port = listener.get("Port", 0)

        # 규칙 조회
        try:
            rules_resp = self.elbv2.describe_rules(ListenerArn=listener_arn)
            rules = rules_resp.get("Rules", [])
        except Exception:
            return None

        if not rules:
            return None

        # 규칙 분석
        rule_analyses = []
        for rule in rules:
            analysis = self._analyze_rule(rule)
            rule_analyses.append(analysis)

        # 발견 항목 생성
        findings = self._generate_findings(rule_analyses, listener_arn)

        # 통계 계산
        total_rules = len(rule_analyses)
        default_exists = any(r.is_default for r in rule_analyses)

        complexities = [r.complexity_score for r in rule_analyses if not r.is_default]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0
        max_complexity = max(complexities) if complexities else 0

        return ListenerAnalysis(
            listener_arn=listener_arn,
            lb_arn=lb_arn,
            lb_name=lb_name,
            protocol=protocol,
            port=port,
            rules=rule_analyses,
            findings=findings,
            total_rules=total_rules,
            default_rule_exists=default_exists,
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
        )

    def _analyze_rule(self, rule: dict[str, Any]) -> RuleAnalysis:
        """단일 규칙 분석"""
        rule_arn = rule.get("RuleArn", "")
        priority_str = rule.get("Priority", "default")
        is_default = priority_str == "default"
        priority = 99999 if is_default else int(priority_str)

        conditions = rule.get("Conditions", [])
        actions = rule.get("Actions", [])

        analysis = RuleAnalysis(
            rule_arn=rule_arn,
            priority=priority,
            conditions=conditions,
            actions=actions,
            is_default=is_default,
            condition_count=len(conditions),
            action_count=len(actions),
        )

        # 조건 분석
        self._analyze_conditions(analysis, conditions)

        # 액션 분석
        self._analyze_actions(analysis, actions)

        # 복잡도 계산
        analysis.complexity_score = self._calculate_complexity(analysis)

        return analysis

    def _analyze_conditions(self, analysis: RuleAnalysis, conditions: list[dict]) -> None:
        """조건 세부 분석"""
        for cond in conditions:
            field_type = cond.get("Field", "")
            analysis.condition_types.append(field_type)

            values = cond.get("Values", [])

            if field_type == "host-header":
                host_config = cond.get("HostHeaderConfig", {})
                analysis.host_headers.extend(host_config.get("Values", values))
            elif field_type == "path-pattern":
                path_config = cond.get("PathPatternConfig", {})
                analysis.path_patterns.extend(path_config.get("Values", values))
            elif field_type == "http-request-method":
                method_config = cond.get("HttpRequestMethodConfig", {})
                analysis.http_methods.extend(method_config.get("Values", values))
            elif field_type == "source-ip":
                ip_config = cond.get("SourceIpConfig", {})
                analysis.source_ips.extend(ip_config.get("Values", values))
            elif field_type == "http-header":
                header_config = cond.get("HttpHeaderConfig", {})
                analysis.headers.append(header_config)
            elif field_type == "query-string":
                qs_config = cond.get("QueryStringConfig", {})
                analysis.query_strings.extend(qs_config.get("Values", []))

    def _analyze_actions(self, analysis: RuleAnalysis, actions: list[dict]) -> None:
        """액션 세부 분석"""
        for action in actions:
            action_type = action.get("Type", "")
            analysis.action_types.append(action_type)

    def _calculate_complexity(self, analysis: RuleAnalysis) -> float:
        """규칙 복잡도 점수 계산"""
        if analysis.is_default:
            return 0.0

        score = 0.0

        # 조건 복잡도
        for cond_type in analysis.condition_types:
            weight = CONDITION_COMPLEXITY_WEIGHTS.get(cond_type, 1.0)
            score += weight

        # 다중 값 보정 (값이 많을수록 복잡)
        value_count = (
            len(analysis.host_headers)
            + len(analysis.path_patterns)
            + len(analysis.http_methods)
            + len(analysis.source_ips)
            + len(analysis.query_strings)
            + len(analysis.headers)
        )
        if value_count > 3:
            score += (value_count - 3) * 0.5

        # 액션 복잡도
        for action_type in analysis.action_types:
            weight = ACTION_COMPLEXITY_WEIGHTS.get(action_type, 1.0)
            score += weight

        return round(score, 2)

    def _generate_findings(self, rules: list[RuleAnalysis], listener_arn: str) -> list[RuleFinding]:
        """분석 결과로부터 발견 항목 생성"""
        findings = []

        # 1. 복잡도 분석
        findings.extend(self._check_complexity(rules))

        # 2. 우선순위 분석
        findings.extend(self._check_priority_issues(rules))

        # 3. 최적화 기회 분석
        findings.extend(self._check_optimization_opportunities(rules))

        # 4. 베스트 프랙티스 분석
        findings.extend(self._check_best_practices(rules))

        return findings

    def _check_complexity(self, rules: list[RuleAnalysis]) -> list[RuleFinding]:
        """복잡도 이슈 체크"""
        findings = []

        for rule in rules:
            if rule.is_default:
                continue

            if rule.complexity_score >= COMPLEXITY_THRESHOLDS["critical"]:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.HIGH,
                        category=FindingCategory.COMPLEXITY,
                        title="매우 복잡한 규칙",
                        description=f"규칙 복잡도가 {rule.complexity_score}로 매우 높습니다. "
                        f"조건 {rule.condition_count}개, 액션 {rule.action_count}개",
                        rule_arn=rule.rule_arn,
                        rule_priority=rule.priority,
                        recommendation="규칙을 여러 개로 분리하거나 조건을 단순화하세요.",
                    )
                )
            elif rule.complexity_score >= COMPLEXITY_THRESHOLDS["high"]:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.MEDIUM,
                        category=FindingCategory.COMPLEXITY,
                        title="복잡한 규칙",
                        description=f"규칙 복잡도가 {rule.complexity_score}로 높습니다.",
                        rule_arn=rule.rule_arn,
                        rule_priority=rule.priority,
                        recommendation="가능하면 조건을 단순화하세요.",
                    )
                )

            # 다중 조건 타입 경고
            if len(set(rule.condition_types)) >= 3:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.LOW,
                        category=FindingCategory.COMPLEXITY,
                        title="다중 조건 타입 사용",
                        description=f"규칙에서 {len(set(rule.condition_types))}가지 "
                        f"조건 타입을 사용: {', '.join(set(rule.condition_types))}",
                        rule_arn=rule.rule_arn,
                        rule_priority=rule.priority,
                        recommendation="조건 타입이 많으면 디버깅이 어렵습니다.",
                    )
                )

        return findings

    def _check_priority_issues(self, rules: list[RuleAnalysis]) -> list[RuleFinding]:
        """우선순위 이슈 체크"""
        findings: list[RuleFinding] = []

        # 기본 규칙 제외
        non_default_rules = [r for r in rules if not r.is_default]

        if not non_default_rules:
            return findings

        # 우선순위 간격 분석
        priorities = sorted([r.priority for r in non_default_rules])

        if len(priorities) >= 2:
            gaps = []
            for i in range(1, len(priorities)):
                gap = priorities[i] - priorities[i - 1]
                if gap == 1:
                    gaps.append((priorities[i - 1], priorities[i]))

            if gaps:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.INFO,
                        category=FindingCategory.PRIORITY,
                        title="연속 우선순위 사용",
                        description=f"연속된 우선순위 사용 {len(gaps)}건. 새 규칙 삽입 시 재정렬 필요할 수 있음.",
                        recommendation="우선순위 간격을 10 또는 100 단위로 유지하세요.",
                    )
                )

        # 겹치는 조건 탐지 (동일 호스트/경로)
        host_rules: dict[str, list[RuleAnalysis]] = {}
        path_rules: dict[str, list[RuleAnalysis]] = {}

        for rule in non_default_rules:
            for host in rule.host_headers:
                host_key = host.lower()
                if host_key not in host_rules:
                    host_rules[host_key] = []
                host_rules[host_key].append(rule)

            for path in rule.path_patterns:
                if path not in path_rules:
                    path_rules[path] = []
                path_rules[path].append(rule)

        # 동일 호스트에 여러 규칙
        for host, host_rule_list in host_rules.items():
            if len(host_rule_list) > 3:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.LOW,
                        category=FindingCategory.PRIORITY,
                        title="호스트에 다수 규칙",
                        description=f"호스트 '{host}'에 {len(host_rule_list)}개 규칙이 매핑됨",
                        recommendation="규칙 통합 또는 path 기반 분리를 검토하세요.",
                    )
                )

        return findings

    def _check_optimization_opportunities(self, rules: list[RuleAnalysis]) -> list[RuleFinding]:
        """최적화 기회 탐지"""
        findings = []

        non_default_rules = [r for r in rules if not r.is_default]

        # 동일 액션 규칙 통합 가능성
        action_groups: dict[str, list[RuleAnalysis]] = {}
        for rule in non_default_rules:
            # 액션을 문자열로 변환하여 그룹핑
            action_key = str(sorted([a.get("Type", "") for a in rule.actions]))
            if action_key not in action_groups:
                action_groups[action_key] = []
            action_groups[action_key].append(rule)

        for _action_key, action_rule_list in action_groups.items():
            if len(action_rule_list) >= 5:
                # 동일 타겟으로 가는 규칙이 많으면 통합 검토
                sample_rule = action_rule_list[0]
                target_types = sample_rule.action_types

                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.INFO,
                        category=FindingCategory.OPTIMIZATION,
                        title="규칙 통합 가능",
                        description=f"동일 액션 타입({', '.join(target_types)})을 사용하는 "
                        f"규칙이 {len(action_rule_list)}개 있습니다.",
                        recommendation="조건을 OR로 통합하여 규칙 수를 줄일 수 있습니다.",
                    )
                )

        # 와일드카드 사용 검토
        for rule in non_default_rules:
            exact_paths = [p for p in rule.path_patterns if "*" not in p]
            if len(exact_paths) >= 3:
                findings.append(
                    RuleFinding(
                        severity=FindingSeverity.INFO,
                        category=FindingCategory.OPTIMIZATION,
                        title="와일드카드 사용 검토",
                        description=f"규칙에서 {len(exact_paths)}개의 정확한 경로를 사용. 예: {exact_paths[:2]}",
                        rule_arn=rule.rule_arn,
                        rule_priority=rule.priority,
                        recommendation="공통 패턴이 있다면 /api/* 같은 와일드카드 사용을 검토하세요.",
                    )
                )

        return findings

    def _check_best_practices(self, rules: list[RuleAnalysis]) -> list[RuleFinding]:
        """베스트 프랙티스 체크"""
        findings = []

        # 기본 규칙 존재 여부
        has_default = any(r.is_default for r in rules)
        if not has_default:
            findings.append(
                RuleFinding(
                    severity=FindingSeverity.HIGH,
                    category=FindingCategory.BEST_PRACTICE,
                    title="기본 규칙 없음",
                    description="리스너에 기본(default) 규칙이 없습니다.",
                    recommendation="매칭되지 않는 요청 처리를 위해 기본 규칙을 추가하세요.",
                )
            )

        non_default_rules = [r for r in rules if not r.is_default]

        # 규칙 수 체크
        if len(non_default_rules) > 50:
            findings.append(
                RuleFinding(
                    severity=FindingSeverity.MEDIUM,
                    category=FindingCategory.PERFORMANCE,
                    title="규칙 수 과다",
                    description=f"리스너에 {len(non_default_rules)}개의 규칙이 있습니다. 최대 100개까지 지원.",
                    recommendation="규칙 수가 많으면 평가 시간이 증가합니다. 통합을 검토하세요.",
                )
            )
        elif len(non_default_rules) > 80:
            findings.append(
                RuleFinding(
                    severity=FindingSeverity.HIGH,
                    category=FindingCategory.PERFORMANCE,
                    title="규칙 한도 근접",
                    description=f"리스너에 {len(non_default_rules)}개의 규칙. 한도(100)에 근접.",
                    recommendation="규칙 통합 또는 리스너 분리를 검토하세요.",
                )
            )

        # 인증 액션 체크
        auth_rules = [
            r
            for r in non_default_rules
            if any(a.get("Type") in ("authenticate-cognito", "authenticate-oidc") for a in r.actions)
        ]
        if auth_rules:
            # 인증 후 forward가 없는 규칙 체크
            for rule in auth_rules:
                has_forward = any(a.get("Type") == "forward" for a in rule.actions)
                if not has_forward:
                    findings.append(
                        RuleFinding(
                            severity=FindingSeverity.MEDIUM,
                            category=FindingCategory.BEST_PRACTICE,
                            title="인증 후 forward 없음",
                            description="인증 액션 후 forward 액션이 없습니다.",
                            rule_arn=rule.rule_arn,
                            rule_priority=rule.priority,
                            recommendation="인증 성공 후 타겟으로 forward하는 액션을 추가하세요.",
                        )
                    )

        return findings


class ToolRunner(BaseToolRunner):
    """Listener Rules Analyzer Runner"""

    def get_tools(self) -> dict:
        return {"Listener Rules 분석": self._run_analysis}

    def _run_analysis(self) -> None:
        """분석 실행"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        all_results: list[dict[str, Any]] = []
        all_findings: list[dict[str, Any]] = []

        # 심각도별 카운터
        severity_counts = {s.value: 0 for s in FindingSeverity}

        for account_id, region, session in self.iterate_accounts_and_regions():
            elbv2 = get_client(session, "elbv2")

            try:
                # ALB만 조회
                lbs_resp = elbv2.describe_load_balancers()
                albs = [lb for lb in lbs_resp.get("LoadBalancers", []) if lb.get("Type") == "application"]

                if not albs:
                    continue

                analyzer = ListenerRulesAnalyzer(elbv2)

                for lb in albs:
                    lb_name = lb["LoadBalancerName"]
                    console.print(f"[dim]분석 중: {lb_name} ({region})[/dim]")

                    listener_analyses = analyzer.analyze_load_balancer(lb)

                    for la in listener_analyses:
                        # 결과 저장
                        result_row = {
                            "Account": account_id or "current",
                            "Region": region,
                            "LoadBalancer": la.lb_name,
                            "Protocol": la.protocol,
                            "Port": la.port,
                            "TotalRules": la.total_rules,
                            "AvgComplexity": round(la.avg_complexity, 2),
                            "MaxComplexity": round(la.max_complexity, 2),
                            "FindingsCount": len(la.findings),
                        }
                        all_results.append(result_row)

                        # 발견 항목 저장
                        for finding in la.findings:
                            severity_counts[finding.severity.value] += 1
                            finding_row = {
                                "Account": account_id or "current",
                                "Region": region,
                                "LoadBalancer": la.lb_name,
                                "Port": la.port,
                                "Severity": finding.severity.value,
                                "Category": finding.category.value,
                                "Title": finding.title,
                                "Description": finding.description,
                                "RulePriority": finding.rule_priority or "-",
                                "Recommendation": finding.recommendation,
                            }
                            all_findings.append(finding_row)

            except Exception as e:
                logger.warning(f"오류 ({region}): {e}")
                console.print(f"[red]오류 ({region}): {e}[/red]")

        # 요약 출력
        console.print()

        if not all_results:
            console.print("[yellow]분석할 ALB가 없습니다.[/yellow]")
            return

        # 요약 테이블
        summary_table = Table(title="Listener Rules 분석 요약", show_header=True)
        summary_table.add_column("항목", style="dim")
        summary_table.add_column("값", justify="right")

        summary_table.add_row("분석한 리스너", str(len(all_results)))
        summary_table.add_row("발견 항목", str(len(all_findings)))
        summary_table.add_row("[red]CRITICAL[/red]", str(severity_counts.get("CRITICAL", 0)))
        summary_table.add_row("[red]HIGH[/red]", str(severity_counts.get("HIGH", 0)))
        summary_table.add_row("[yellow]MEDIUM[/yellow]", str(severity_counts.get("MEDIUM", 0)))
        summary_table.add_row("[dim]LOW[/dim]", str(severity_counts.get("LOW", 0)))
        summary_table.add_row("[dim]INFO[/dim]", str(severity_counts.get("INFO", 0)))

        console.print(summary_table)

        # 주요 발견 항목 출력 (HIGH 이상)
        high_findings = [f for f in all_findings if f["Severity"] in ("CRITICAL", "HIGH")]

        if high_findings:
            console.print()
            findings_table = Table(title="주요 발견 항목 (HIGH 이상)", show_header=True)
            findings_table.add_column("LB", style="cyan")
            findings_table.add_column("심각도")
            findings_table.add_column("제목")
            findings_table.add_column("설명", max_width=40)

            for f in high_findings[:10]:
                sev_color = "red" if f["Severity"] == "CRITICAL" else "yellow"
                findings_table.add_row(
                    f["LoadBalancer"],
                    f"[{sev_color}]{f['Severity']}[/{sev_color}]",
                    f["Title"],
                    f["Description"][:40],
                )

            console.print(findings_table)

        # 엑셀 출력
        if all_results and self.ctx:
            # 출력 디렉토리 생성
            output_dir = OutputPath(self.ctx.profile_name or "default").sub("elb", "inventory").with_date().build()

            # 엑셀 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{output_dir}/ALB_Listener_Rules_{timestamp}.xlsx"
            save_dict_list_to_excel(all_results, output_path, sheet_name="Listener_Summary")
            console.print(f"\n[bold green]보고서 저장: {output_path}[/bold green]")


def run(ctx) -> None:
    """Entry point"""
    runner = ToolRunner(ctx=ctx)
    runner._run_analysis()
