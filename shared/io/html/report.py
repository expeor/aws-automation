"""HTML 리포트 생성기

ECharts 기반 시각화를 포함한 단일 HTML 파일 생성
실행 → 저장 → 브라우저 자동 열기
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 대용량 데이터 처리 상수
DEFAULT_TOP_N = 10  # Top N 표시 기본값
MAX_CHART_CATEGORIES = 15  # 차트에 표시할 최대 카테고리 수
ANIMATION_THRESHOLD = 100  # 애니메이션 비활성화 임계값

# ECharts 색상 팔레트
COLORS = [
    "#5470c6",  # 파랑
    "#91cc75",  # 초록
    "#fac858",  # 노랑
    "#ee6666",  # 빨강
    "#73c0de",  # 하늘
    "#3ba272",  # 진초록
    "#fc8452",  # 주황
    "#9a60b4",  # 보라
    "#ea7ccc",  # 분홍
]


def open_in_browser(filepath: str) -> bool:
    """브라우저에서 HTML 파일 열기"""
    try:
        if sys.platform == "win32":
            os.startfile(filepath)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath], check=True)  # noqa: S603, S607
        else:
            subprocess.run(["xdg-open", filepath], check=True)  # noqa: S603, S607
        return True
    except Exception as e:
        logger.warning(f"브라우저 열기 실패: {e}")
        try:
            webbrowser.open(f"file://{Path(filepath).resolve()}")
            return True
        except Exception as e:
            logger.debug("Failed to open in browser: %s", e)
            return False


def group_top_n(
    data: list[tuple[str, int | float]],
    top_n: int = DEFAULT_TOP_N,
    others_label: str = "기타",
    include_others_count: bool = True,
) -> list[tuple[str, int | float]]:
    """대용량 데이터를 Top N + "기타"로 그룹화

    Args:
        data: (이름, 값) 튜플 리스트
        top_n: 상위 N개만 표시
        others_label: 기타 그룹 라벨
        include_others_count: "기타 (23개)" 형식으로 개수 포함

    Returns:
        Top N + 기타로 그룹화된 데이터

    Example:
        >>> data = [("A", 100), ("B", 90), ..., ("Z", 5)]  # 26개
        >>> group_top_n(data, top_n=5)
        [("A", 100), ("B", 90), ("C", 80), ("D", 70), ("E", 60), ("기타 (21개)", 150)]
    """
    if len(data) <= top_n:
        return data

    # 값 기준 정렬
    sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

    top_items = sorted_data[:top_n]
    others = sorted_data[top_n:]

    others_value = sum(v for _, v in others)
    others_count = len(others)

    others_name = f"{others_label} ({others_count}개)" if include_others_count else others_label

    return top_items + [(others_name, others_value)]


def aggregate_by_group(
    data: list[dict[str, Any]],
    group_key: str,
    value_key: str | None = None,
    aggregation: str = "count",
) -> list[tuple[str, int | float]]:
    """데이터를 그룹별로 집계

    Args:
        data: 딕셔너리 리스트
        group_key: 그룹화할 키
        value_key: 집계할 값 키 (sum 시 필요)
        aggregation: "count", "sum", "avg"

    Returns:
        (그룹명, 집계값) 튜플 리스트
    """
    from collections import defaultdict

    groups: dict[str, list] = defaultdict(list)
    for item in data:
        key = item.get(group_key, "Unknown")
        if value_key:
            groups[key].append(item.get(value_key, 0))
        else:
            groups[key].append(1)

    result = []
    for name, values in groups.items():
        if aggregation == "count":
            result.append((name, len(values)))
        elif aggregation == "sum":
            result.append((name, sum(values)))
        elif aggregation == "avg":
            result.append((name, sum(values) / len(values) if values else 0))

    return sorted(result, key=lambda x: x[1], reverse=True)


def build_treemap_hierarchy(
    data: list[dict[str, Any]],
    group_keys: list[str],
    value_key: str | None = None,
) -> list[dict[str, Any]]:
    """계층적 트리맵 데이터 생성

    Args:
        data: 딕셔너리 리스트
        group_keys: 계층 순서 (예: ["account_name", "region", "service"])
        value_key: 값 키 (None이면 count)

    Returns:
        트리맵용 계층 데이터

    Example:
        >>> data = [
        ...     {"account": "A", "region": "ap-northeast-2", "count": 10},
        ...     {"account": "A", "region": "us-east-1", "count": 5},
        ...     {"account": "B", "region": "ap-northeast-2", "count": 8},
        ... ]
        >>> build_treemap_hierarchy(data, ["account", "region"], "count")
        [
            {"name": "A", "value": 15, "children": [
                {"name": "ap-northeast-2", "value": 10},
                {"name": "us-east-1", "value": 5},
            ]},
            {"name": "B", "value": 8, "children": [
                {"name": "ap-northeast-2", "value": 8},
            ]},
        ]
    """
    if not group_keys:
        return []

    from collections import defaultdict

    def build_level(items: list[dict], keys: list[str]) -> list[dict[str, Any]]:
        if not keys:
            return []

        current_key = keys[0]
        remaining_keys = keys[1:]

        groups: dict[str, list] = defaultdict(list)
        for item in items:
            group_name = str(item.get(current_key, "Unknown"))
            groups[group_name].append(item)

        result = []
        for name, group_items in groups.items():
            value = sum(item.get(value_key, 0) for item in group_items) if value_key else len(group_items)

            node: dict[str, Any] = {"name": name, "value": value}

            if remaining_keys:
                children = build_level(group_items, remaining_keys)
                if children:
                    node["children"] = children

            result.append(node)

        return sorted(result, key=lambda x: x["value"], reverse=True)

    return build_level(data, group_keys)


class ChartSize(Enum):
    """차트 크기 설정

    - SMALL: 350px 높이, 1열 차지 (기본)
    - MEDIUM: 400px 높이, 1열 차지
    - LARGE: 500px 높이, 전체 너비 (2열 span)
    - XLARGE: 600px 높이, 전체 너비
    """

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


def _determine_chart_size(
    data_count: int,
    series_count: int = 1,
    chart_type: str = "default",
) -> tuple[int, ChartSize]:
    """데이터 양에 따라 적절한 차트 크기 결정

    Args:
        data_count: 데이터 포인트/카테고리 수
        series_count: 시리즈 수
        chart_type: 차트 타입 ("pie", "bar", "line", "treemap", "default")

    Returns:
        (height, size) 튜플
    """
    # 복잡도 점수 계산
    complexity = data_count * series_count

    if complexity <= 6:
        return (350, ChartSize.SMALL)
    elif complexity <= 15:
        return (400, ChartSize.MEDIUM)
    elif complexity <= 30:
        return (500, ChartSize.LARGE)
    else:
        return (600, ChartSize.XLARGE)


def _count_treemap_nodes(data: list[dict]) -> int:
    """트리맵 데이터의 총 노드 수 계산"""
    count = 0
    for node in data:
        count += 1
        if "children" in node:
            count += _count_treemap_nodes(node["children"])
    return count


@dataclass
class ChartConfig:
    """차트 설정"""

    chart_id: str
    option: dict[str, Any]
    height: int = 350
    size: ChartSize = field(default=ChartSize.SMALL)


class HTMLReport:
    """HTML 리포트 생성기 (ECharts 기반)

    Example:
        report = HTMLReport("리소스 분석 리포트")

        report.add_summary([
            ("총 리소스", 150, None),
            ("미사용", 23, "danger"),
            ("예상 절감", "$1,234", "success"),
        ])

        report.add_pie_chart(
            title="리소스 유형별 분포",
            data=[("EC2", 45), ("RDS", 30), ("Lambda", 25)]
        )

        report.add_bar_chart(
            title="계정별 미사용 리소스",
            categories=["account-1", "account-2"],
            series=[("미사용", [12, 8]), ("사용중", [88, 92])]
        )

        report.add_table(
            title="상세 데이터",
            headers=["계정", "리전", "리소스"],
            rows=[["account-1", "ap-northeast-2", "i-12345"]]
        )

        report.save("output/report.html")
    """

    def __init__(self, title: str, subtitle: str | None = None):
        self.title = title
        self.subtitle = subtitle
        self.charts: list[ChartConfig] = []
        self.tables: list[dict[str, Any]] = []
        self.summaries: list[dict[str, Any]] = []
        self.created_at = datetime.now()
        self._chart_counter = 0

    def _next_chart_id(self) -> str:
        self._chart_counter += 1
        return f"chart_{self._chart_counter}"

    def add_summary(self, items: list[tuple[str, str | int | float, str | None]]) -> HTMLReport:
        """요약 카드 추가

        Args:
            items: (라벨, 값, 색상) 튜플 리스트
                   색상: "danger", "warning", "success", None
        """
        self.summaries.append({"items": items})
        return self

    def add_pie_chart(
        self,
        title: str,
        data: list[tuple[str, int | float]],
        doughnut: bool = False,
        rose: bool = False,
        top_n: int | None = None,
        others_label: str = "기타",
    ) -> HTMLReport:
        """파이/도넛/로즈 차트

        Args:
            title: 차트 제목
            data: (이름, 값) 튜플 리스트
            doughnut: 도넛 차트 여부
            rose: 로즈(nightingale) 차트 여부
            top_n: Top N만 표시 (나머지는 "기타"로 그룹화). None이면 자동 판단
            others_label: 기타 그룹 라벨

        Note:
            - 6개 초과 카테고리는 자동으로 Top 5 + 기타로 그룹화됨 (top_n=None일 때)
            - 명시적으로 top_n을 지정하면 해당 값 사용
        """
        # 대용량 데이터 자동 그룹화
        if top_n is not None:
            data = group_top_n(data, top_n=top_n, others_label=others_label)
        elif len(data) > 6:
            # 6개 초과 시 자동으로 Top 5로 그룹화
            data = group_top_n(data, top_n=5, others_label=others_label)

        series_data = [{"name": name, "value": value} for name, value in data]

        radius = ["40%", "70%"] if doughnut else "70%"

        option = {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left", "top": "middle"},
            "color": COLORS,
            "animationThreshold": ANIMATION_THRESHOLD,
            "series": [
                {
                    "type": "pie",
                    "radius": radius,
                    "roseType": "radius" if rose else False,
                    "data": series_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.3)",
                        }
                    },
                    "label": {"formatter": "{b}: {d}%"},
                }
            ],
        }
        # 데이터 양에 따른 크기 결정
        height, size = _determine_chart_size(len(data), chart_type="pie")
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_bar_chart(
        self,
        title: str,
        categories: list[str],
        series: list[tuple[str, list[int | float]]],
        horizontal: bool | None = None,
        stacked: bool = False,
        top_n: int | None = None,
    ) -> HTMLReport:
        """바 차트

        Args:
            title: 차트 제목
            categories: 카테고리 리스트 (X축)
            series: (시리즈명, 값 리스트) 튜플 리스트
            horizontal: 가로 바 차트 (None이면 카테고리 수에 따라 자동 결정)
            stacked: 스택 차트
            top_n: Top N만 표시 (시리즈 첫 번째 기준 정렬)

        Note:
            - horizontal=None이고 카테고리가 8개 이상이면 자동으로 가로 바 차트
            - top_n 지정 시 첫 번째 시리즈 값 기준으로 정렬 후 Top N만 표시
        """
        # Top N 처리
        if top_n is not None and len(categories) > top_n:
            # 첫 번째 시리즈 기준 정렬
            first_series_values = series[0][1] if series else []
            indices = sorted(
                range(len(categories)),
                key=lambda i: first_series_values[i] if i < len(first_series_values) else 0,
                reverse=True,
            )[:top_n]

            categories = [categories[i] for i in indices]
            series = [(name, [values[i] for i in indices if i < len(values)]) for name, values in series]

        # 카테고리가 많으면 자동으로 horizontal
        if horizontal is None:
            horizontal = len(categories) >= 8

        series_list = []
        for name, values in series:
            s = {
                "name": name,
                "type": "bar",
                "data": values,
                "emphasis": {"focus": "series"},
            }
            if stacked:
                s["stack"] = "total"
            series_list.append(s)

        axis_config = {"type": "category", "data": categories}
        value_axis = {"type": "value"}

        # 데이터 복잡도 기반 크기 결정
        complexity = len(categories) * len(series)
        height, size = _determine_chart_size(complexity, chart_type="bar")

        # 가로 바 차트일 때 높이 조정: 카테고리당 35px 확보
        if horizontal:
            height = max(height, len(categories) * 35)
            # 카테고리 많으면 전체 너비 사용
            if len(categories) > 10:
                size = ChartSize.LARGE if size == ChartSize.SMALL else size

        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"top": 30},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "color": COLORS,
            "animationThreshold": ANIMATION_THRESHOLD,
            "xAxis": value_axis if horizontal else axis_config,
            "yAxis": axis_config if horizontal else value_axis,
            "series": series_list,
        }
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_line_chart(
        self,
        title: str,
        categories: list[str],
        series: list[tuple[str, list[int | float]]],
        area: bool = False,
        smooth: bool = True,
        scrollable: bool | None = None,
    ) -> HTMLReport:
        """라인 차트

        Args:
            title: 차트 제목
            categories: X축 카테고리
            series: (시리즈명, 값 리스트) 튜플 리스트
            area: 영역 채우기
            smooth: 곡선 여부
            scrollable: 스크롤 가능 여부 (None이면 데이터 양에 따라 자동)

        Note:
            - scrollable=None이고 카테고리가 30개 이상이면 자동으로 dataZoom 활성화
        """
        series_list: list[dict[str, Any]] = []
        for name, values in series:
            s: dict[str, Any] = {
                "name": name,
                "type": "line",
                "data": values,
                "smooth": smooth,
            }
            if area:
                s["areaStyle"] = {"opacity": 0.3}
            series_list.append(s)

        # 대용량 데이터 시 스크롤 활성화
        enable_scroll = scrollable if scrollable is not None else len(categories) >= 30

        option: dict[str, Any] = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 30},
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "15%" if enable_scroll else "3%",
                "containLabel": True,
            },
            "color": COLORS,
            "animationThreshold": ANIMATION_THRESHOLD,
            "xAxis": {"type": "category", "boundaryGap": False, "data": categories},
            "yAxis": {"type": "value"},
            "series": series_list,
        }

        if enable_scroll:
            option["dataZoom"] = [
                {
                    "type": "slider",
                    "start": 0,
                    "end": min(100, 3000 / max(1, len(categories)) * 100),  # 초기 30개 표시
                },
                {"type": "inside"},
            ]

        # 데이터 복잡도 기반 크기 결정
        complexity = len(categories) * len(series)
        height, size = _determine_chart_size(complexity, chart_type="line")

        # 데이터 포인트가 많으면 넓은 공간 필요
        if len(categories) > 50:
            size = ChartSize.LARGE if size.value in ("small", "medium") else size

        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_gauge_chart(
        self,
        title: str,
        value: int | float,
        max_value: int | float = 100,
        thresholds: list[tuple[float, str]] | None = None,
    ) -> HTMLReport:
        """게이지 차트

        Args:
            title: 차트 제목
            value: 현재 값
            max_value: 최대 값
            thresholds: (비율, 색상) 리스트. 예: [(0.3, '#91cc75'), (0.7, '#fac858'), (1, '#ee6666')]
        """
        if thresholds is None:
            thresholds = [(0.3, "#91cc75"), (0.7, "#fac858"), (1, "#ee6666")]

        option = {
            "title": {"text": title, "left": "center"},
            "series": [
                {
                    "type": "gauge",
                    "min": 0,
                    "max": max_value,
                    "progress": {"show": True, "width": 18},
                    "axisLine": {
                        "lineStyle": {
                            "width": 18,
                            "color": thresholds,
                        }
                    },
                    "pointer": {"itemStyle": {"color": "auto"}},
                    "axisTick": {"distance": -30, "length": 8},
                    "splitLine": {"distance": -30, "length": 20},
                    "axisLabel": {"distance": 25, "fontSize": 12},
                    "detail": {
                        "valueAnimation": True,
                        "formatter": "{value}",
                        "fontSize": 24,
                    },
                    "data": [{"value": value, "name": title}],
                }
            ],
        }
        # 게이지 차트는 항상 SMALL
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=300, size=ChartSize.SMALL))
        return self

    def add_radar_chart(
        self,
        title: str,
        indicators: list[tuple[str, int | float]],
        series: list[tuple[str, list[int | float]]],
    ) -> HTMLReport:
        """레이더 차트

        Args:
            title: 차트 제목
            indicators: (지표명, 최대값) 리스트
            series: (시리즈명, 값 리스트) 튜플 리스트
        """
        indicator_list = [{"name": name, "max": max_val} for name, max_val in indicators]

        series_data = []
        for name, values in series:
            series_data.append({"name": name, "value": values})

        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "legend": {"top": 30, "data": [name for name, _ in series]},
            "color": COLORS,
            "radar": {"indicator": indicator_list},
            "series": [
                {
                    "type": "radar",
                    "data": series_data,
                }
            ],
        }
        # 레이더 차트: 지표 수에 따라 크기 결정
        height, size = _determine_chart_size(len(indicators), len(series), chart_type="radar")
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_treemap_chart(
        self,
        title: str,
        data: list[dict[str, Any]],
        max_depth: int = 3,
        top_n_per_level: int | None = None,
    ) -> HTMLReport:
        """트리맵 차트 - 대용량 계층 데이터에 적합

        Args:
            title: 차트 제목
            data: 계층 데이터. 예:
                [
                    {"name": "EC2", "value": 100, "children": [
                        {"name": "t3.micro", "value": 30},
                        {"name": "t3.small", "value": 70}
                    ]},
                    {"name": "RDS", "value": 50}
                ]
            max_depth: 최대 표시 깊이 (기본 3)
            top_n_per_level: 각 레벨에서 Top N만 표시 (None이면 전체)

        Tip:
            50개 이상의 계정/리소스가 있을 때 build_treemap_hierarchy()와 함께 사용:

            >>> data = build_treemap_hierarchy(
            ...     items,
            ...     group_keys=["account_name", "region", "service"],
            ...     value_key="count"
            ... )
            >>> report.add_treemap_chart("리소스 분포", data, top_n_per_level=10)
        """

        # Top N 필터링
        def filter_top_n(nodes: list[dict], n: int | None) -> list[dict]:
            if n is None or len(nodes) <= n:
                return nodes
            sorted_nodes = sorted(nodes, key=lambda x: x.get("value", 0), reverse=True)
            top = sorted_nodes[:n]
            others_value = sum(x.get("value", 0) for x in sorted_nodes[n:])
            if others_value > 0:
                top.append({"name": f"기타 ({len(sorted_nodes) - n}개)", "value": others_value})
            return top

        def process_level(nodes: list[dict], depth: int) -> list[dict]:
            if depth > max_depth:
                return [{"name": n.get("name"), "value": n.get("value", 0)} for n in nodes]

            result = []
            for node in nodes:
                new_node = {"name": node.get("name"), "value": node.get("value", 0)}
                if "children" in node and depth < max_depth:
                    children = filter_top_n(node["children"], top_n_per_level)
                    new_node["children"] = process_level(children, depth + 1)
                result.append(new_node)
            return result

        processed_data = filter_top_n(data, top_n_per_level)
        processed_data = process_level(processed_data, 1)

        option = {
            "title": {"text": title, "left": "center"},
            "tooltip": {"formatter": "{b}: {c}"},
            "color": COLORS,
            "animationThreshold": ANIMATION_THRESHOLD,
            "series": [
                {
                    "type": "treemap",
                    "data": processed_data,
                    "label": {"show": True, "formatter": "{b}"},
                    "upperLabel": {"show": True, "height": 30},
                    "breadcrumb": {"show": True},
                    "levels": [
                        {"itemStyle": {"borderWidth": 3, "borderColor": "#333", "gapWidth": 3}},
                        {"itemStyle": {"borderWidth": 2, "borderColor": "#555", "gapWidth": 2}},
                        {"itemStyle": {"borderWidth": 1, "gapWidth": 1}},
                    ],
                }
            ],
        }
        # 트리맵은 항상 넓은 공간 필요
        node_count = _count_treemap_nodes(processed_data)
        if node_count > 20:
            size = ChartSize.XLARGE
            height = 600
        else:
            size = ChartSize.LARGE
            height = 450
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_heatmap_chart(
        self,
        title: str,
        x_data: list[str],
        y_data: list[str],
        data: list[list[int | float]],
        min_val: int | float = 0,
        max_val: int | float | None = None,
    ) -> HTMLReport:
        """히트맵 차트

        Args:
            title: 차트 제목
            x_data: X축 카테고리
            y_data: Y축 카테고리
            data: 2차원 값 배열 또는 [x, y, value] 형태 리스트
            min_val: 최소값
            max_val: 최대값 (None이면 자동)
        """
        # [x, y, value] 형태로 변환
        if data and isinstance(data[0], list) and len(data[0]) == 3:
            heatmap_data = data
        else:
            heatmap_data = []
            for y_idx, row in enumerate(data):
                for x_idx, val in enumerate(row):
                    heatmap_data.append([x_idx, y_idx, val])

        if max_val is None:
            max_val = max(d[2] for d in heatmap_data) if heatmap_data else 100

        option = {
            "title": {"text": title},
            "tooltip": {"position": "top"},
            "grid": {"height": "60%", "top": "15%"},
            "xAxis": {"type": "category", "data": x_data, "splitArea": {"show": True}},
            "yAxis": {"type": "category", "data": y_data, "splitArea": {"show": True}},
            "visualMap": {
                "min": min_val,
                "max": max_val,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "5%",
            },
            "series": [
                {
                    "type": "heatmap",
                    "data": heatmap_data,
                    "label": {"show": True},
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}},
                }
            ],
        }
        # 히트맵: 데이터 크기에 따라 조정
        complexity = len(x_data) * len(y_data)
        height, size = _determine_chart_size(complexity, chart_type="heatmap")
        # 히트맵은 Y축 카테고리 수에 따라 높이 조정
        height = max(height, len(y_data) * 40 + 100)
        if len(x_data) > 10 or len(y_data) > 8:
            size = ChartSize.LARGE if size.value in ("small", "medium") else size
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_scatter_chart(
        self,
        title: str,
        series: list[tuple[str, list[tuple[float, float]]]],
        x_name: str = "X",
        y_name: str = "Y",
    ) -> HTMLReport:
        """산점도 차트

        Args:
            title: 차트 제목
            series: (시리즈명, [(x, y), ...]) 튜플 리스트
            x_name: X축 이름
            y_name: Y축 이름
        """
        series_list = []
        for name, points in series:
            series_list.append(
                {
                    "name": name,
                    "type": "scatter",
                    "data": points,
                    "symbolSize": 10,
                }
            )

        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "legend": {"top": 30},
            "color": COLORS,
            "xAxis": {"name": x_name, "type": "value"},
            "yAxis": {"name": y_name, "type": "value"},
            "series": series_list,
        }
        # 산점도: 데이터 포인트 수에 따라 크기 결정
        total_points = sum(len(points) for _, points in series)
        height, size = _determine_chart_size(total_points, len(series), chart_type="scatter")
        self.charts.append(ChartConfig(self._next_chart_id(), option, height=height, size=size))
        return self

    def add_time_series_chart(
        self,
        title: str,
        timestamps: list[datetime],
        values: list[int | float] | dict[str, list[int | float]],
        *,
        bucket_minutes: int | None = None,
        aggregation: str = "sum",
        area: bool = True,
        smooth: bool = True,
    ) -> HTMLReport:
        """CloudWatch 스타일 적응형 시계열 차트

        시간 범위에 따라 자동으로 해상도를 조절하여 효율적으로 표현합니다.

        Args:
            title: 차트 제목
            timestamps: datetime 리스트 (정렬 필요 없음)
            values: 값 리스트 (단일 시리즈) 또는 {시리즈명: 값 리스트} (다중 시리즈)
            bucket_minutes: 버킷 크기 (분). None이면 시간 범위에 따라 자동 결정:
                - ≤3시간: 5분
                - ≤24시간: 15분
                - ≤7일: 1시간
                - ≤30일: 4시간
                - >30일: 1일
            aggregation: 집계 방법 ("sum", "avg", "max", "min", "count")
            area: 영역 채우기 여부
            smooth: 곡선 여부

        Returns:
            self (체이닝 지원)

        Example:
            >>> report.add_time_series_chart(
            ...     "요청 트렌드",
            ...     timestamps=[datetime(2024, 1, 1, 10, 0), ...],
            ...     values=[100, 150, 200, ...],
            ... )

            # 다중 시리즈
            >>> report.add_time_series_chart(
            ...     "상태코드별 트렌드",
            ...     timestamps=timestamps,
            ...     values={"2xx": [...], "4xx": [...], "5xx": [...]},
            ... )
        """
        if not timestamps:
            return self

        # 단일 시리즈를 dict 형태로 통일
        if isinstance(values, list):
            series_data: dict[str, list[int | float]] = {"요청 수": values}
        else:
            series_data = values

        # 시간 범위 계산
        min_time = min(timestamps)
        max_time = max(timestamps)
        total_seconds = (max_time - min_time).total_seconds()
        total_hours = total_seconds / 3600

        # 자동 해상도 결정 (CloudWatch 스타일)
        if bucket_minutes is None:
            if total_hours <= 3:
                bucket_minutes = 5
            elif total_hours <= 24:
                bucket_minutes = 15
            elif total_hours <= 24 * 7:
                bucket_minutes = 60
            elif total_hours <= 24 * 30:
                bucket_minutes = 240
            else:
                bucket_minutes = 1440  # 1일

        bucket_seconds = bucket_minutes * 60

        # 시간을 버킷으로 그룹화
        from collections import defaultdict

        # 각 시리즈별로 버킷 데이터 수집
        buckets: dict[str, dict[datetime, list[float]]] = {name: defaultdict(list) for name in series_data}

        for i, ts in enumerate(timestamps):
            # 버킷 시작 시간 계산
            bucket_start = datetime.fromtimestamp((ts.timestamp() // bucket_seconds) * bucket_seconds)
            for name, vals in series_data.items():
                if i < len(vals):
                    buckets[name][bucket_start].append(vals[i])

        # 모든 시리즈의 버킷 키 통합
        all_bucket_keys: set[datetime] = set()
        for name_buckets in buckets.values():
            all_bucket_keys.update(name_buckets.keys())
        sorted_buckets = sorted(all_bucket_keys)

        if not sorted_buckets:
            return self

        # 집계 함수
        def aggregate_values(vals: list[float]) -> float:
            if not vals:
                return 0
            if aggregation == "sum":
                return sum(vals)
            elif aggregation == "avg":
                return sum(vals) / len(vals)
            elif aggregation == "max":
                return max(vals)
            elif aggregation == "min":
                return min(vals)
            elif aggregation == "count":
                return len(vals)
            return sum(vals)

        # 카테고리 라벨 생성 (시간 범위에 따라 포맷 변경)
        if total_hours <= 24:
            time_format = "%H:%M"
        elif total_hours <= 24 * 7:
            time_format = "%m/%d %H:%M"
        else:
            time_format = "%m/%d"

        categories = [ts.strftime(time_format) for ts in sorted_buckets]

        # 시리즈 데이터 생성
        chart_series: list[tuple[str, list[float]]] = []
        for name in series_data:
            aggregated = [aggregate_values(buckets[name].get(ts, [])) for ts in sorted_buckets]
            chart_series.append((name, aggregated))

        # 해상도 라벨 생성
        if bucket_minutes < 60:
            period_label = f"{bucket_minutes}분"
        elif bucket_minutes < 1440:
            period_label = f"{bucket_minutes // 60}시간"
        else:
            period_label = f"{bucket_minutes // 1440}일"

        chart_title = f"{title} ({period_label} 단위)"

        # add_line_chart 사용
        return self.add_line_chart(
            title=chart_title,
            categories=categories,
            series=chart_series,
            area=area,
            smooth=smooth,
        )

    def add_table(
        self,
        title: str,
        headers: list[str],
        rows: list[list[Any]],
        sortable: bool = True,
        searchable: bool = True,
        page_size: int = 20,
    ) -> HTMLReport:
        """테이블 추가

        Args:
            title: 테이블 제목
            headers: 헤더 리스트
            rows: 행 데이터 리스트
            sortable: 정렬 가능 여부
            searchable: 검색 가능 여부
            page_size: 페이지당 행 수
        """
        self.tables.append(
            {
                "title": title,
                "headers": headers,
                "rows": rows,
                "sortable": sortable,
                "searchable": searchable,
                "page_size": page_size,
            }
        )
        return self

    def save(self, filepath: str | Path, auto_open: bool = True) -> Path:
        """HTML 파일 저장 및 브라우저 열기"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        html = self._generate_html()
        path.write_text(html, encoding="utf-8")

        logger.info(f"HTML 리포트 저장: {path}")

        if auto_open:
            open_in_browser(str(path))

        return path

    def _generate_html(self) -> str:
        """HTML 생성"""
        charts_json = []
        for chart in self.charts:
            charts_json.append({"id": chart.chart_id, "option": chart.option, "height": chart.height})

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{
            zoom: 0.9;  /* Chrome, Safari, Edge */
            -moz-transform: scale(0.9);  /* Firefox */
            -moz-transform-origin: 0 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }}
        @-moz-document url-prefix() {{
            body {{ width: 111.11%; }}  /* Firefox: 100/0.9 = 111.11% to compensate for scale */
        }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}

        header {{
            background: linear-gradient(135deg, #5470c6 0%, #91cc75 100%);
            color: white;
            padding: 32px 40px;
            margin-bottom: 24px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(84, 112, 198, 0.3);
        }}
        header h1 {{ font-size: 32px; font-weight: 600; margin-bottom: 8px; }}
        header p {{ opacity: 0.9; font-size: 14px; }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .summary-card {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .summary-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
        .summary-card .label {{ font-size: 13px; color: #666; margin-bottom: 8px; font-weight: 500; }}
        .summary-card .value {{ font-size: 36px; font-weight: 700; }}
        .summary-card.danger .value {{ color: #ee6666; }}
        .summary-card.warning .value {{ color: #fac858; }}
        .summary-card.success .value {{ color: #91cc75; }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 24px;
        }}
        .chart-box {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .chart-box.small {{ }}
        .chart-box.medium {{ }}
        .chart-box.large {{ grid-column: 1 / -1; }}
        .chart-box.xlarge {{ grid-column: 1 / -1; }}
        .chart-container {{ width: 100%; }}

        .table-section {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            margin-bottom: 24px;
        }}
        .table-section h3 {{ margin-bottom: 16px; font-size: 18px; font-weight: 600; color: #333; }}
        .table-controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .search-input {{
            padding: 10px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            width: 280px;
            transition: border-color 0.2s;
        }}
        .search-input:focus {{ outline: none; border-color: #5470c6; }}
        .pagination {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .pagination button {{
            padding: 8px 12px;
            border: 1px solid #e0e0e0;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }}
        .pagination button:hover {{ background: #f5f5f5; }}
        .pagination button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .pagination span {{ font-size: 13px; color: #666; }}

        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th, td {{ padding: 14px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{
            background: #fafafa;
            font-weight: 600;
            color: #333;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        th:hover {{ background: #f0f0f0; }}
        th .sort-icon {{ margin-left: 6px; opacity: 0.4; font-size: 12px; }}
        tr:hover {{ background: #fafafa; }}
        td {{ color: #555; }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: #999;
            font-size: 12px;
        }}

        @media (max-width: 1000px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            .chart-box.large, .chart-box.xlarge {{ grid-column: auto; }}
        }}
        @media (max-width: 768px) {{
            .search-input {{ width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p>{self.subtitle or "AWS Automation Toolkit Report"} | {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </header>

        {self._generate_summary_html()}
        {self._generate_charts_html()}
        {self._generate_tables_html()}

        <div class="footer">
            Generated by AWS Automation Toolkit
        </div>
    </div>

    <script>
        // 차트 설정
        const chartsConfig = {json.dumps(charts_json, ensure_ascii=False)};

        // 차트 렌더링
        chartsConfig.forEach(config => {{
            const container = document.getElementById(config.id);
            if (container) {{
                container.style.height = config.height + 'px';
                const chart = echarts.init(container);
                chart.setOption(config.option);
                window.addEventListener('resize', () => chart.resize());
            }}
        }});

        // 테이블 기능
        document.querySelectorAll('.table-section').forEach(section => {{
            const tableId = section.querySelector('table').id;
            const searchInput = section.querySelector('.search-input');
            const tbody = section.querySelector('tbody');
            const allRows = Array.from(tbody.querySelectorAll('tr'));
            const pageSize = parseInt(section.dataset.pageSize) || 20;
            let currentPage = 1;
            let filteredRows = [...allRows];

            const pagInfo = section.querySelector('.page-info');
            const prevBtn = section.querySelector('.prev-btn');
            const nextBtn = section.querySelector('.next-btn');

            function render() {{
                const start = (currentPage - 1) * pageSize;
                const end = start + pageSize;
                const totalPages = Math.ceil(filteredRows.length / pageSize);

                allRows.forEach(r => r.style.display = 'none');
                filteredRows.slice(start, end).forEach(r => r.style.display = '');

                if (pagInfo) {{
                    pagInfo.textContent = `${{currentPage}} / ${{totalPages || 1}} (${{filteredRows.length}}건)`;
                }}
                if (prevBtn) prevBtn.disabled = currentPage <= 1;
                if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
            }}

            if (searchInput) {{
                searchInput.addEventListener('input', function() {{
                    const filter = this.value.toLowerCase();
                    filteredRows = allRows.filter(row =>
                        row.textContent.toLowerCase().includes(filter)
                    );
                    currentPage = 1;
                    render();
                }});
            }}

            if (prevBtn) prevBtn.addEventListener('click', () => {{ currentPage--; render(); }});
            if (nextBtn) nextBtn.addEventListener('click', () => {{ currentPage++; render(); }});

            // 정렬
            section.querySelectorAll('th[data-sortable]').forEach(th => {{
                th.addEventListener('click', function() {{
                    const col = this.cellIndex;
                    const asc = this.dataset.order !== 'asc';

                    filteredRows.sort((a, b) => {{
                        const aVal = a.cells[col]?.textContent || '';
                        const bVal = b.cells[col]?.textContent || '';
                        const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                        const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));

                        if (!isNaN(aNum) && !isNaN(bNum)) {{
                            return asc ? aNum - bNum : bNum - aNum;
                        }}
                        return asc ? aVal.localeCompare(bVal, 'ko') : bVal.localeCompare(aVal, 'ko');
                    }});

                    filteredRows.forEach(row => tbody.appendChild(row));
                    this.dataset.order = asc ? 'asc' : 'desc';

                    section.querySelectorAll('th .sort-icon').forEach(icon => icon.textContent = '↕');
                    this.querySelector('.sort-icon').textContent = asc ? '↑' : '↓';
                    currentPage = 1;
                    render();
                }});
            }});

            render();
        }});
    </script>
</body>
</html>"""

    def _generate_summary_html(self) -> str:
        if not self.summaries:
            return ""

        cards = []
        for summary in self.summaries:
            for label, value, color in summary["items"]:
                color_class = f" {color}" if color else ""
                cards.append(
                    f'<div class="summary-card{color_class}">'
                    f'<div class="label">{label}</div>'
                    f'<div class="value">{value}</div>'
                    f"</div>"
                )

        return f'<div class="summary-cards">{"".join(cards)}</div>'

    def _generate_charts_html(self) -> str:
        if not self.charts:
            return ""

        boxes = []
        for chart in self.charts:
            size_class = chart.size.value  # "small", "medium", "large", "xlarge"
            boxes.append(
                f'<div class="chart-box {size_class}"><div id="{chart.chart_id}" class="chart-container"></div></div>'
            )

        return f'<div class="charts-grid">{"".join(boxes)}</div>'

    def _generate_tables_html(self) -> str:
        if not self.tables:
            return ""

        tables_html = []
        for i, table in enumerate(self.tables):
            table_id = f"table_{i}"

            # 컨트롤
            controls = []
            if table["searchable"]:
                controls.append('<input type="text" class="search-input" placeholder="검색...">')
            controls.append(
                '<div class="pagination">'
                '<button class="prev-btn">◀ 이전</button>'
                '<span class="page-info">1 / 1</span>'
                '<button class="next-btn">다음 ▶</button>'
                "</div>"
            )

            # 헤더
            headers = []
            for h in table["headers"]:
                sortable = 'data-sortable="true"' if table["sortable"] else ""
                icon = '<span class="sort-icon">↕</span>' if table["sortable"] else ""
                headers.append(f"<th {sortable}>{h}{icon}</th>")

            # 행
            rows = []
            for row in table["rows"]:
                cells = "".join(f"<td>{c}</td>" for c in row)
                rows.append(f"<tr>{cells}</tr>")

            tables_html.append(
                f'<div class="table-section" data-page-size="{table["page_size"]}">'
                f"<h3>{table['title']}</h3>"
                f'<div class="table-controls">{"".join(controls)}</div>'
                f'<table id="{table_id}">'
                f"<thead><tr>{''.join(headers)}</tr></thead>"
                f"<tbody>{''.join(rows)}</tbody>"
                f"</table>"
                f"</div>"
            )

        return "".join(tables_html)
