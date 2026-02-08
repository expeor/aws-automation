"""
tests/shared/io/html/test_report.py - HTML 리포트 테스트
"""

from datetime import datetime
from pathlib import Path

from core.shared.io.html import (
    ChartSize,
    HTMLReport,
    aggregate_by_group,
    build_treemap_hierarchy,
    group_top_n,
)


class TestGroupTopN:
    """group_top_n 함수 테스트"""

    def test_returns_all_when_under_limit(self):
        """Top N 이하면 모든 데이터 반환"""
        data = [("A", 100), ("B", 90), ("C", 80)]
        result = group_top_n(data, top_n=5)

        assert len(result) == 3
        assert result == data

    def test_groups_others_when_over_limit(self):
        """Top N 초과 시 기타로 그룹화"""
        data = [
            ("A", 100),
            ("B", 90),
            ("C", 80),
            ("D", 70),
            ("E", 60),
            ("F", 50),
            ("G", 40),
        ]
        result = group_top_n(data, top_n=3)

        assert len(result) == 4  # Top 3 + 기타
        assert result[0] == ("A", 100)
        assert result[1] == ("B", 90)
        assert result[2] == ("C", 80)
        # 기타: 70 + 60 + 50 + 40 = 220
        assert result[3][1] == 220
        assert "기타" in result[3][0]
        assert "(4개)" in result[3][0]

    def test_custom_others_label(self):
        """커스텀 기타 라벨"""
        data = [("A", 100), ("B", 90), ("C", 80), ("D", 70)]
        result = group_top_n(data, top_n=2, others_label="Others")

        assert "Others" in result[2][0]

    def test_without_count_in_label(self):
        """개수 없는 기타 라벨"""
        data = [("A", 100), ("B", 90), ("C", 80), ("D", 70)]
        result = group_top_n(data, top_n=2, include_others_count=False)

        assert result[2][0] == "기타"


class TestAggregateByGroup:
    """aggregate_by_group 함수 테스트"""

    def test_count_aggregation(self):
        """count 집계"""
        data = [
            {"region": "ap-northeast-2", "count": 10},
            {"region": "ap-northeast-2", "count": 20},
            {"region": "us-east-1", "count": 15},
        ]
        result = aggregate_by_group(data, group_key="region", aggregation="count")

        assert len(result) == 2
        # 정렬되어 ap-northeast-2가 먼저 (2개)
        assert result[0] == ("ap-northeast-2", 2)
        assert result[1] == ("us-east-1", 1)

    def test_sum_aggregation(self):
        """sum 집계"""
        data = [
            {"region": "ap-northeast-2", "count": 10},
            {"region": "ap-northeast-2", "count": 20},
            {"region": "us-east-1", "count": 15},
        ]
        result = aggregate_by_group(data, group_key="region", value_key="count", aggregation="sum")

        assert len(result) == 2
        # ap-northeast-2: 10 + 20 = 30
        assert result[0] == ("ap-northeast-2", 30)
        assert result[1] == ("us-east-1", 15)

    def test_avg_aggregation(self):
        """avg 집계"""
        data = [
            {"region": "ap-northeast-2", "count": 10},
            {"region": "ap-northeast-2", "count": 30},
        ]
        result = aggregate_by_group(data, group_key="region", value_key="count", aggregation="avg")

        assert result[0] == ("ap-northeast-2", 20.0)

    def test_unknown_group_key(self):
        """그룹 키 없으면 Unknown"""
        data = [{"other": "value"}]
        result = aggregate_by_group(data, group_key="region", aggregation="count")

        assert result[0][0] == "Unknown"


class TestBuildTreemapHierarchy:
    """build_treemap_hierarchy 함수 테스트"""

    def test_single_level(self):
        """단일 레벨 계층"""
        data = [
            {"account": "A", "count": 10},
            {"account": "A", "count": 20},
            {"account": "B", "count": 15},
        ]
        result = build_treemap_hierarchy(data, ["account"], "count")

        assert len(result) == 2
        # 정렬됨: A(30) > B(15)
        assert result[0]["name"] == "A"
        assert result[0]["value"] == 30
        assert result[1]["name"] == "B"
        assert result[1]["value"] == 15

    def test_multi_level(self):
        """다단계 계층"""
        data = [
            {"account": "A", "region": "ap-northeast-2", "count": 10},
            {"account": "A", "region": "us-east-1", "count": 5},
            {"account": "B", "region": "ap-northeast-2", "count": 8},
        ]
        result = build_treemap_hierarchy(data, ["account", "region"], "count")

        # A: 15 total
        assert result[0]["name"] == "A"
        assert result[0]["value"] == 15
        assert len(result[0]["children"]) == 2

        # A의 자식: ap-northeast-2(10) > us-east-1(5)
        assert result[0]["children"][0]["name"] == "ap-northeast-2"
        assert result[0]["children"][0]["value"] == 10

    def test_count_when_no_value_key(self):
        """value_key 없으면 count"""
        data = [
            {"account": "A"},
            {"account": "A"},
            {"account": "B"},
        ]
        result = build_treemap_hierarchy(data, ["account"])

        assert result[0]["value"] == 2  # A 개수
        assert result[1]["value"] == 1  # B 개수

    def test_empty_keys(self):
        """빈 그룹 키"""
        data = [{"account": "A"}]
        result = build_treemap_hierarchy(data, [])

        assert result == []


class TestChartSize:
    """ChartSize Enum 테스트"""

    def test_sizes(self):
        """크기 값 확인"""
        assert ChartSize.SMALL.value == "small"
        assert ChartSize.MEDIUM.value == "medium"
        assert ChartSize.LARGE.value == "large"
        assert ChartSize.XLARGE.value == "xlarge"


class TestHTMLReport:
    """HTMLReport 클래스 테스트"""

    def test_initialization(self):
        """초기화"""
        report = HTMLReport("테스트 리포트", "부제목")

        assert report.title == "테스트 리포트"
        assert report.subtitle == "부제목"
        assert report.charts == []
        assert report.tables == []
        assert report.summaries == []

    def test_add_summary(self):
        """요약 카드 추가"""
        report = HTMLReport("테스트")

        result = report.add_summary(
            [
                ("총 리소스", 100, None),
                ("미사용", 10, "danger"),
                ("예상 절감", "$500", "success"),
            ]
        )

        assert result is report  # 체이닝 지원
        assert len(report.summaries) == 1
        assert len(report.summaries[0]["items"]) == 3

    def test_add_pie_chart(self):
        """파이 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_pie_chart(
            title="분포",
            data=[("EC2", 45), ("RDS", 30), ("Lambda", 25)],
        )

        assert result is report
        assert len(report.charts) == 1
        assert report.charts[0].chart_id == "chart_1"

    def test_add_pie_chart_auto_groups_large_data(self):
        """파이 차트 대용량 데이터 자동 그룹화"""
        report = HTMLReport("테스트")

        # 10개 데이터 (6개 초과 시 자동 그룹화)
        data = [(f"Item{i}", i * 10) for i in range(10)]
        report.add_pie_chart("테스트", data)

        # 차트 옵션에서 series data 확인
        series_data = report.charts[0].option["series"][0]["data"]
        # Top 5 + 기타 = 6개
        assert len(series_data) == 6

    def test_add_bar_chart(self):
        """바 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_bar_chart(
            title="계정별 리소스",
            categories=["Account-1", "Account-2"],
            series=[("EC2", [10, 20]), ("RDS", [5, 15])],
        )

        assert result is report
        assert len(report.charts) == 1

    def test_add_bar_chart_horizontal_auto(self):
        """바 차트 가로 모드 자동 전환"""
        report = HTMLReport("테스트")

        # 10개 카테고리 (8개 이상 시 자동 가로)
        categories = [f"Account-{i}" for i in range(10)]
        report.add_bar_chart("테스트", categories, [("Count", list(range(10)))])

        # yAxis가 category여야 함 (가로 모드)
        assert report.charts[0].option["yAxis"]["type"] == "category"

    def test_add_line_chart(self):
        """라인 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_line_chart(
            title="트렌드",
            categories=["1월", "2월", "3월"],
            series=[("요청 수", [100, 150, 200])],
        )

        assert result is report
        assert len(report.charts) == 1

    def test_add_gauge_chart(self):
        """게이지 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_gauge_chart(
            title="사용률",
            value=75,
            max_value=100,
        )

        assert result is report
        assert len(report.charts) == 1

    def test_add_table(self):
        """테이블 추가"""
        report = HTMLReport("테스트")

        result = report.add_table(
            title="상세 데이터",
            headers=["계정", "리전", "리소스"],
            rows=[
                ["account-1", "ap-northeast-2", "i-12345"],
                ["account-2", "us-east-1", "i-67890"],
            ],
        )

        assert result is report
        assert len(report.tables) == 1
        assert report.tables[0]["title"] == "상세 데이터"
        assert len(report.tables[0]["headers"]) == 3
        assert len(report.tables[0]["rows"]) == 2

    def test_method_chaining(self):
        """메서드 체이닝"""
        report = HTMLReport("테스트")

        result = (
            report.add_summary([("총계", 100, None)])
            .add_pie_chart("분포", [("A", 50), ("B", 50)])
            .add_bar_chart("막대", ["X"], [("Y", [10])])
            .add_table("테이블", ["H1"], [["V1"]])
        )

        assert result is report
        assert len(report.summaries) == 1
        assert len(report.charts) == 2
        assert len(report.tables) == 1

    def test_save_creates_file(self, tmp_path):
        """파일 저장"""
        report = HTMLReport("테스트 리포트")
        report.add_summary([("항목", 100, None)])
        report.add_pie_chart("차트", [("A", 50), ("B", 50)])
        report.add_table("테이블", ["H1", "H2"], [["V1", "V2"]])

        filepath = report.save(tmp_path / "test_report.html", auto_open=False)

        assert Path(filepath).exists()
        assert str(filepath).endswith(".html")

        # 파일 내용 확인
        content = Path(filepath).read_text(encoding="utf-8")
        assert "테스트 리포트" in content
        assert "echarts" in content

    def test_generate_html_structure(self):
        """HTML 구조 생성"""
        report = HTMLReport("테스트 리포트", "부제목")
        report.add_summary([("항목", 100, None)])

        html = report._generate_html()

        assert "<!DOCTYPE html>" in html
        assert "테스트 리포트" in html
        assert "부제목" in html
        assert "echarts" in html

    def test_add_radar_chart(self):
        """레이더 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_radar_chart(
            title="역량 평가",
            indicators=[("보안", 100), ("비용", 100), ("성능", 100)],
            series=[("현재", [80, 70, 90])],
        )

        assert result is report
        assert len(report.charts) == 1

    def test_add_treemap_chart(self):
        """트리맵 차트 추가"""
        report = HTMLReport("테스트")

        data = [
            {
                "name": "EC2",
                "value": 100,
                "children": [
                    {"name": "t3.micro", "value": 30},
                    {"name": "t3.small", "value": 70},
                ],
            },
            {"name": "RDS", "value": 50},
        ]

        result = report.add_treemap_chart("리소스 분포", data)

        assert result is report
        assert len(report.charts) == 1

    def test_add_scatter_chart(self):
        """산점도 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_scatter_chart(
            title="상관관계",
            series=[("데이터", [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)])],
        )

        assert result is report
        assert len(report.charts) == 1

    def test_add_heatmap_chart(self):
        """히트맵 차트 추가"""
        report = HTMLReport("테스트")

        result = report.add_heatmap_chart(
            title="활동량",
            x_data=["월", "화", "수"],
            y_data=["오전", "오후"],
            data=[[10, 20, 30], [40, 50, 60]],
        )

        assert result is report
        assert len(report.charts) == 1


class TestHTMLReportTimeSeries:
    """시계열 차트 테스트"""

    def test_add_time_series_chart_basic(self):
        """기본 시계열 차트"""
        report = HTMLReport("테스트")

        timestamps = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 1, 10, 5),
            datetime(2024, 1, 1, 10, 10),
        ]
        values = [100, 150, 200]

        result = report.add_time_series_chart("요청 트렌드", timestamps, values)

        assert result is report
        assert len(report.charts) == 1

    def test_add_time_series_chart_multi_series(self):
        """다중 시리즈 시계열"""
        report = HTMLReport("테스트")

        timestamps = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 1, 10, 5),
        ]
        values = {
            "2xx": [100, 150],
            "4xx": [10, 15],
            "5xx": [1, 2],
        }

        result = report.add_time_series_chart("상태코드별", timestamps, values)

        assert result is report
        assert len(report.charts) == 1

    def test_add_time_series_empty_data(self):
        """빈 데이터 처리"""
        report = HTMLReport("테스트")

        result = report.add_time_series_chart("빈 데이터", [], [])

        assert result is report
        assert len(report.charts) == 0  # 빈 데이터면 차트 추가 안됨
