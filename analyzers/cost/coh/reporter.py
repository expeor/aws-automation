"""
plugins/cost/coh/reporter.py - Cost Optimization Hub 리포트 생성기

수집된 권장사항을 Excel 형식으로 출력합니다.
프로젝트의 shared.io.excel 모듈을 사용합니다.

사용법:
    from analyzers.cost.coh.reporter import CostOptimizationReporter

    reporter = CostOptimizationReporter(collection_result)
    reporter.generate_report(output_dir, "cost_optimization")
    reporter.print_summary()
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.io.excel import ColumnDef, Styles, Workbook

from .analyzer import Recommendation
from .collector import CollectionResult

logger = logging.getLogger(__name__)


# 리포트 컬럼 정의
COLUMNS_RECOMMENDATIONS = [
    ColumnDef(header="Account ID", width=14, style="text"),
    ColumnDef(header="Account Name", width=20, style="data"),
    ColumnDef(header="Region", width=15, style="center"),
    ColumnDef(header="Resource ID", width=25, style="data"),
    ColumnDef(header="Resource Name", width=25, style="data"),
    ColumnDef(header="Resource Type", width=18, style="center"),
    ColumnDef(header="Action", width=15, style="center"),
    ColumnDef(header="Current", width=20, style="data"),
    ColumnDef(header="Recommended", width=20, style="data"),
    ColumnDef(header="Monthly Cost", width=12, style="currency"),
    ColumnDef(header="Monthly Savings", width=14, style="currency"),
    ColumnDef(header="Savings %", width=10, style="percent"),
    ColumnDef(header="Effort", width=10, style="center"),
    ColumnDef(header="Restart", width=8, style="center"),
    ColumnDef(header="Rollback", width=8, style="center"),
    ColumnDef(header="Tag:Service", width=15, style="data"),
    ColumnDef(header="Tag:Environment", width=12, style="data"),
]


class CostOptimizationReporter:
    """Cost Optimization Hub 리포트 생성기

    수집된 권장사항을 Excel 형식으로 출력합니다.
    프로젝트의 Workbook 클래스를 사용합니다.
    """

    def __init__(
        self,
        result: CollectionResult,
        account_names: dict[str, str] | None = None,
    ):
        """초기화

        Args:
            result: CollectionResult 객체
            account_names: 계정 ID → 이름 매핑 (optional)
        """
        self.result = result
        self.account_names = account_names or {}

    def generate_report(
        self,
        output_dir: str,
        file_prefix: str = "cost_optimization_hub",
        include_summary: bool = True,
    ) -> Path:
        """Excel 리포트 생성

        Args:
            output_dir: 출력 디렉토리
            file_prefix: 파일명 접두사
            include_summary: 요약 시트 포함 여부

        Returns:
            생성된 파일 경로
        """
        wb = Workbook()

        # 요약 시트 (맨 앞에)
        if include_summary:
            self._create_summary_sheet(wb)

        # 권장사항 유형별 시트
        self._create_recommendations_sheets(wb)

        # 파일 저장
        output_path = wb.save_as(
            output_dir=output_dir,
            prefix=file_prefix,
        )

        logger.info(f"리포트 생성됨: {output_path}")
        return output_path

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """분석 요약 시트 생성"""
        summary = wb.new_summary_sheet("분석 요약")

        summary.add_title("AWS Cost Optimization Hub 분석 결과")

        # ===== 절약 가능액 =====
        summary.add_section("절약 가능액")

        annual_savings = self.result.total_savings * 12
        summary.add_item(
            "연간 절약 가능액",
            f"${annual_savings:,.0f}",
            highlight="success" if annual_savings > 0 else None,
        )
        summary.add_item("월간 절약 가능액", f"${self.result.total_savings:,.2f}")

        if self.result.total_cost > 0:
            savings_pct = (self.result.total_savings / self.result.total_cost) * 100
            summary.add_item("절약 비율", f"{savings_pct:.1f}%")

        summary.add_item("최적화 기회", f"{self.result.filtered_count:,}건")

        summary.add_blank_row()

        # ===== 조치 유형별 =====
        summary.add_section("조치 유형별 절약액")

        # 액션 타입 정보 (이름, 난이도/위험도)
        action_info = {
            "Stop": ("유휴 리소스 중지", "쉬움"),
            "Delete": ("미사용 리소스 삭제", "쉬움"),
            "Rightsize": ("리소스 크기 조정", "중간"),
            "PurchaseSavingsPlans": ("Savings Plans 구매", "쉬움"),
            "PurchaseReservedInstances": ("Reserved Instances 구매", "쉬움"),
            "Upgrade": ("세대 업그레이드", "중간"),
            "MigrateToGraviton": ("Graviton 마이그레이션", "어려움"),
            "ScaleIn": ("스케일 축소", "중간"),
        }

        # 절약액 순으로 정렬
        sorted_actions = sorted(
            self.result.summary_by_action.items(),
            key=lambda x: x[1]["savings"],
            reverse=True,
        )

        for action_type, data in sorted_actions:
            action_name, difficulty = action_info.get(action_type, (action_type, "중간"))
            summary.add_item(
                f"{action_name} [{difficulty}]",
                f"{data['count']:,}건, 월 ${data['savings']:,.0f}",
            )

        summary.add_blank_row()

        # ===== 구현 난이도별 =====
        summary.add_section("구현 난이도별 절약액")

        effort_groups: dict[str, list[Recommendation]] = {"쉬움": [], "중간": [], "어려움": []}
        effort_map = {
            "VeryLow": "쉬움",
            "Low": "쉬움",
            "Medium": "중간",
            "High": "어려움",
            "VeryHigh": "어려움",
        }

        for rec in self.result.recommendations:
            effort_level = effort_map.get(rec.implementation_effort, "중간")
            effort_groups[effort_level].append(rec)

        for level, recs in effort_groups.items():
            if recs:
                total = sum(r.estimated_monthly_savings for r in recs)
                highlight = "success" if level == "쉬움" and total > 0 else None
                summary.add_item(
                    f"{level} ({len(recs)}건)",
                    f"월 ${total:,.0f}",
                    highlight=highlight,
                )

        summary.add_blank_row()

        # ===== 서비스별 Top 5 =====
        summary.add_section("서비스별 절약액 (Top 5)")

        sorted_resources = sorted(
            self.result.summary_by_resource.items(),
            key=lambda x: x[1]["savings"],
            reverse=True,
        )[:5]

        for res_type, data in sorted_resources:
            summary.add_item(
                self._get_service_display_name(res_type),
                f"{data['count']:,}건, 월 ${data['savings']:,.0f}",
            )

        summary.add_blank_row()

        # ===== 리포트 정보 =====
        summary.add_section("리포트 정보")
        summary.add_item("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        summary.add_item("분석 대상", f"{self.result.total_count:,}건")
        summary.add_item("제외 계정", f"{len(self.result.excluded_accounts):,}개")
        summary.add_item("데이터 소스", "AWS Cost Optimization Hub")

    def _get_service_display_name(self, resource_type: str) -> str:
        """리소스 타입을 읽기 쉬운 서비스 이름으로 변환"""
        name_map = {
            "Ec2Instance": "EC2 인스턴스",
            "Ec2AutoScalingGroup": "EC2 Auto Scaling",
            "EbsVolume": "EBS 볼륨",
            "EcsService": "ECS 서비스",
            "LambdaFunction": "Lambda 함수",
            "RdsDbInstance": "RDS 인스턴스",
            "RdsDbInstanceStorage": "RDS 스토리지",
            "AuroraDbClusterStorage": "Aurora 스토리지",
            "ComputeSavingsPlans": "Compute Savings Plans",
            "Ec2InstanceSavingsPlans": "EC2 Savings Plans",
            "SageMakerSavingsPlans": "SageMaker Savings Plans",
            "Ec2ReservedInstances": "EC2 Reserved Instances",
            "RdsReservedInstances": "RDS Reserved Instances",
            "RedshiftReservedNodes": "Redshift Reserved Nodes",
            "OpenSearchReservedInstances": "OpenSearch Reserved",
            "ElastiCacheReservedNodes": "ElastiCache Reserved",
            "MemoryDbReservedInstances": "MemoryDB Reserved",
            "DynamoDbReservedCapacity": "DynamoDB Reserved",
        }
        return name_map.get(resource_type, resource_type)

    def _create_recommendations_sheets(self, wb: Workbook) -> None:
        """권장사항 시트 생성 (액션 타입별)"""
        grouped = self.result.get_by_action_type()

        # 액션 타입별로 시트 생성
        for action_type, recommendations in sorted(grouped.items()):
            sheet_name = self._get_sheet_name(action_type)
            sheet = wb.new_sheet(name=sheet_name, columns=COLUMNS_RECOMMENDATIONS)

            for rec in sorted(
                recommendations,
                key=lambda r: r.estimated_monthly_savings,
                reverse=True,
            ):
                row = self._recommendation_to_row(rec)
                style = self._get_row_style(rec)
                sheet.add_row(row, style=style)

            # 요약 행
            total_cost = sum(r.estimated_monthly_cost for r in recommendations)
            total_savings = sum(r.estimated_monthly_savings for r in recommendations)
            avg_savings_pct = (total_savings / total_cost * 100) if total_cost > 0 else 0

            sheet.add_summary_row(
                [
                    "합계",
                    "",
                    "",
                    f"{len(recommendations)}개",
                    "",
                    "",
                    "",
                    "",
                    "",
                    total_cost,
                    total_savings,
                    avg_savings_pct / 100,
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

        # 전체 권장사항 시트 (모든 타입 포함)
        if len(grouped) > 1:
            all_sheet = wb.new_sheet(name="All Recommendations", columns=COLUMNS_RECOMMENDATIONS)

            for rec in sorted(
                self.result.recommendations,
                key=lambda r: r.estimated_monthly_savings,
                reverse=True,
            ):
                row = self._recommendation_to_row(rec)
                style = self._get_row_style(rec)
                all_sheet.add_row(row, style=style)

            all_sheet.add_summary_row(
                [
                    "합계",
                    "",
                    "",
                    f"{self.result.filtered_count}개",
                    "",
                    "",
                    "",
                    "",
                    "",
                    self.result.total_cost,
                    self.result.total_savings,
                    (self.result.total_savings / self.result.total_cost) if self.result.total_cost > 0 else 0,
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

    def _recommendation_to_row(self, rec: Recommendation) -> list[Any]:
        """Recommendation을 행 데이터로 변환"""
        resource_name = rec.tags.get("Name", rec.resource_id)
        account_name = self.account_names.get(rec.account_id, "")

        return [
            rec.account_id,
            account_name,
            rec.region,
            rec.resource_id,
            resource_name,
            rec.current_resource_type,
            rec.action_type,
            rec.current_resource_summary,
            rec.recommended_resource_summary,
            rec.estimated_monthly_cost,
            rec.estimated_monthly_savings,
            rec.estimated_savings_percentage / 100,  # percent 형식
            rec.implementation_effort,
            "Yes" if rec.restart_needed else "No",
            "Yes" if rec.rollback_possible else "No",
            rec.tags.get("Service", ""),
            rec.tags.get("Environment", ""),
        ]

    def _get_row_style(self, rec: Recommendation) -> dict | None:
        """권장사항에 따른 행 스타일 결정"""
        # 높은 절약액 강조
        if rec.estimated_monthly_savings >= 100:
            return Styles.success()
        # 높은 구현 난이도 경고
        if rec.implementation_effort in ["High", "VeryHigh"]:
            return Styles.warning()
        return None

    def _get_sheet_name(self, action_type: str) -> str:
        """액션 타입을 시트 이름으로 변환"""
        name_map = {
            "Rightsize": "Rightsizing",
            "Stop": "Stop (Idle)",
            "Delete": "Delete (Unused)",
            "ScaleIn": "Scale In",
            "Upgrade": "Upgrade",
            "PurchaseSavingsPlans": "Savings Plans",
            "PurchaseReservedInstances": "Reserved Instances",
            "MigrateToGraviton": "Graviton Migration",
        }
        return name_map.get(action_type, action_type)

    def print_summary(self) -> None:
        """콘솔에 요약 정보 출력"""
        try:
            from rich.console import Console

            console = Console()
            self._print_rich_summary(console)
        except ImportError:
            self._print_plain_summary()

    def _print_rich_summary(self, console) -> None:
        """Rich 라이브러리를 사용한 요약 출력"""
        from rich.table import Table

        console.print("\n[bold cyan]Cost Optimization Hub 권장사항 요약[/bold cyan]")
        console.print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"전체 권장사항: {self.result.total_count:,}개 → 필터링 후: {self.result.filtered_count:,}개")
        console.print(f"제외된 계정: {len(self.result.excluded_accounts):,}개")
        console.print()

        # 액션 타입별 요약
        table = Table(title="액션 타입별 요약")
        table.add_column("액션 타입", style="cyan")
        table.add_column("개수", justify="right", style="green")
        table.add_column("예상 월간 비용", justify="right")
        table.add_column("예상 월간 절약액", justify="right", style="yellow")

        for action_type, data in sorted(
            self.result.summary_by_action.items(),
            key=lambda x: x[1]["savings"],
            reverse=True,
        ):
            table.add_row(
                action_type,
                f"{data['count']:,}",
                f"${data['cost']:,.2f}",
                f"${data['savings']:,.2f}",
            )

        table.add_row(
            "[bold]합계[/bold]",
            f"[bold]{self.result.filtered_count:,}[/bold]",
            f"[bold]${self.result.total_cost:,.2f}[/bold]",
            f"[bold]${self.result.total_savings:,.2f}[/bold]",
        )

        console.print(table)

        # 리소스 타입별 요약
        console.print()
        res_table = Table(title="리소스 타입별 요약")
        res_table.add_column("리소스 타입", style="cyan")
        res_table.add_column("개수", justify="right", style="green")
        res_table.add_column("예상 월간 절약액", justify="right", style="yellow")

        for res_type, data in sorted(
            self.result.summary_by_resource.items(),
            key=lambda x: x[1]["savings"],
            reverse=True,
        )[:10]:  # 상위 10개만
            res_table.add_row(
                res_type,
                f"{data['count']:,}",
                f"${data['savings']:,.2f}",
            )

        console.print(res_table)

    def _print_plain_summary(self) -> None:
        """일반 텍스트 요약 출력"""
        print("\n=== Cost Optimization Hub 권장사항 요약 ===")
        print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"전체 권장사항: {self.result.total_count:,}개 → 필터링 후: {self.result.filtered_count:,}개")
        print(f"제외된 계정: {len(self.result.excluded_accounts):,}개")
        print()

        print("액션 타입별 요약:")
        print("-" * 60)
        for action_type, data in sorted(
            self.result.summary_by_action.items(),
            key=lambda x: x[1]["savings"],
            reverse=True,
        ):
            print(f"  {action_type}: {data['count']:,}개, 절약액 ${data['savings']:,.2f}")
        print("-" * 60)
        print(f"  합계: {self.result.filtered_count:,}개, 총 절약액 ${self.result.total_savings:,.2f}")


def generate_report(
    result: CollectionResult,
    output_dir: str,
    file_prefix: str = "cost_optimization_hub",
    account_names: dict[str, str] | None = None,
) -> Path:
    """리포트 파일 생성 (편의 함수)

    Args:
        result: CollectionResult 객체
        output_dir: 출력 디렉토리
        file_prefix: 파일명 접두사
        account_names: 계정 ID → 이름 매핑

    Returns:
        생성된 파일 경로
    """
    reporter = CostOptimizationReporter(result, account_names)
    return reporter.generate_report(output_dir, file_prefix)
