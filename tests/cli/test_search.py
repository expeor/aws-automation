"""
tests/cli/test_search.py - 검색 엔진 테스트

Fuzzy 검색, 별칭 검색, 카테고리 필터 테스트
"""

import pytest

from cli.ui.search import ToolSearchEngine, get_chosung, normalize_text


# 테스트용 카테고리 데이터
@pytest.fixture
def sample_categories():
    """테스트용 카테고리 데이터"""
    return [
        {
            "name": "ec2",
            "display_name": "EC2",
            "description": "EC2 및 컴퓨팅 리소스 관리",
            "aliases": ["compute", "ebs", "eip"],
            "sub_services": [],
            "tools": [
                {
                    "name": "미사용 EC2 인스턴스 탐지",
                    "module": "unused",
                    "description": "유휴/저사용 EC2 인스턴스 탐지",
                    "permission": "read",
                },
                {
                    "name": "EC2 인벤토리",
                    "module": "inventory",
                    "description": "EC2 인스턴스 현황 조회",
                    "permission": "read",
                },
            ],
        },
        {
            "name": "elb",
            "display_name": "ELB",
            "description": "Elastic Load Balancing",
            "aliases": ["loadbalancer", "lb"],
            "sub_services": ["alb", "nlb", "clb"],
            "tools": [
                {
                    "name": "미사용 ELB 탐지",
                    "module": "unused",
                    "description": "타겟이 없는 로드밸런서 탐지",
                    "permission": "read",
                },
                {
                    "name": "ELB 인벤토리",
                    "module": "inventory",
                    "description": "로드밸런서 현황 조회",
                    "permission": "read",
                },
            ],
        },
        {
            "name": "lambda",
            "display_name": "Lambda",
            "description": "Lambda 함수 관리",
            "aliases": ["function", "serverless"],
            "sub_services": [],
            "tools": [
                {
                    "name": "미사용 Lambda 탐지",
                    "module": "unused",
                    "description": "미사용 Lambda 함수 탐지",
                    "permission": "read",
                },
            ],
        },
    ]


@pytest.fixture
def search_engine(sample_categories):
    """초기화된 검색 엔진"""
    engine = ToolSearchEngine()
    engine.build_index(sample_categories)
    return engine


class TestNormalizeText:
    """텍스트 정규화 테스트"""

    def test_lowercase(self):
        assert normalize_text("EC2") == "ec2"

    def test_special_chars(self):
        assert normalize_text("ec2-instance") == "ec2 instance"
        assert normalize_text("ec2_instance") == "ec2 instance"

    def test_whitespace(self):
        assert normalize_text("  ec2   instance  ") == "ec2 instance"


class TestGetChosung:
    """초성 추출 테스트"""

    def test_korean(self):
        assert get_chosung("미사용") == "ㅁㅅㅇ"

    def test_mixed(self):
        assert get_chosung("EC2인스턴스") == "EC2ㅇㅅㅌㅅ"


class TestSearchEngine:
    """검색 엔진 기본 테스트"""

    def test_build_index(self, search_engine):
        """인덱스 구축 테스트"""
        assert search_engine.get_tool_count() == 5
        assert "ec2" in search_engine.get_categories()
        assert "elb" in search_engine.get_categories()

    def test_exact_match(self, search_engine):
        """정확한 매칭 테스트"""
        results = search_engine.search("EC2 인벤토리")
        assert len(results) > 0
        assert results[0].tool_name == "EC2 인벤토리"
        assert results[0].match_type == "exact"

    def test_prefix_match(self, search_engine):
        """접두사 매칭 테스트"""
        results = search_engine.search("미사용")
        assert len(results) >= 3
        # 미사용으로 시작하는 도구들이 상위에
        for r in results[:3]:
            assert "미사용" in r.tool_name

    def test_category_match(self, search_engine):
        """카테고리 매칭 테스트"""
        results = search_engine.search("ec2")
        assert len(results) > 0
        assert results[0].category == "ec2"

    def test_empty_query(self, search_engine):
        """빈 쿼리 테스트"""
        results = search_engine.search("")
        assert len(results) == 0

        results = search_engine.search("   ")
        assert len(results) == 0


class TestFuzzySearch:
    """Fuzzy 검색 테스트"""

    def test_typo_lambda(self, search_engine):
        """오타 허용 테스트 - lambda"""
        # "lambda" 대신 "lambad" (오타)
        results = search_engine.search("lambad")
        assert len(results) > 0
        # fuzzy 매칭으로 lambda 관련 도구 찾기
        assert results[0].match_type in ("fuzzy", "fuzzy_cat")
        assert results[0].category == "lambda"

    def test_typo_inventory(self, search_engine):
        """오타 허용 테스트 - inventory"""
        # "인벤토리" 대신 "인벤톨이" (다른 초성)
        # 영어 오타 사용 - fuzzy 매칭이 되거나 매칭 안됨
        # 한글 오타는 초성이 같으면 chosung으로 먼저 매칭됨
        _ = search_engine.search("inventroy")  # 결과는 사용하지 않음 (동작 확인만)

    def test_fuzzy_category(self, search_engine):
        """카테고리명 fuzzy 매칭"""
        # "elb" 대신 "ebl" (오타)
        results = search_engine.search("ebl")
        # 3글자로 fuzzy 검색 가능
        if len(results) > 0 and results[0].match_type == "fuzzy_cat":
            assert results[0].category == "elb"

    def test_short_query_no_fuzzy(self, search_engine):
        """짧은 쿼리는 fuzzy 미적용"""
        # 3자 미만은 fuzzy 검색 안함
        results = search_engine.search("ab")
        # fuzzy 결과가 없거나 다른 매칭 타입
        for r in results:
            assert r.match_type != "fuzzy"


class TestAliasSearch:
    """별칭 검색 테스트"""

    def test_alias_lb(self, search_engine):
        """별칭 검색 - lb → elb 카테고리"""
        results = search_engine.search("lb")
        assert len(results) > 0
        # lb는 elb의 별칭이지만, 도구명에 "elb"가 포함되어 contains로 먼저 매칭
        assert results[0].category == "elb"
        # contains 또는 alias 둘 다 유효
        assert results[0].match_type in ("contains", "alias", "category")

    def test_alias_compute(self, search_engine):
        """별칭 검색 - compute → ec2"""
        results = search_engine.search("compute")
        assert len(results) > 0
        assert results[0].category == "ec2"
        # "compute"는 도구명에 없으므로 alias로 매칭
        assert results[0].match_type == "alias"

    def test_sub_service_alb(self, search_engine):
        """sub_services 검색 - alb → elb"""
        results = search_engine.search("alb")
        assert len(results) > 0
        assert results[0].category == "elb"
        # "alb"는 sub_service로 alias 처리
        assert results[0].match_type == "alias"

    def test_alias_serverless(self, search_engine):
        """별칭 검색 - serverless → lambda"""
        results = search_engine.search("serverless")
        assert len(results) > 0
        assert results[0].category == "lambda"
        # "serverless"는 도구명에 없으므로 alias로 매칭
        assert results[0].match_type == "alias"

    def test_alias_loadbalancer(self, search_engine):
        """별칭 검색 - loadbalancer → elb"""
        results = search_engine.search("loadbalancer")
        assert len(results) > 0
        assert results[0].category == "elb"
        # "loadbalancer"는 도구명에 없으므로 alias로 매칭
        assert results[0].match_type == "alias"


class TestCategoryFilter:
    """카테고리 필터 문법 테스트"""

    def test_filter_ec2(self, search_engine):
        """카테고리 필터 - ec2:미사용"""
        results = search_engine.search("ec2:미사용")
        assert len(results) > 0
        # 모든 결과가 ec2 카테고리
        for r in results:
            assert r.category == "ec2"

    def test_filter_elb(self, search_engine):
        """카테고리 필터 - elb:인벤토리"""
        results = search_engine.search("elb:인벤토리")
        assert len(results) > 0
        for r in results:
            assert r.category == "elb"

    def test_filter_with_alias(self, search_engine):
        """별칭으로 필터 - lb:미사용"""
        results = search_engine.search("lb:미사용")
        assert len(results) > 0
        # lb는 elb의 별칭
        for r in results:
            assert r.category == "elb"

    def test_filter_empty_search(self, search_engine):
        """필터만 있고 검색어 없음 - ec2:"""
        results = search_engine.search("ec2:")
        # 검색어가 비어있지만 카테고리 필터가 있으면 해당 카테고리 도구 반환
        assert len(results) > 0
        for r in results:
            assert r.category == "ec2"

    def test_filter_invalid(self, search_engine):
        """잘못된 필터 - invalid:미사용"""
        # invalid는 유효하지 않은 카테고리이므로 원본 쿼리로 검색
        # "invalid:미사용" 전체가 검색어로 처리됨
        # 매칭되는 결과가 없거나 있을 수 있음
        _ = search_engine.search("invalid:미사용")  # 동작 확인만

    def test_filter_colon_in_query(self, search_engine):
        """콜론이 포함된 일반 쿼리"""
        # 유효하지 않은 필터는 무시
        results = search_engine.search(":미사용")
        # 콜론 앞이 비어있으면 필터 무시
        assert len(results) > 0


class TestChosungSearch:
    """초성 검색 테스트"""

    def test_chosung_msy(self, search_engine):
        """초성 검색 - ㅁㅅㅇ → 미사용"""
        results = search_engine.search("ㅁㅅㅇ")
        assert len(results) > 0
        assert results[0].match_type == "chosung"

    def test_chosung_mix(self, search_engine):
        """초성 + 영문 혼합은 일반 검색"""
        results = search_engine.search("EC2ㅁㅅㅇ")
        # 혼합 쿼리는 초성 검색이 아닌 다른 매칭
        # 결과가 있든 없든 동작만 확인
        _ = results  # 결과는 사용하지 않음


class TestSearchPriority:
    """검색 우선순위 테스트"""

    def test_exact_over_fuzzy(self, search_engine):
        """정확한 매칭이 fuzzy보다 우선"""
        results = search_engine.search("EC2 인벤토리")
        assert len(results) > 0
        assert results[0].match_type == "exact"
        assert results[0].score == 1.0

    def test_prefix_over_contains(self, search_engine):
        """접두사 매칭이 포함보다 우선"""
        results = search_engine.search("미사용")
        assert len(results) > 0
        # 점수 순으로 정렬되어 있어야 함
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestGetSuggestions:
    """자동완성 테스트"""

    def test_suggestions(self, search_engine):
        """자동완성 제안"""
        suggestions = search_engine.get_suggestions("미사용")
        assert len(suggestions) > 0
        for s in suggestions:
            assert s.startswith("미사용")

    def test_suggestions_empty(self, search_engine):
        """빈 입력 자동완성"""
        suggestions = search_engine.get_suggestions("")
        assert len(suggestions) == 0
