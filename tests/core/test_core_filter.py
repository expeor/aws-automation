"""
tests/test_core_filter.py - core/filter.py 테스트
"""


import pytest

from core.auth.types import AccountInfo
from core.filter import (
    AccountFilter,
    expand_region_pattern,
    filter_accounts_by_pattern,
    filter_strings_by_pattern,
    match_any_pattern,
    match_pattern,
    parse_patterns,
)


def make_account(id: str, name: str) -> AccountInfo:
    """테스트용 AccountInfo 생성"""
    return AccountInfo(id=id, name=name)


class TestParsePatterns:
    """parse_patterns 테스트"""

    def test_empty_string(self):
        """빈 문자열"""
        assert parse_patterns("") == []

    def test_single_pattern(self):
        """단일 패턴"""
        assert parse_patterns("prod*") == ["prod*"]

    def test_comma_separated(self):
        """쉼표로 구분된 패턴"""
        assert parse_patterns("prod*, dev-*, stg-*") == ["prod*", "dev-*", "stg-*"]

    def test_space_separated(self):
        """공백으로 구분된 패턴"""
        assert parse_patterns("prod* dev-*") == ["prod*", "dev-*"]

    def test_mixed_separators(self):
        """혼합 구분자"""
        result = parse_patterns("prod*, dev-* stg-*")
        assert result == ["prod*", "dev-*", "stg-*"]

    def test_extra_whitespace(self):
        """추가 공백 처리"""
        result = parse_patterns("  prod*  ,  dev-*  ")
        assert result == ["prod*", "dev-*"]


class TestMatchPattern:
    """match_pattern 테스트"""

    def test_exact_match(self):
        """정확한 매칭"""
        assert match_pattern("prod-web", "prod-web") is True

    def test_wildcard_prefix(self):
        """접두사 와일드카드"""
        assert match_pattern("prod-web", "prod*") is True
        assert match_pattern("dev-web", "prod*") is False

    def test_wildcard_suffix(self):
        """접미사 와일드카드"""
        assert match_pattern("prod-web", "*-web") is True
        assert match_pattern("prod-api", "*-web") is False

    def test_wildcard_middle(self):
        """중간 와일드카드"""
        assert match_pattern("prod-web-server", "prod*server") is True

    def test_question_mark(self):
        """단일 문자 와일드카드"""
        assert match_pattern("prod1", "prod?") is True
        assert match_pattern("prod12", "prod?") is False

    def test_case_insensitive(self):
        """대소문자 무시"""
        assert match_pattern("PROD-WEB", "prod*", case_sensitive=False) is True
        assert match_pattern("prod-web", "PROD*", case_sensitive=False) is True

    def test_case_sensitive(self):
        """대소문자 구분 (플랫폼 의존적)"""
        # Windows에서 fnmatch는 대소문자를 구분하지 않음
        # case_sensitive=True일 때 소문자 변환을 하지 않지만,
        # fnmatch 자체가 플랫폼 의존적
        import sys

        if sys.platform != "win32":
            assert match_pattern("PROD-WEB", "prod*", case_sensitive=True) is False
        # 소문자는 항상 매칭
        assert match_pattern("prod-web", "prod*", case_sensitive=True) is True


class TestMatchAnyPattern:
    """match_any_pattern 테스트"""

    def test_empty_patterns(self):
        """패턴이 없으면 전체 선택"""
        assert match_any_pattern("anything", []) is True

    def test_single_pattern_match(self):
        """단일 패턴 매칭"""
        assert match_any_pattern("prod-web", ["prod*"]) is True
        assert match_any_pattern("dev-web", ["prod*"]) is False

    def test_multiple_patterns_or(self):
        """여러 패턴 OR 조건"""
        patterns = ["prod*", "stg*"]
        assert match_any_pattern("prod-web", patterns) is True
        assert match_any_pattern("stg-web", patterns) is True
        assert match_any_pattern("dev-web", patterns) is False

    def test_no_match(self):
        """매칭 없음"""
        assert match_any_pattern("dev", ["prod*", "stg*"]) is False


class TestFilterAccountsByPattern:
    """filter_accounts_by_pattern 테스트"""

    @pytest.fixture
    def accounts(self):
        """테스트용 계정 목록"""
        return [
            make_account("111111111111", "prod-web"),
            make_account("222222222222", "prod-api"),
            make_account("333333333333", "dev-web"),
            make_account("444444444444", "stg-web"),
        ]

    def test_none_pattern_returns_all(self, accounts):
        """None 패턴이면 전체 반환"""
        result = filter_accounts_by_pattern(accounts, None)
        assert len(result) == 4

    def test_empty_pattern_returns_all(self, accounts):
        """빈 패턴이면 전체 반환"""
        result = filter_accounts_by_pattern(accounts, "")
        assert len(result) == 4

    def test_single_pattern_string(self, accounts):
        """단일 패턴 문자열"""
        result = filter_accounts_by_pattern(accounts, "prod*")
        assert len(result) == 2
        assert all("prod" in a.name for a in result)

    def test_multiple_patterns_list(self, accounts):
        """여러 패턴 리스트"""
        result = filter_accounts_by_pattern(accounts, ["prod*", "dev*"])
        assert len(result) == 3

    def test_comma_separated_string(self, accounts):
        """쉼표로 구분된 문자열"""
        result = filter_accounts_by_pattern(accounts, "prod*, stg*")
        assert len(result) == 3

    def test_filter_by_id(self, accounts):
        """계정 ID로 필터링"""
        result = filter_accounts_by_pattern(accounts, "111*")
        assert len(result) == 1
        assert result[0].id == "111111111111"

    def test_suffix_pattern(self, accounts):
        """접미사 패턴"""
        result = filter_accounts_by_pattern(accounts, "*-web")
        assert len(result) == 3

    def test_no_match(self, accounts):
        """매칭 없음"""
        result = filter_accounts_by_pattern(accounts, "uat*")
        assert len(result) == 0


class TestFilterStringsByPattern:
    """filter_strings_by_pattern 테스트"""

    @pytest.fixture
    def regions(self):
        """테스트용 리전 목록"""
        return ["ap-northeast-1", "ap-northeast-2", "us-east-1", "eu-west-1"]

    def test_none_pattern_returns_all(self, regions):
        """None 패턴이면 전체 반환"""
        result = filter_strings_by_pattern(regions, None)
        assert len(result) == 4

    def test_prefix_pattern(self, regions):
        """접두사 패턴"""
        result = filter_strings_by_pattern(regions, "ap-*")
        assert len(result) == 2
        assert all(r.startswith("ap-") for r in result)

    def test_multiple_patterns(self, regions):
        """여러 패턴"""
        result = filter_strings_by_pattern(regions, ["ap-*", "us-*"])
        assert len(result) == 3


class TestExpandRegionPattern:
    """expand_region_pattern 테스트"""

    def test_all_pattern(self):
        """'all' 패턴"""
        result = expand_region_pattern("all")
        assert len(result) > 10
        assert "ap-northeast-2" in result
        assert "us-east-1" in result

    def test_prefix_pattern(self):
        """접두사 패턴"""
        result = expand_region_pattern("ap-*")
        assert all(r.startswith("ap-") for r in result)
        assert "ap-northeast-2" in result

    def test_specific_region(self):
        """특정 리전"""
        result = expand_region_pattern("us-east-1")
        assert "us-east-1" in result


class TestAccountFilter:
    """AccountFilter 클래스 테스트"""

    @pytest.fixture
    def accounts(self):
        """테스트용 계정 목록"""
        return [
            make_account("111111111111", "prod-web"),
            make_account("222222222222", "prod-api"),
            make_account("333333333333", "dev-web"),
        ]

    def test_inactive_filter_no_patterns(self):
        """패턴 없으면 비활성"""
        f = AccountFilter(patterns=None)
        assert f.is_active is False

    def test_inactive_filter_empty_patterns(self):
        """빈 패턴 리스트면 비활성"""
        f = AccountFilter(patterns=[])
        assert f.is_active is False

    def test_active_filter(self):
        """패턴 있으면 활성"""
        f = AccountFilter(patterns=["prod*"])
        assert f.is_active is True

    def test_string_pattern_parsing(self):
        """문자열 패턴 파싱"""
        f = AccountFilter(patterns="prod*, dev*")
        assert f.patterns == ["prod*", "dev*"]

    def test_matches_by_name(self, accounts):
        """이름으로 매칭"""
        f = AccountFilter(patterns=["prod*"])
        assert f.matches(accounts[0]) is True
        assert f.matches(accounts[2]) is False

    def test_matches_by_id(self, accounts):
        """ID로 매칭"""
        f = AccountFilter(patterns=["111*"])
        assert f.matches(accounts[0]) is True
        assert f.matches(accounts[1]) is False

    def test_inactive_matches_all(self, accounts):
        """비활성 필터는 전체 매칭"""
        f = AccountFilter()
        for acc in accounts:
            assert f.matches(acc) is True

    def test_apply(self, accounts):
        """필터 적용"""
        f = AccountFilter(patterns=["prod*"])
        result = f.apply(accounts)
        assert len(result) == 2

    def test_apply_inactive(self, accounts):
        """비활성 필터 적용"""
        f = AccountFilter()
        result = f.apply(accounts)
        assert len(result) == 3

    def test_repr_inactive(self):
        """repr - 비활성"""
        f = AccountFilter()
        assert "inactive" in repr(f)

    def test_repr_active(self):
        """repr - 활성"""
        f = AccountFilter(patterns=["prod*"])
        assert "patterns" in repr(f)
        assert "prod*" in repr(f)
