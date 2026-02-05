# tests/cli/test_console_helpers.py
"""
cli/ui/console 새 헬퍼 함수 단위 테스트

Rich utility functions: print_rule, print_result_tree, print_error_tree,
print_stat_columns, print_execution_summary, print_results_json.
"""


from rich.panel import Panel

# =============================================================================
# print_rule 테스트
# =============================================================================


class TestPrintRule:
    """print_rule 테스트"""

    def test_rule_without_title(self):
        """제목 없는 구분선"""
        from cli.ui.console import print_rule

        # 에러 없이 실행되면 성공
        print_rule()

    def test_rule_with_title(self):
        """제목 있는 구분선"""
        from cli.ui.console import print_rule

        print_rule("종합 결과")

    def test_rule_with_custom_style(self):
        """커스텀 스타일"""
        from cli.ui.console import print_rule

        print_rule("결과", style="bold cyan")


# =============================================================================
# print_result_tree 테스트
# =============================================================================


class TestPrintResultTree:
    """print_result_tree 테스트"""

    def test_basic_tree(self):
        """기본 트리 출력"""
        from cli.ui.console import print_result_tree

        sections = [
            {"label": "EC2", "items": [("미사용", 5, "red"), ("저사용", 12, "yellow")]},
            {"label": "RDS", "items": [("미사용", 2, "red")]},
        ]
        print_result_tree("분석 결과", sections)

    def test_empty_sections(self):
        """빈 섹션 리스트"""
        from cli.ui.console import print_result_tree

        print_result_tree("결과", [])

    def test_section_without_items(self):
        """아이템 없는 섹션"""
        from cli.ui.console import print_result_tree

        sections = [{"label": "빈 섹션"}]
        print_result_tree("결과", sections)


# =============================================================================
# print_error_tree 테스트
# =============================================================================


class TestPrintErrorTree:
    """print_error_tree 테스트"""

    def test_basic_errors(self):
        """기본 에러 트리"""
        from cli.ui.console import print_error_tree

        errors = [
            ("AccessDenied", ["ap-northeast-2", "us-east-1"]),
            ("ThrottlingException", ["eu-west-1"]),
        ]
        print_error_tree(errors)

    def test_truncation(self):
        """3개 초과 시 truncation"""
        from cli.ui.console import print_error_tree

        errors = [
            ("AccessDenied", ["ap-northeast-2", "us-east-1", "eu-west-1", "us-west-2", "ap-southeast-1"]),
        ]
        print_error_tree(errors)

    def test_custom_title(self):
        """커스텀 제목"""
        from cli.ui.console import print_error_tree

        errors = [("Error", ["region-1"])]
        print_error_tree(errors, title="에러 목록")

    def test_empty_errors(self):
        """빈 에러 리스트"""
        from cli.ui.console import print_error_tree

        print_error_tree([])


# =============================================================================
# print_stat_columns 테스트
# =============================================================================


class TestPrintStatColumns:
    """print_stat_columns 테스트"""

    def test_two_panels(self):
        """두 개 패널"""
        from cli.ui.console import print_stat_columns

        print_stat_columns(
            Panel("10개", title="성공"),
            Panel("2개", title="실패"),
        )

    def test_three_panels(self):
        """세 개 패널"""
        from cli.ui.console import print_stat_columns

        print_stat_columns(
            Panel("10", title="성공"),
            Panel("2", title="실패"),
            Panel("12", title="전체"),
        )


# =============================================================================
# print_execution_summary 테스트
# =============================================================================


class TestPrintExecutionSummary:
    """print_execution_summary 테스트"""

    def test_full_summary(self):
        """전체 요약"""
        from cli.ui.console import print_execution_summary

        print_execution_summary(
            tool_name="미사용 EC2",
            profile="my-profile",
            regions=["ap-northeast-2", "us-east-1"],
            accounts=5,
        )

    def test_minimal_summary(self):
        """최소 요약 (도구 이름만)"""
        from cli.ui.console import print_execution_summary

        print_execution_summary(tool_name="미사용 EC2")

    def test_many_regions(self):
        """많은 리전 (4개 이상)"""
        from cli.ui.console import print_execution_summary

        regions = ["ap-northeast-2", "us-east-1", "eu-west-1", "ap-southeast-1"]
        print_execution_summary(tool_name="테스트", regions=regions)


# =============================================================================
# print_results_json 테스트
# =============================================================================


class TestPrintResultsJson:
    """print_results_json 테스트"""

    def test_basic_json(self):
        """기본 JSON 출력"""
        from cli.ui.console import print_results_json

        data = [{"name": "test", "value": 123}]
        print_results_json(data)

    def test_compact_json(self):
        """압축 JSON 출력"""
        from cli.ui.console import print_results_json

        data = [{"name": "test"}]
        print_results_json(data, pretty=False)

    def test_korean_json(self):
        """한글 JSON 출력"""
        from cli.ui.console import print_results_json

        data = [{"이름": "테스트", "상태": "성공"}]
        print_results_json(data)

    def test_empty_json(self):
        """빈 리스트 JSON 출력"""
        from cli.ui.console import print_results_json

        print_results_json([])


# =============================================================================
# print_tool_start / print_tool_complete (Rule 적용) 테스트
# =============================================================================


class TestToolStartComplete:
    """print_tool_start/complete Rule 적용 테스트"""

    def test_tool_start(self):
        """도구 시작 출력"""
        from cli.ui.console import print_tool_start

        print_tool_start("미사용 EC2", "EC2 미사용 인스턴스 검색")

    def test_tool_start_no_description(self):
        """설명 없는 도구 시작"""
        from cli.ui.console import print_tool_start

        print_tool_start("미사용 EC2")

    def test_tool_complete(self):
        """도구 완료 출력"""
        from cli.ui.console import print_tool_complete

        print_tool_complete(elapsed=1.5)

    def test_tool_complete_no_elapsed(self):
        """소요 시간 없는 도구 완료"""
        from cli.ui.console import print_tool_complete

        print_tool_complete()

    def test_tool_complete_custom_message(self):
        """커스텀 메시지"""
        from cli.ui.console import print_tool_complete

        print_tool_complete(message="분석 완료", elapsed=2.3)


# =============================================================================
# 모듈 Import 테스트
# =============================================================================


class TestModuleImports:
    """새 함수들이 cli.ui에서 import 가능한지 테스트"""

    def test_import_from_cli_ui(self):
        """cli.ui에서 import 가능"""
        from cli.ui import (
            print_error_tree,
            print_execution_summary,
            print_result_tree,
            print_results_json,
            print_rule,
            print_stat_columns,
        )

        assert callable(print_rule)
        assert callable(print_result_tree)
        assert callable(print_error_tree)
        assert callable(print_stat_columns)
        assert callable(print_execution_summary)
        assert callable(print_results_json)
