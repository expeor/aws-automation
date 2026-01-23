"""HTML 리포트 출력 모듈

ECharts 기반 시각화 + 테이블을 단일 HTML 파일로 생성

사용법:
    # 저수준 API (커스텀 리포트)
    from core.tools.io.html import HTMLReport

    report = HTMLReport("리포트 제목")
    report.add_pie_chart("분포", [("A", 10), ("B", 20)])
    report.add_table("데이터", ["col1", "col2"], [["a", "b"]])
    report.save("output.html")

    # 고수준 API (AWS 분석 도구용 - 권장)
    from core.tools.io.html import AWSReport, ResourceItem

    report = AWSReport("EC2 미사용 분석", "EC2", "unused", ctx)
    report.set_summary(total=100, found=10, savings=500)
    report.add_resource(ResourceItem(...))
    report.save("output.html")

    # 더 간단하게
    from core.tools.io.html import create_aws_report

    report = create_aws_report(
        title="EC2 미사용",
        service="EC2",
        tool_name="unused",
        ctx=ctx,
        resources=results,  # list[dict]
    )
    report.save("output.html")
"""

from .aws_report import AWSReport, ResourceItem, create_aws_report
from .report import (
    DEFAULT_TOP_N,
    ChartSize,
    HTMLReport,
    aggregate_by_group,
    build_treemap_hierarchy,
    group_top_n,
    open_in_browser,
)

__all__ = [
    # 저수준 API
    "HTMLReport",
    "ChartSize",
    "open_in_browser",
    # 고수준 API (AWS 리포트)
    "AWSReport",
    "ResourceItem",
    "create_aws_report",
    # 대용량 데이터 헬퍼
    "group_top_n",
    "aggregate_by_group",
    "build_treemap_hierarchy",
    "DEFAULT_TOP_N",
]
