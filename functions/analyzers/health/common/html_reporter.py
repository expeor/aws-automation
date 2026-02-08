"""
plugins/health/html_reporter.py - AWS Health 대시보드 HTML 리포터

AWS Health 이벤트를 CloudScape UI 스타일의 HTML 대시보드로 생성합니다.
- 요약 카드: 긴급도별 현황
- 서비스별 분포 차트
- 월별 캘린더 뷰
- 이벤트 상세 테이블

사용법:
    from functions.analyzers.health.html_reporter import HealthDashboard

    dashboard = HealthDashboard(result)
    dashboard.generate("output/health_dashboard.html")
"""

from __future__ import annotations

import json
import logging
from calendar import monthcalendar
from datetime import datetime
from pathlib import Path
from typing import Any

from .collector import CollectionResult, PatchItem

logger = logging.getLogger(__name__)

# CloudScape UI 색상
COLORS = {
    "primary": "#0972d3",
    "success": "#037f0c",
    "warning": "#8d6605",
    "danger": "#d91515",
    "info": "#006ce0",
    "neutral": "#414d5c",
    "critical_bg": "#fff1f0",
    "critical_border": "#d91515",
    "high_bg": "#fffae6",
    "high_border": "#8d6605",
    "medium_bg": "#f2f8fd",
    "medium_border": "#0972d3",
    "low_bg": "#f4f4f4",
    "low_border": "#7d8998",
}


class HealthDashboard:
    """AWS Health 대시보드 HTML 생성기"""

    def __init__(self, result: CollectionResult):
        """초기화

        Args:
            result: CollectionResult 객체
        """
        self.result = result
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate(self, output_path: str | Path, auto_open: bool = True) -> Path:
        """HTML 대시보드 생성

        Args:
            output_path: 출력 파일 경로
            auto_open: 브라우저 자동 열기

        Returns:
            생성된 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._build_html()
        output_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Health 대시보드 생성됨: {output_path}")

        if auto_open:
            self._open_in_browser(str(output_path))

        return output_path

    def _open_in_browser(self, filepath: str) -> None:
        """브라우저에서 HTML 파일 열기"""
        import os
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                os.startfile(filepath)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", filepath], check=True)  # noqa: S603, S607
            else:
                subprocess.run(["xdg-open", filepath], check=True)  # noqa: S603, S607
        except Exception as e:
            logger.warning(f"브라우저 열기 실패: {e}")

    def _build_html(self) -> str:
        """HTML 문서 생성"""
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Health Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
{self._get_styles()}
    </style>
</head>
<body>
    <div class="cs-app-layout">
        <header class="cs-header">
            <div class="cs-header-content">
                <h1><i class="fa-solid fa-heart-pulse"></i> AWS Health Dashboard</h1>
                <span class="cs-header-meta">생성: {self.generated_at}</span>
            </div>
        </header>

        <main class="cs-main">
            <div class="cs-content">
                {self._build_summary_section()}
                {self._build_charts_section()}
                {self._build_calendar_section()}
                {self._build_events_section()}
            </div>
        </main>

        <footer class="cs-footer">
            <p>AWS Personal Health Dashboard Analysis | AA (AWS Automation)</p>
        </footer>
    </div>

    <script>
{self._get_scripts()}
    </script>
</body>
</html>"""

    def _get_styles(self) -> str:
        """CSS 스타일"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f2f3f3;
            color: #16191f;
            line-height: 1.5;
        }

        .cs-app-layout {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .cs-header {
            background: linear-gradient(135deg, #232f3e 0%, #0a1128 100%);
            color: #fff;
            padding: 20px 32px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }

        .cs-header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .cs-header h1 {
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .cs-header h1 i {
            color: #ff9900;
        }

        .cs-header-meta {
            font-size: 14px;
            color: #aab7b8;
        }

        .cs-main {
            flex: 1;
            padding: 24px 32px;
        }

        .cs-content {
            max-width: 1400px;
            margin: 0 auto;
        }

        .cs-container {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            overflow: hidden;
        }

        .cs-container-header {
            padding: 16px 20px;
            border-bottom: 1px solid #e9ebed;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .cs-container-header h2 {
            font-size: 18px;
            font-weight: 600;
            color: #16191f;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .cs-container-body {
            padding: 20px;
        }

        /* Summary Cards */
        .cs-metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .cs-metric-card {
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid #0972d3;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .cs-metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .cs-metric-card.critical {
            border-left-color: #d91515;
            background: linear-gradient(135deg, #fff 0%, #fff1f0 100%);
        }

        .cs-metric-card.high {
            border-left-color: #8d6605;
            background: linear-gradient(135deg, #fff 0%, #fffae6 100%);
        }

        .cs-metric-card.medium {
            border-left-color: #0972d3;
            background: linear-gradient(135deg, #fff 0%, #f2f8fd 100%);
        }

        .cs-metric-card.low {
            border-left-color: #7d8998;
            background: linear-gradient(135deg, #fff 0%, #f4f4f4 100%);
        }

        .cs-metric-label {
            font-size: 13px;
            color: #5f6b7a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .cs-metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #16191f;
        }

        .cs-metric-card.critical .cs-metric-value { color: #d91515; }
        .cs-metric-card.high .cs-metric-value { color: #8d6605; }

        .cs-metric-detail {
            font-size: 13px;
            color: #5f6b7a;
            margin-top: 8px;
        }

        /* Charts Grid */
        .cs-charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
        }

        .cs-chart-container {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 20px;
        }

        .cs-chart-title {
            font-size: 16px;
            font-weight: 600;
            color: #16191f;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .cs-chart {
            height: 300px;
        }

        /* Calendar */
        .cs-calendar {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 4px;
        }

        .cs-calendar-header {
            background: #f7f8f8;
            padding: 12px 8px;
            text-align: center;
            font-weight: 600;
            font-size: 13px;
            color: #5f6b7a;
            border-radius: 6px;
        }

        .cs-calendar-day {
            min-height: 80px;
            padding: 8px;
            background: #fff;
            border: 1px solid #e9ebed;
            border-radius: 6px;
            font-size: 13px;
            transition: background-color 0.2s;
        }

        .cs-calendar-day:hover {
            background: #f7f8f8;
        }

        .cs-calendar-day.empty {
            background: #f7f8f8;
            border-color: transparent;
        }

        .cs-calendar-day-number {
            font-weight: 600;
            color: #16191f;
            margin-bottom: 4px;
        }

        .cs-calendar-event {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .cs-calendar-event.critical {
            background: #fee7e7;
            color: #d91515;
            font-weight: 600;
        }

        .cs-calendar-event.high {
            background: #fef6e0;
            color: #8d6605;
        }

        .cs-calendar-event.medium {
            background: #e3f2fd;
            color: #0972d3;
        }

        .cs-calendar-event.low {
            background: #f4f4f4;
            color: #5f6b7a;
        }

        .cs-calendar-more {
            font-size: 11px;
            color: #0972d3;
            cursor: pointer;
        }

        /* Month Tabs */
        .cs-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }

        .cs-tab {
            padding: 8px 16px;
            border: 1px solid #e9ebed;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }

        .cs-tab:hover {
            border-color: #0972d3;
            color: #0972d3;
        }

        .cs-tab.active {
            background: #0972d3;
            color: #fff;
            border-color: #0972d3;
        }

        /* Events Table */
        .cs-table-wrapper {
            overflow-x: auto;
        }

        .cs-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .cs-table th {
            background: #f7f8f8;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: #16191f;
            border-bottom: 2px solid #e9ebed;
            white-space: nowrap;
        }

        .cs-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #e9ebed;
            vertical-align: top;
        }

        .cs-table tr:hover {
            background: #f7f8f8;
        }

        .cs-table tr.critical { background: #fff1f0; }
        .cs-table tr.critical:hover { background: #fee7e7; }
        .cs-table tr.high { background: #fffae6; }
        .cs-table tr.high:hover { background: #fef6e0; }

        .cs-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }

        .cs-badge.critical {
            background: #d91515;
            color: #fff;
        }

        .cs-badge.high {
            background: #8d6605;
            color: #fff;
        }

        .cs-badge.medium {
            background: #0972d3;
            color: #fff;
        }

        .cs-badge.low {
            background: #7d8998;
            color: #fff;
        }

        .cs-badge.open {
            background: #037f0c;
            color: #fff;
        }

        .cs-badge.upcoming {
            background: #006ce0;
            color: #fff;
        }

        .cs-badge.closed {
            background: #5f6b7a;
            color: #fff;
        }

        /* Search & Filter */
        .cs-search-box {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }

        .cs-search-input {
            flex: 1;
            min-width: 200px;
            padding: 10px 16px;
            border: 1px solid #e9ebed;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        .cs-search-input:focus {
            outline: none;
            border-color: #0972d3;
            box-shadow: 0 0 0 3px rgba(9, 114, 211, 0.1);
        }

        .cs-select {
            padding: 10px 16px;
            border: 1px solid #e9ebed;
            border-radius: 6px;
            font-size: 14px;
            background: #fff;
            cursor: pointer;
        }

        /* Footer */
        .cs-footer {
            background: #232f3e;
            color: #aab7b8;
            padding: 16px 32px;
            text-align: center;
            font-size: 13px;
        }

        /* Empty State */
        .cs-empty-state {
            text-align: center;
            padding: 48px 24px;
            color: #5f6b7a;
        }

        .cs-empty-state i {
            font-size: 48px;
            margin-bottom: 16px;
            color: #aab7b8;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .cs-header-content {
                flex-direction: column;
                gap: 8px;
            }

            .cs-main {
                padding: 16px;
            }

            .cs-charts-grid {
                grid-template-columns: 1fr;
            }

            .cs-metrics-row {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        """

    def _build_summary_section(self) -> str:
        """요약 카드 섹션"""
        urgency_data = self.result.summary_by_urgency
        total = self.result.patch_count
        affected = self.result.affected_resource_count

        critical = urgency_data.get("critical", {}).get("count", 0)
        high = urgency_data.get("high", {}).get("count", 0)
        medium = urgency_data.get("medium", {}).get("count", 0)
        low = urgency_data.get("low", {}).get("count", 0)

        critical_services = ", ".join(urgency_data.get("critical", {}).get("services", [])[:3])
        high_services = ", ".join(urgency_data.get("high", {}).get("services", [])[:3])

        return f"""
        <section class="cs-metrics-row">
            <div class="cs-metric-card critical">
                <div class="cs-metric-label"><i class="fa-solid fa-circle-exclamation"></i> 긴급 (3일 이내)</div>
                <div class="cs-metric-value">{critical}</div>
                <div class="cs-metric-detail">{critical_services or "-"}</div>
            </div>
            <div class="cs-metric-card high">
                <div class="cs-metric-label"><i class="fa-solid fa-triangle-exclamation"></i> 높음 (7일 이내)</div>
                <div class="cs-metric-value">{high}</div>
                <div class="cs-metric-detail">{high_services or "-"}</div>
            </div>
            <div class="cs-metric-card medium">
                <div class="cs-metric-label"><i class="fa-solid fa-circle-info"></i> 중간 (14일 이내)</div>
                <div class="cs-metric-value">{medium}</div>
                <div class="cs-metric-detail">-</div>
            </div>
            <div class="cs-metric-card low">
                <div class="cs-metric-label"><i class="fa-solid fa-clock"></i> 낮음 (14일 이후)</div>
                <div class="cs-metric-value">{low}</div>
                <div class="cs-metric-detail">-</div>
            </div>
            <div class="cs-metric-card">
                <div class="cs-metric-label"><i class="fa-solid fa-list-check"></i> 전체 패치</div>
                <div class="cs-metric-value">{total}</div>
                <div class="cs-metric-detail">영향 리소스: {affected}개</div>
            </div>
        </section>
        """

    def _build_charts_section(self) -> str:
        """차트 섹션"""
        return """
        <div class="cs-container">
            <div class="cs-container-header">
                <h2><i class="fa-solid fa-chart-pie"></i> 분석 현황</h2>
            </div>
            <div class="cs-container-body">
                <div class="cs-charts-grid">
                    <div class="cs-chart-container">
                        <div class="cs-chart-title"><i class="fa-solid fa-gauge-high"></i> 긴급도별 분포</div>
                        <div id="urgencyChart" class="cs-chart"></div>
                    </div>
                    <div class="cs-chart-container">
                        <div class="cs-chart-title"><i class="fa-solid fa-server"></i> 서비스별 분포</div>
                        <div id="serviceChart" class="cs-chart"></div>
                    </div>
                    <div class="cs-chart-container">
                        <div class="cs-chart-title"><i class="fa-solid fa-calendar-days"></i> 월별 예정 현황</div>
                        <div id="monthlyChart" class="cs-chart"></div>
                    </div>
                    <div class="cs-chart-container">
                        <div class="cs-chart-title"><i class="fa-solid fa-wrench"></i> 필요 조치별 분포</div>
                        <div id="actionChart" class="cs-chart"></div>
                    </div>
                </div>
            </div>
        </div>
        """

    def _build_calendar_section(self) -> str:
        """캘린더 섹션"""
        months = sorted([k for k in self.result.summary_by_month if k != "미정"])[:3]

        if not months:
            return """
            <div class="cs-container">
                <div class="cs-container-header">
                    <h2><i class="fa-solid fa-calendar"></i> 패치 일정</h2>
                </div>
                <div class="cs-container-body">
                    <div class="cs-empty-state">
                        <i class="fa-solid fa-calendar-check"></i>
                        <p>예정된 패치가 없습니다</p>
                    </div>
                </div>
            </div>
            """

        tabs_html = ""
        calendars_html = ""

        for i, month_key in enumerate(months):
            active = "active" if i == 0 else ""
            display = "block" if i == 0 else "none"

            tabs_html += f'<button class="cs-tab {active}" onclick="switchMonth(\'{month_key}\')">{month_key}</button>'

            calendar_html = self._build_month_calendar(month_key)
            calendars_html += f'<div id="calendar-{month_key}" class="cs-calendar-wrapper" style="display: {display};">{calendar_html}</div>'

        return f"""
        <div class="cs-container">
            <div class="cs-container-header">
                <h2><i class="fa-solid fa-calendar"></i> 패치 일정</h2>
            </div>
            <div class="cs-container-body">
                <div class="cs-tabs">{tabs_html}</div>
                {calendars_html}
            </div>
        </div>
        """

    def _build_month_calendar(self, month_key: str) -> str:
        """월별 캘린더 생성"""
        try:
            year, month = map(int, month_key.split("-"))
        except ValueError:
            return ""

        patches = self.result.summary_by_month.get(month_key, [])

        # 일자별 패치 매핑
        patches_by_day: dict[int, list[PatchItem]] = {}
        for patch in patches:
            if patch.scheduled_date:
                day = patch.scheduled_date.day
                if day not in patches_by_day:
                    patches_by_day[day] = []
                patches_by_day[day].append(patch)

        # 캘린더 생성
        cal = monthcalendar(year, month)
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]

        html = '<div class="cs-calendar">'

        # 요일 헤더
        for day_name in weekdays:
            html += f'<div class="cs-calendar-header">{day_name}</div>'

        # 날짜 셀
        for week in cal:
            for day in week:
                if day == 0:
                    html += '<div class="cs-calendar-day empty"></div>'
                else:
                    day_patches = patches_by_day.get(day, [])
                    html += '<div class="cs-calendar-day">'
                    html += f'<div class="cs-calendar-day-number">{day}</div>'

                    for patch in day_patches[:2]:
                        urgency_class = patch.urgency
                        html += f'<div class="cs-calendar-event {urgency_class}" title="{patch.event_type}">{patch.service}</div>'

                    if len(day_patches) > 2:
                        html += f'<div class="cs-calendar-more">+{len(day_patches) - 2} more</div>'

                    html += "</div>"

        html += "</div>"
        return html

    def _build_events_section(self) -> str:
        """이벤트 테이블 섹션"""
        if not self.result.patches:
            return """
            <div class="cs-container">
                <div class="cs-container-header">
                    <h2><i class="fa-solid fa-list"></i> 패치 목록</h2>
                </div>
                <div class="cs-container-body">
                    <div class="cs-empty-state">
                        <i class="fa-solid fa-check-circle"></i>
                        <p>예정된 패치가 없습니다</p>
                    </div>
                </div>
            </div>
            """

        rows_html = ""
        for patch in self.result.patches:
            urgency_class = patch.urgency
            urgency_text = {"critical": "긴급", "high": "높음", "medium": "중간", "low": "낮음"}.get(
                patch.urgency, patch.urgency
            )

            scheduled_date = patch.scheduled_date.strftime("%Y-%m-%d") if patch.scheduled_date else "-"
            d_day = f"D-{patch.event.days_until_start}" if patch.event.days_until_start is not None else "-"

            status_class = patch.event.status_code

            rows_html += f"""
            <tr class="{urgency_class}">
                <td><span class="cs-badge {urgency_class}">{urgency_text}</span></td>
                <td>{patch.service}</td>
                <td>{patch.event_type}</td>
                <td>{scheduled_date}</td>
                <td>{d_day}</td>
                <td><span class="cs-badge {status_class}">{patch.event.status_code}</span></td>
                <td>{patch.action_required}</td>
                <td>{len(patch.affected_resources)}</td>
                <td>{patch.event.region}</td>
            </tr>
            """

        return f"""
        <div class="cs-container">
            <div class="cs-container-header">
                <h2><i class="fa-solid fa-list"></i> 패치 목록</h2>
            </div>
            <div class="cs-container-body">
                <div class="cs-search-box">
                    <input type="text" class="cs-search-input" id="searchInput" placeholder="검색 (서비스, 이벤트 유형...)" onkeyup="filterTable()">
                    <select class="cs-select" id="urgencyFilter" onchange="filterTable()">
                        <option value="">전체 긴급도</option>
                        <option value="critical">긴급</option>
                        <option value="high">높음</option>
                        <option value="medium">중간</option>
                        <option value="low">낮음</option>
                    </select>
                </div>
                <div class="cs-table-wrapper">
                    <table class="cs-table" id="eventsTable">
                        <thead>
                            <tr>
                                <th>긴급도</th>
                                <th>서비스</th>
                                <th>이벤트 유형</th>
                                <th>예정일</th>
                                <th>D-Day</th>
                                <th>상태</th>
                                <th>필요 조치</th>
                                <th>영향 리소스</th>
                                <th>리전</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

    def _get_scripts(self) -> str:
        """JavaScript"""
        urgency_data = self._get_urgency_chart_data()
        service_data = self._get_service_chart_data()
        monthly_data = self._get_monthly_chart_data()
        action_data = self._get_action_chart_data()

        return f"""
        // Chart Data
        const urgencyData = {json.dumps(urgency_data, ensure_ascii=False)};
        const serviceData = {json.dumps(service_data, ensure_ascii=False)};
        const monthlyData = {json.dumps(monthly_data, ensure_ascii=False)};
        const actionData = {json.dumps(action_data, ensure_ascii=False)};

        // Initialize Charts
        document.addEventListener('DOMContentLoaded', function() {{
            initUrgencyChart();
            initServiceChart();
            initMonthlyChart();
            initActionChart();
        }});

        function initUrgencyChart() {{
            const chart = echarts.init(document.getElementById('urgencyChart'));
            const option = {{
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}건 ({{d}}%)' }},
                legend: {{ bottom: 10, left: 'center' }},
                color: ['#d91515', '#8d6605', '#0972d3', '#7d8998'],
                series: [{{
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    itemStyle: {{ borderRadius: 10, borderColor: '#fff', borderWidth: 2 }},
                    label: {{ show: false }},
                    emphasis: {{ label: {{ show: true, fontSize: 14, fontWeight: 'bold' }} }},
                    data: urgencyData
                }}]
            }};
            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        function initServiceChart() {{
            const chart = echarts.init(document.getElementById('serviceChart'));
            const option = {{
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: 80, right: 20, bottom: 30, top: 20 }},
                xAxis: {{ type: 'value' }},
                yAxis: {{ type: 'category', data: serviceData.labels, inverse: true }},
                series: [{{
                    type: 'bar',
                    data: serviceData.values,
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            {{ offset: 0, color: '#0972d3' }},
                            {{ offset: 1, color: '#73c0de' }}
                        ]),
                        borderRadius: [0, 4, 4, 0]
                    }}
                }}]
            }};
            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        function initMonthlyChart() {{
            const chart = echarts.init(document.getElementById('monthlyChart'));
            const option = {{
                tooltip: {{ trigger: 'axis' }},
                grid: {{ left: 50, right: 20, bottom: 30, top: 40 }},
                legend: {{ top: 0 }},
                xAxis: {{ type: 'category', data: monthlyData.labels }},
                yAxis: {{ type: 'value' }},
                series: [
                    {{ name: '긴급', type: 'bar', stack: 'total', data: monthlyData.critical, color: '#d91515' }},
                    {{ name: '높음', type: 'bar', stack: 'total', data: monthlyData.high, color: '#8d6605' }},
                    {{ name: '중간', type: 'bar', stack: 'total', data: monthlyData.medium, color: '#0972d3' }},
                    {{ name: '낮음', type: 'bar', stack: 'total', data: monthlyData.low, color: '#7d8998' }}
                ]
            }};
            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        function initActionChart() {{
            const chart = echarts.init(document.getElementById('actionChart'));
            const option = {{
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}건 ({{d}}%)' }},
                legend: {{ bottom: 10, left: 'center' }},
                color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452'],
                series: [{{
                    type: 'pie',
                    radius: '60%',
                    data: actionData,
                    emphasis: {{
                        itemStyle: {{ shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }}
                    }}
                }}]
            }};
            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }}

        // Month Tab Switch
        function switchMonth(monthKey) {{
            document.querySelectorAll('.cs-tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.cs-calendar-wrapper').forEach(cal => cal.style.display = 'none');

            event.target.classList.add('active');
            document.getElementById('calendar-' + monthKey).style.display = 'block';
        }}

        // Table Filter
        function filterTable() {{
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            const urgencyFilter = document.getElementById('urgencyFilter').value;
            const rows = document.querySelectorAll('#eventsTable tbody tr');

            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                const urgencyMatch = !urgencyFilter || row.classList.contains(urgencyFilter);
                const searchMatch = !searchText || text.includes(searchText);
                row.style.display = (urgencyMatch && searchMatch) ? '' : 'none';
            }});
        }}
        """

    def _get_urgency_chart_data(self) -> list[dict[str, Any]]:
        """긴급도별 차트 데이터"""
        urgency_map = {"critical": "긴급", "high": "높음", "medium": "중간", "low": "낮음"}
        data = []
        for key, label in urgency_map.items():
            count = self.result.summary_by_urgency.get(key, {}).get("count", 0)
            if count > 0:
                data.append({"name": label, "value": count})
        return data if data else [{"name": "없음", "value": 0}]

    def _get_service_chart_data(self) -> dict[str, Any]:
        """서비스별 차트 데이터"""
        sorted_services = sorted(
            self.result.summary_by_service.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:10]

        labels = [s[0] for s in sorted_services]
        values = [s[1]["count"] for s in sorted_services]

        return {"labels": labels, "values": values}

    def _get_monthly_chart_data(self) -> dict[str, Any]:
        """월별 차트 데이터"""
        months = sorted([k for k in self.result.summary_by_month if k != "미정"])[:6]

        labels = []
        critical = []
        high = []
        medium = []
        low = []

        for month_key in months:
            patches = self.result.summary_by_month[month_key]
            labels.append(month_key)
            critical.append(sum(1 for p in patches if p.urgency == "critical"))
            high.append(sum(1 for p in patches if p.urgency == "high"))
            medium.append(sum(1 for p in patches if p.urgency == "medium"))
            low.append(sum(1 for p in patches if p.urgency == "low"))

        return {"labels": labels, "critical": critical, "high": high, "medium": medium, "low": low}

    def _get_action_chart_data(self) -> list[dict[str, Any]]:
        """필요 조치별 차트 데이터"""
        action_counts: dict[str, int] = {}
        for patch in self.result.patches:
            action = patch.action_required
            action_counts[action] = action_counts.get(action, 0) + 1

        data = [
            {"name": action, "value": count} for action, count in sorted(action_counts.items(), key=lambda x: -x[1])
        ]

        return data if data else [{"name": "없음", "value": 0}]


def generate_dashboard(result: CollectionResult, output_path: str | Path, auto_open: bool = True) -> Path:
    """대시보드 생성 편의 함수

    Args:
        result: CollectionResult 객체
        output_path: 출력 파일 경로
        auto_open: 브라우저 자동 열기

    Returns:
        생성된 파일 경로
    """
    dashboard = HealthDashboard(result)
    return dashboard.generate(output_path, auto_open)
