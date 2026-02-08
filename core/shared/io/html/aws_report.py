"""AWS 분석 도구용 표준 HTML 리포트

플러그인에서 일관된 형식의 리포트를 쉽게 생성할 수 있도록 하는 래퍼 클래스
Excel의 Workbook/SummarySheet 패턴과 동일한 컨셉
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .report import HTMLReport

if TYPE_CHECKING:
    pass


@dataclass
class ResourceItem:
    """리소스 데이터 표준 구조

    HTML 리포트의 테이블에 표시할 리소스 정보를 표준화된 형태로 저장합니다.
    AWSReport.add_resource()에 전달하여 리포트에 추가합니다.

    Attributes:
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전
        resource_id: 리소스 식별자 (인스턴스 ID, ARN 등)
        resource_name: 리소스 이름 (Name 태그 등)
        resource_type: 리소스 유형 (예: "t3.micro", "gp3")
        status: 리소스 상태 (예: "unused", "running")
        reason: 감지 사유 또는 설명
        cost: 월간 비용 (USD)
        extra: 추가 메타데이터 딕셔너리 (커스텀 컬럼에 매핑)
    """

    account_id: str
    account_name: str
    region: str
    resource_id: str
    resource_name: str = ""
    resource_type: str = ""
    status: str = ""
    reason: str = ""
    cost: float = 0.0
    extra: dict[str, Any] | None = None

    def to_row(self, columns: list[str]) -> list[Any]:
        """지정된 컬럼 순서로 행 데이터 반환

        Args:
            columns: 출력할 컬럼 키 목록 (예: ["account", "region", "resource_id"])

        Returns:
            컬럼 순서에 맞는 값 리스트. extra 딕셔너리 키도 매핑됨.
        """
        mapping = {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account": f"{self.account_name} ({self.account_id})",
            "region": self.region,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "status": self.status,
            "reason": self.reason,
            "cost": f"${self.cost:,.2f}" if self.cost else "-",
        }
        if self.extra:
            mapping.update(self.extra)

        return [mapping.get(col, "") for col in columns]


class AWSReport:
    """AWS 분석 도구용 표준 HTML 리포트

    플러그인에서 일관된 형식으로 리포트를 생성할 수 있는 래퍼 클래스.
    Excel의 Workbook 패턴과 동일하게 사용.

    Example:
        # 기본 사용
        report = AWSReport(
            title="EC2 미사용 리소스",
            service="EC2",
            tool_name="unused",
            ctx=ctx,
        )

        # 요약 정보
        report.set_summary(
            total=150,
            found=23,
            savings=1234.56,
        )

        # 리소스 데이터 추가
        for item in results:
            report.add_resource(ResourceItem(
                account_id=item["account_id"],
                account_name=item["account_name"],
                region=item["region"],
                resource_id=item["instance_id"],
                resource_name=item.get("name", ""),
                status="unused",
                reason=item["reason"],
                cost=item.get("monthly_cost", 0),
            ))

        # 저장 (브라우저 자동 열림)
        report.save(output_path)
    """

    def __init__(
        self,
        title: str,
        service: str,
        tool_name: str,
        ctx: Any | None = None,
        subtitle: str | None = None,
    ):
        """초기화

        Args:
            title: 리포트 제목 (예: "EC2 미사용 리소스 분석")
            service: AWS 서비스명 (예: "EC2", "RDS", "Lambda")
            tool_name: 도구명 (예: "unused", "security_audit")
            ctx: 실행 컨텍스트 (계정/리전 정보 추출용)
            subtitle: 부제목 (없으면 자동 생성)
        """
        self.title = title
        self.service = service
        self.tool_name = tool_name
        self.ctx = ctx
        self.subtitle = subtitle

        # 데이터
        self.resources: list[ResourceItem] = []
        self.summary_data: dict[str, Any] = {}
        self.custom_charts: list[dict[str, Any]] = []
        self.custom_sections: list[dict[str, Any]] = []

        # 실행 정보
        self.execution_info = self._extract_execution_info(ctx)

    def _extract_execution_info(self, ctx: Any | None) -> dict[str, Any]:
        """컨텍스트에서 실행 정보 추출

        Args:
            ctx: 실행 컨텍스트 (None 허용)

        Returns:
            실행 정보 딕셔너리 (timestamp, accounts, regions, profile)
        """
        info: dict[str, Any] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accounts": [],
            "regions": [],
            "profile": None,
        }

        if ctx is None:
            return info

        # 계정 정보
        if hasattr(ctx, "accounts") and ctx.accounts:
            info["accounts"] = [f"{a.name} ({a.id})" for a in ctx.accounts]

        # 리전 정보
        if hasattr(ctx, "regions") and ctx.regions:
            info["regions"] = ctx.regions

        # 프로필
        if hasattr(ctx, "profile_name"):
            info["profile"] = ctx.profile_name

        return info

    def set_summary(
        self,
        total: int,
        found: int,
        savings: float = 0.0,
        custom: dict[str, Any] | None = None,
    ) -> AWSReport:
        """요약 정보 설정

        Args:
            total: 전체 리소스 수
            found: 발견된 리소스 수 (미사용, 위험 등)
            savings: 예상 절감액 (월간)
            custom: 추가 요약 항목 {"라벨": (값, 색상), ...}
        """
        self.summary_data = {
            "total": total,
            "found": found,
            "savings": savings,
            "custom": custom or {},
        }
        return self

    def add_resource(self, item: ResourceItem) -> AWSReport:
        """리소스 추가

        Args:
            item: 추가할 ResourceItem

        Returns:
            self (메서드 체이닝)
        """
        self.resources.append(item)
        return self

    def add_resources(self, items: list[ResourceItem]) -> AWSReport:
        """리소스 일괄 추가

        Args:
            items: 추가할 ResourceItem 리스트

        Returns:
            self (메서드 체이닝)
        """
        self.resources.extend(items)
        return self

    def add_custom_chart(
        self,
        chart_type: str,
        title: str,
        data: Any,
        **kwargs: Any,
    ) -> AWSReport:
        """커스텀 차트 추가

        Args:
            chart_type: "pie", "bar", "line", "gauge", "radar", "treemap", "heatmap", "scatter"
            title: 차트 제목
            data: 차트 데이터 (타입별로 다름)
            **kwargs: 추가 옵션
        """
        self.custom_charts.append({"type": chart_type, "title": title, "data": data, "options": kwargs})
        return self

    def add_custom_section(
        self,
        title: str,
        content_type: str,
        data: Any,
    ) -> AWSReport:
        """커스텀 섹션 추가

        Args:
            title: 섹션 제목
            content_type: "table", "list", "text"
            data: 섹션 데이터
        """
        self.custom_sections.append({"title": title, "type": content_type, "data": data})
        return self

    def save(
        self,
        filepath: str | Path,
        auto_open: bool = True,
        table_columns: list[tuple[str, str]] | None = None,
    ) -> Path:
        """리포트 저장

        Args:
            filepath: 저장 경로
            auto_open: 브라우저 자동 열기
            table_columns: 테이블 컬럼 정의 [(key, header), ...]
                          None이면 기본 컬럼 사용

        Returns:
            저장된 파일 경로
        """
        report = self._build_report(table_columns)
        return report.save(filepath, auto_open=auto_open)

    def _build_report(self, table_columns: list[tuple[str, str]] | None = None) -> HTMLReport:
        """HTMLReport 객체 생성

        요약 카드, 분포 차트, 커스텀 차트, 리소스 테이블, 커스텀 섹션을
        순서대로 조합하여 HTMLReport 인스턴스를 구성합니다.

        Args:
            table_columns: 테이블 컬럼 정의 [(key, header), ...]. None이면 자동 생성.

        Returns:
            완성된 HTMLReport 인스턴스
        """
        subtitle = self.subtitle or self._generate_subtitle()
        report = HTMLReport(self.title, subtitle)

        # 1. 요약 카드
        self._add_summary_section(report)

        # 2. 분포 차트 (자동 생성)
        self._add_distribution_charts(report)

        # 3. 커스텀 차트
        self._add_custom_charts(report)

        # 4. 리소스 테이블
        self._add_resource_table(report, table_columns)

        # 5. 커스텀 섹션
        self._add_custom_sections(report)

        return report

    def _generate_subtitle(self) -> str:
        """부제목 자동 생성

        서비스명, 프로파일, 계정 수, 리전 수를 조합하여 부제목을 생성합니다.

        Returns:
            "EC2 / unused | Profile: my-profile | 3개 계정 | 5개 리전" 형식 문자열
        """
        parts = [f"{self.service} / {self.tool_name}"]

        if self.execution_info["profile"]:
            parts.append(f"Profile: {self.execution_info['profile']}")

        if self.execution_info["accounts"]:
            count = len(self.execution_info["accounts"])
            parts.append(f"{count}개 계정")

        if self.execution_info["regions"]:
            count = len(self.execution_info["regions"])
            parts.append(f"{count}개 리전")

        return " | ".join(parts)

    def _add_summary_section(self, report: HTMLReport) -> None:
        """요약 카드 추가"""
        if not self.summary_data:
            # 기본 요약 (리소스 데이터 기반)
            if self.resources:
                self.summary_data = {
                    "total": len(self.resources),
                    "found": len(self.resources),
                    "savings": sum(r.cost for r in self.resources),
                    "custom": {},
                }
            else:
                return

        items: list[tuple[str, str | int | float, str | None]] = []

        # 기본 항목
        total = self.summary_data.get("total", 0)
        found = self.summary_data.get("found", 0)
        savings = self.summary_data.get("savings", 0)

        items.append(("전체 리소스", total, None))
        items.append(("발견", found, "danger" if found > 0 else None))

        # 비율
        if total > 0:
            ratio = (found / total) * 100
            items.append(("비율", f"{ratio:.1f}%", "warning" if ratio > 10 else None))

        # 절감액
        if savings > 0:
            items.append(("예상 절감 (월)", f"${savings:,.0f}", "success"))

        # 커스텀 항목
        for label, (value, color) in self.summary_data.get("custom", {}).items():
            items.append((label, value, color))

        report.add_summary(items)

    def _add_distribution_charts(self, report: HTMLReport) -> None:
        """분포 차트 자동 생성"""
        if not self.resources:
            return

        # 계정별 분포
        account_counts: dict[str, int] = {}
        for r in self.resources:
            key = r.account_name or r.account_id
            account_counts[key] = account_counts.get(key, 0) + 1

        if len(account_counts) > 1:
            report.add_pie_chart(
                "계정별 분포",
                [(name, count) for name, count in sorted(account_counts.items(), key=lambda x: -x[1])[:10]],
                doughnut=True,
            )

        # 리전별 분포
        region_counts: dict[str, int] = {}
        for r in self.resources:
            region_counts[r.region] = region_counts.get(r.region, 0) + 1

        if len(region_counts) > 1:
            sorted_regions = sorted(region_counts.items(), key=lambda x: -x[1])[:10]
            report.add_bar_chart(
                "리전별 분포",
                [r[0] for r in sorted_regions],
                [("리소스 수", [r[1] for r in sorted_regions])],
            )

        # 상태별 분포 (있는 경우)
        status_counts: dict[str, int] = {}
        for r in self.resources:
            if r.status:
                status_counts[r.status] = status_counts.get(r.status, 0) + 1

        if len(status_counts) > 1:
            report.add_pie_chart(
                "상태별 분포",
                [(status, count) for status, count in sorted(status_counts.items(), key=lambda x: -x[1])],
            )

        # 리소스 타입별 분포 (있는 경우)
        type_counts: dict[str, int] = {}
        for r in self.resources:
            if r.resource_type:
                type_counts[r.resource_type] = type_counts.get(r.resource_type, 0) + 1

        if len(type_counts) > 1:
            sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])[:10]
            report.add_bar_chart(
                "타입별 분포",
                [t[0] for t in sorted_types],
                [("리소스 수", [t[1] for t in sorted_types])],
                horizontal=True,
            )

    def _add_custom_charts(self, report: HTMLReport) -> None:
        """커스텀 차트 추가"""
        for chart in self.custom_charts:
            chart_type = chart["type"]
            title = chart["title"]
            data = chart["data"]
            options = chart["options"]

            if chart_type == "pie":
                report.add_pie_chart(title, data, **options)
            elif chart_type == "bar":
                report.add_bar_chart(title, **data, **options)
            elif chart_type == "line":
                report.add_line_chart(title, **data, **options)
            elif chart_type == "gauge":
                report.add_gauge_chart(title, data, **options)
            elif chart_type == "radar":
                report.add_radar_chart(title, **data, **options)
            elif chart_type == "treemap":
                report.add_treemap_chart(title, data, **options)
            elif chart_type == "heatmap":
                report.add_heatmap_chart(title, **data, **options)
            elif chart_type == "scatter":
                report.add_scatter_chart(title, data, **options)

    def _add_resource_table(
        self,
        report: HTMLReport,
        table_columns: list[tuple[str, str]] | None = None,
    ) -> None:
        """리소스 테이블 추가"""
        if not self.resources:
            return

        # 기본 컬럼
        if table_columns is None:
            table_columns = [
                ("account", "계정"),
                ("region", "리전"),
                ("resource_id", "리소스 ID"),
                ("resource_name", "이름"),
                ("resource_type", "타입"),
                ("status", "상태"),
                ("reason", "사유"),
                ("cost", "비용"),
            ]

            # 불필요한 컬럼 제거 (데이터가 없는 경우)
            table_columns = [
                (key, header)
                for key, header in table_columns
                if any(getattr(r, key, None) or (r.extra and r.extra.get(key)) for r in self.resources)
            ]

        column_keys = [col[0] for col in table_columns]
        headers = [col[1] for col in table_columns]

        rows = [r.to_row(column_keys) for r in self.resources]

        report.add_table(
            f"{self.service} 리소스 상세",
            headers,
            rows,
            sortable=True,
            searchable=True,
            page_size=20,
        )

    def _add_custom_sections(self, report: HTMLReport) -> None:
        """커스텀 섹션 추가"""
        for section in self.custom_sections:
            if section["type"] == "table":
                headers = section["data"].get("headers", [])
                rows = section["data"].get("rows", [])
                report.add_table(section["title"], headers, rows)


# 편의 함수
def create_aws_report(
    title: str,
    service: str,
    tool_name: str,
    ctx: Any = None,
    resources: list[dict[str, Any]] | None = None,
    total: int | None = None,
    found: int | None = None,
    savings: float = 0.0,
) -> AWSReport:
    """AWS 리포트 빠른 생성

    Args:
        title: 리포트 제목
        service: AWS 서비스명
        tool_name: 도구명
        ctx: 실행 컨텍스트
        resources: 리소스 딕셔너리 리스트
        total: 전체 리소스 수
        found: 발견된 리소스 수
        savings: 예상 절감액

    Returns:
        AWSReport 인스턴스
    """
    report = AWSReport(title, service, tool_name, ctx)

    if resources:
        for r in resources:
            item = ResourceItem(
                account_id=r.get("account_id", ""),
                account_name=r.get("account_name", ""),
                region=r.get("region", ""),
                resource_id=r.get("resource_id", r.get("id", "")),
                resource_name=r.get("resource_name", r.get("name", "")),
                resource_type=r.get("resource_type", r.get("type", "")),
                status=r.get("status", ""),
                reason=r.get("reason", ""),
                cost=r.get("cost", r.get("monthly_cost", 0.0)),
                extra={
                    k: v
                    for k, v in r.items()
                    if k
                    not in [
                        "account_id",
                        "account_name",
                        "region",
                        "resource_id",
                        "id",
                        "resource_name",
                        "name",
                        "resource_type",
                        "type",
                        "status",
                        "reason",
                        "cost",
                        "monthly_cost",
                    ]
                },
            )
            report.add_resource(item)

    if total is not None or found is not None:
        report.set_summary(
            total=total or len(resources or []),
            found=found or len(resources or []),
            savings=savings,
        )

    return report
