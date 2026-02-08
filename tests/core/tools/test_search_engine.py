"""
tests/test_search_engine.py - 검색 엔진 테스트
"""

import pytest

from core.cli.ui.search import SearchResult, ToolSearchEngine, get_chosung, normalize_text


class TestTextUtils:
    """텍스트 유틸리티 테스트"""

    def test_get_chosung_korean(self):
        """한글 초성 추출"""
        assert get_chosung("미사용") == "ㅁㅅㅇ"
        assert get_chosung("볼륨") == "ㅂㄹ"
        assert get_chosung("인스턴스") == "ㅇㅅㅌㅅ"

    def test_get_chosung_mixed(self):
        """혼합 텍스트 초성 추출"""
        assert get_chosung("EBS 볼륨") == "EBS ㅂㄹ"
        assert get_chosung("IAM 사용자") == "IAM ㅅㅇㅈ"

    def test_normalize_text(self):
        """텍스트 정규화"""
        assert normalize_text("Hello_World") == "hello world"
        assert normalize_text("test-case") == "test case"
        assert normalize_text("  Multiple   Spaces  ") == "multiple spaces"


class TestToolSearchEngine:
    """검색 엔진 테스트"""

    @pytest.fixture
    def sample_categories(self):
        """샘플 카테고리 데이터"""
        return [
            {
                "name": "ebs",
                "description": "EBS 볼륨 분석",
                "tools": [
                    {
                        "name": "미사용 볼륨",
                        "module": "unused",
                        "description": "미사용 EBS 볼륨 탐지",
                        "permission": "read",
                    },
                    {
                        "name": "스냅샷 분석",
                        "module": "snapshots",
                        "description": "EBS 스냅샷 분석",
                        "permission": "read",
                    },
                ],
            },
            {
                "name": "ec2",
                "description": "EC2 인스턴스 관리",
                "tools": [
                    {
                        "name": "인스턴스 목록",
                        "module": "instances",
                        "description": "EC2 인스턴스 목록 조회",
                        "permission": "read",
                    },
                    {
                        "name": "미사용 AMI",
                        "module": "unused_ami",
                        "description": "미사용 AMI 이미지 탐지",
                        "permission": "read",
                    },
                ],
            },
            {
                "name": "iam",
                "description": "IAM 사용자/역할",
                "tools": [
                    {
                        "name": "사용자 분석",
                        "module": "users",
                        "description": "IAM 사용자 분석",
                        "permission": "read",
                    },
                ],
            },
        ]

    @pytest.fixture
    def engine(self, sample_categories):
        """검색 엔진 인스턴스"""
        engine = ToolSearchEngine()
        engine.build_index(sample_categories)
        return engine

    def test_build_index(self, engine):
        """인덱스 구축"""
        assert engine.get_tool_count() == 5
        assert len(engine.get_categories()) == 3

    def test_search_exact_match(self, engine):
        """정확한 일치 검색"""
        results = engine.search("미사용 볼륨")
        assert len(results) > 0
        assert results[0].tool_name == "미사용 볼륨"
        assert results[0].score == 1.0
        assert results[0].match_type == "exact"

    def test_search_contains(self, engine):
        """포함 검색"""
        results = engine.search("미사용")
        assert len(results) >= 2
        # 미사용 볼륨, 미사용 AMI

    def test_search_category(self, engine):
        """카테고리 검색"""
        results = engine.search("ebs")
        assert len(results) == 2  # ebs 카테고리의 모든 도구

    def test_search_description(self, engine):
        """설명 검색"""
        results = engine.search("탐지")
        assert len(results) >= 2  # 탐지 포함된 도구들

    def test_search_no_results(self, engine):
        """검색 결과 없음"""
        results = engine.search("존재하지않는키워드")
        assert len(results) == 0

    def test_search_empty_query(self, engine):
        """빈 쿼리"""
        results = engine.search("")
        assert len(results) == 0

        results = engine.search("   ")
        assert len(results) == 0

    def test_search_limit(self, engine):
        """검색 결과 제한"""
        results = engine.search("미사용", limit=1)
        assert len(results) == 1

    def test_search_category_filter(self, engine):
        """카테고리 필터"""
        results = engine.search("미사용", category_filter="ebs")
        assert len(results) == 1
        assert results[0].category == "ebs"

    def test_chosung_search(self, engine):
        """초성 검색"""
        results = engine.search("ㅁㅅㅇ")  # 미사용
        # 초성 검색 결과가 있어야 함
        assert len(results) > 0

    def test_get_suggestions(self, engine):
        """자동완성 제안"""
        suggestions = engine.get_suggestions("미사용")
        assert len(suggestions) > 0
        assert all("미사용" in s for s in suggestions)

    def test_search_result_structure(self, engine):
        """검색 결과 구조"""
        results = engine.search("볼륨")
        assert len(results) > 0

        result = results[0]
        assert isinstance(result, SearchResult)
        assert hasattr(result, "tool_name")
        assert hasattr(result, "tool_module")
        assert hasattr(result, "category")
        assert hasattr(result, "description")
        assert hasattr(result, "permission")
        assert hasattr(result, "score")
        assert hasattr(result, "match_type")
