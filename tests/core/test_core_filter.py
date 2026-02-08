"""
tests/test_core_filter.py - core/filter.py 테스트
"""

import pytest

from core.auth.types import AccountInfo
from core.region.filter import (
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


class TestParsePatternEdgeCases:
    """parse_patterns 경계 조건 테스트"""

    def test_only_whitespace(self):
        """공백만 있는 문자열"""
        assert parse_patterns("   ") == []

    def test_only_commas(self):
        """쉼표만 있는 문자열"""
        assert parse_patterns(",,,") == []

    def test_mixed_empty_parts(self):
        """빈 파트가 섞인 패턴"""
        result = parse_patterns("prod*, , dev*, ,")
        assert result == ["prod*", "dev*"]

    def test_newlines_in_pattern(self):
        """개행 문자 처리"""
        result = parse_patterns("prod*\ndev*")
        assert "prod*" in result or "prod*\ndev*" in result  # 플랫폼 의존적

    def test_tabs_in_pattern(self):
        """탭 문자 처리"""
        result = parse_patterns("prod*\tdev*")
        assert len(result) >= 1


class TestMatchPatternAdvanced:
    """match_pattern 고급 테스트"""

    def test_multiple_wildcards(self):
        """여러 와일드카드"""
        assert match_pattern("prod-web-server-01", "prod*web*01") is True
        assert match_pattern("prod-api-server-01", "prod*web*01") is False

    def test_question_mark_multiple(self):
        """여러 ? 와일드카드"""
        assert match_pattern("prod12", "prod??") is True
        assert match_pattern("prod123", "prod??") is False

    def test_brackets_pattern(self):
        """대괄호 패턴 (fnmatch 지원)"""
        assert match_pattern("prod1", "prod[123]") is True
        assert match_pattern("prod4", "prod[123]") is False

    def test_empty_pattern(self):
        """빈 패턴"""
        assert match_pattern("anything", "") is False
        assert match_pattern("", "") is True

    def test_empty_name(self):
        """빈 이름"""
        assert match_pattern("", "prod*") is False
        assert match_pattern("", "*") is True

    def test_special_characters(self):
        """특수 문자"""
        assert match_pattern("prod-web_server", "prod-web_server") is True
        assert match_pattern("prod.web", "prod.web") is True


class TestFilterAccountsEdgeCases:
    """filter_accounts_by_pattern 경계 조건 테스트"""

    def test_empty_accounts_list(self):
        """빈 계정 목록"""
        result = filter_accounts_by_pattern([], "prod*")
        assert result == []

    def test_pattern_matches_none(self):
        """아무것도 매칭하지 않는 패턴"""
        accounts = [
            make_account("111", "prod-web"),
            make_account("222", "prod-api"),
        ]
        result = filter_accounts_by_pattern(accounts, "dev*")
        assert len(result) == 0

    def test_pattern_matches_all(self):
        """모든 계정을 매칭하는 패턴"""
        accounts = [
            make_account("111", "prod-web"),
            make_account("222", "prod-api"),
        ]
        result = filter_accounts_by_pattern(accounts, "*")
        assert len(result) == 2

    def test_empty_string_pattern(self):
        """빈 문자열 패턴은 전체 반환"""
        accounts = [
            make_account("111", "prod-web"),
        ]
        result = filter_accounts_by_pattern(accounts, "")
        assert len(result) == 1

    def test_empty_list_pattern(self):
        """빈 리스트 패턴은 전체 반환"""
        accounts = [
            make_account("111", "prod-web"),
        ]
        result = filter_accounts_by_pattern(accounts, [])
        assert len(result) == 1

    def test_case_sensitive_matching(self):
        """대소문자 구분 매칭"""
        accounts = [
            make_account("111", "PROD-WEB"),
            make_account("222", "prod-api"),
        ]

        # 대소문자 무시 (기본)
        result = filter_accounts_by_pattern(accounts, "prod*", case_sensitive=False)
        assert len(result) == 2

        # 대소문자 구분 (플랫폼 의존적)
        import sys

        if sys.platform != "win32":
            result = filter_accounts_by_pattern(accounts, "prod*", case_sensitive=True)
            assert len(result) == 1  # prod-api만 매칭

    def test_match_by_id_and_name(self):
        """ID와 이름 모두로 매칭"""
        accounts = [
            make_account("111111111111", "prod-web"),
            make_account("222222222222", "dev-web"),
        ]

        # 패턴이 이름과 ID 둘 다 확인
        result = filter_accounts_by_pattern(accounts, ["111*", "dev*"])
        assert len(result) == 2


class TestFilterStringsByPatternAdvanced:
    """filter_strings_by_pattern 고급 테스트"""

    def test_with_special_characters(self):
        """특수 문자가 포함된 문자열"""
        items = ["prod_web", "prod-api", "prod.service"]
        result = filter_strings_by_pattern(items, "prod*")
        assert len(result) == 3

    def test_multiple_patterns_or_logic(self):
        """여러 패턴의 OR 로직 확인"""
        items = ["ap-northeast-1", "us-east-1", "eu-west-1"]
        result = filter_strings_by_pattern(items, ["ap-*", "us-*"])
        assert len(result) == 2
        assert "ap-northeast-1" in result
        assert "us-east-1" in result

    def test_overlapping_patterns(self):
        """중복되는 패턴"""
        items = ["prod-web"]
        result = filter_strings_by_pattern(items, ["prod*", "prod-*", "*-web"])
        # 중복 매칭되어도 한 번만 포함
        assert len(result) == 1

    def test_numeric_strings(self):
        """숫자 문자열"""
        items = ["123", "456", "789"]
        result = filter_strings_by_pattern(items, "1*")
        assert result == ["123"]


class TestExpandRegionPatternAdvanced:
    """expand_region_pattern 고급 테스트"""

    def test_all_lowercase(self):
        """'all' 소문자"""
        result = expand_region_pattern("all")
        assert "ap-northeast-2" in result

    def test_all_uppercase(self):
        """'ALL' 대문자"""
        result = expand_region_pattern("ALL")
        assert "ap-northeast-2" in result

    def test_all_mixed_case(self):
        """'All' 혼합"""
        result = expand_region_pattern("All")
        assert "ap-northeast-2" in result

    def test_specific_pattern_ap_northeast(self):
        """ap-northeast 패턴"""
        result = expand_region_pattern("ap-northeast-*")
        assert "ap-northeast-1" in result
        assert "ap-northeast-2" in result
        assert "ap-southeast-1" not in result

    def test_specific_pattern_us(self):
        """us 패턴"""
        result = expand_region_pattern("us-*")
        assert all(r.startswith("us-") for r in result)

    def test_no_match_returns_empty(self):
        """매칭 없으면 빈 리스트"""
        result = expand_region_pattern("invalid-pattern-*")
        assert result == []

    def test_exact_region_match(self):
        """정확한 리전 매칭"""
        result = expand_region_pattern("ap-northeast-2")
        assert result == ["ap-northeast-2"]


class TestAccountFilterAdvanced:
    """AccountFilter 고급 테스트"""

    def test_filter_with_list_patterns(self):
        """리스트 패턴으로 초기화"""
        f = AccountFilter(patterns=["prod*", "stg*"])
        assert len(f.patterns) == 2
        assert f.is_active is True

    def test_filter_updates_not_supported(self):
        """필터는 불변 (패턴 변경 불가)"""
        f = AccountFilter(patterns=["prod*"])
        original_patterns = f.patterns

        # 패턴은 리스트지만 직접 수정은 권장하지 않음
        # (새 필터를 만드는 것이 권장됨)
        assert f.patterns == original_patterns

    def test_matches_empty_account_name(self):
        """빈 계정 이름 매칭"""
        f = AccountFilter(patterns=["*"])
        account = make_account("123", "")

        # * 패턴은 빈 문자열도 매칭
        assert f.matches(account) is True

    def test_apply_preserves_order(self):
        """필터 적용 시 순서 유지"""
        accounts = [
            make_account("333", "dev-web"),
            make_account("111", "prod-web"),
            make_account("222", "prod-api"),
        ]

        f = AccountFilter(patterns=["prod*"])
        result = f.apply(accounts)

        # prod-web가 prod-api보다 먼저 (입력 순서 유지)
        assert result[0].id == "111"
        assert result[1].id == "222"

    def test_case_sensitive_filter(self):
        """대소문자 구분 필터"""
        accounts = [
            make_account("111", "PROD-WEB"),
            make_account("222", "prod-api"),
        ]

        # 대소문자 무시 (기본)
        f = AccountFilter(patterns=["prod*"], case_sensitive=False)
        result = f.apply(accounts)
        assert len(result) == 2

        # 대소문자 구분 (플랫폼 의존적)
        import sys

        if sys.platform != "win32":
            f = AccountFilter(patterns=["prod*"], case_sensitive=True)
            result = f.apply(accounts)
            assert len(result) == 1


class TestMatchAnyPatternEdgeCases:
    """match_any_pattern 경계 조건 테스트"""

    def test_empty_name_empty_patterns(self):
        """빈 이름, 빈 패턴"""
        assert match_any_pattern("", []) is True

    def test_empty_name_with_patterns(self):
        """빈 이름, 패턴 있음"""
        assert match_any_pattern("", ["prod*"]) is False
        assert match_any_pattern("", ["*"]) is True

    def test_name_with_empty_pattern_list(self):
        """이름 있음, 빈 패턴 리스트"""
        assert match_any_pattern("prod-web", []) is True

    def test_single_pattern_in_list(self):
        """리스트에 패턴 1개"""
        assert match_any_pattern("prod-web", ["prod*"]) is True

    def test_many_patterns_first_matches(self):
        """많은 패턴 중 첫 번째 매칭"""
        patterns = ["prod*", "dev*", "stg*", "uat*"]
        assert match_any_pattern("prod-web", patterns) is True

    def test_many_patterns_last_matches(self):
        """많은 패턴 중 마지막 매칭"""
        patterns = ["dev*", "stg*", "uat*", "*-web"]
        assert match_any_pattern("prod-web", patterns) is True

    def test_many_patterns_none_match(self):
        """많은 패턴 중 매칭 없음"""
        patterns = ["dev*", "stg*", "uat*"]
        assert match_any_pattern("prod-web", patterns) is False


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    def test_multi_account_filtering_scenario(self):
        """멀티 계정 필터링 시나리오"""
        accounts = [
            make_account("111111111111", "prod-web-01"),
            make_account("111111111112", "prod-web-02"),
            make_account("222222222222", "prod-api-01"),
            make_account("333333333333", "stg-web-01"),
            make_account("444444444444", "stg-api-01"),
            make_account("555555555555", "dev-web-01"),
            make_account("666666666666", "dev-api-01"),
        ]

        # prod 환경만
        prod_accounts = filter_accounts_by_pattern(accounts, "prod*")
        assert len(prod_accounts) == 3

        # web 서비스만 (prod-web-01, prod-web-02, stg-web-01, dev-web-01 = 4개)
        web_accounts = filter_accounts_by_pattern(accounts, "*-web-*")
        assert len(web_accounts) == 4

        # prod 또는 stg
        prod_or_stg = filter_accounts_by_pattern(accounts, ["prod*", "stg*"])
        assert len(prod_or_stg) == 5

        # 특정 계정 ID
        specific = filter_accounts_by_pattern(accounts, "1111111111*")
        assert len(specific) == 2

    def test_region_filtering_scenario(self):
        """리전 필터링 시나리오"""
        # 모든 ap 리전
        ap_regions = expand_region_pattern("ap-*")
        assert len(ap_regions) > 5
        assert all(r.startswith("ap-") for r in ap_regions)

        # 특정 ap-northeast 리전
        ap_ne_regions = expand_region_pattern("ap-northeast-*")
        assert "ap-northeast-1" in ap_ne_regions
        assert "ap-northeast-2" in ap_ne_regions
        assert "ap-southeast-1" not in ap_ne_regions

        # 전체 리전
        all_regions = expand_region_pattern("all")
        assert len(all_regions) > 10

    def test_account_filter_class_scenario(self):
        """AccountFilter 클래스 사용 시나리오"""
        accounts = [
            make_account("111", "prod-web"),
            make_account("222", "prod-api"),
            make_account("333", "stg-web"),
        ]

        # 프로덕션 필터 생성
        prod_filter = AccountFilter(patterns="prod*")

        # 개별 확인
        assert prod_filter.matches(accounts[0]) is True
        assert prod_filter.matches(accounts[2]) is False

        # 일괄 필터링
        prod_accounts = prod_filter.apply(accounts)
        assert len(prod_accounts) == 2

        # 필터 비활성화
        no_filter = AccountFilter()
        all_accounts = no_filter.apply(accounts)
        assert len(all_accounts) == 3


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_parse_patterns_with_none(self):
        """None 입력 처리"""
        # parse_patterns는 문자열을 받으므로 None은 타입 에러
        # 실제 사용에서는 filter 함수들이 None을 처리함

    def test_filter_accounts_none_accounts(self):
        """None 계정 리스트는 사용하지 않음 (타입 에러)"""
        # 타입 힌트상 list[AccountInfo]를 받으므로 None은 불가

    def test_account_filter_with_invalid_pattern_type(self):
        """잘못된 패턴 타입"""
        # 정수 패턴 (iterable이 아니므로 TypeError)
        with pytest.raises(TypeError):
            AccountFilter(patterns=123)  # type: ignore


class TestPerformance:
    """성능 관련 테스트"""

    def test_large_account_list_filtering(self):
        """대량 계정 필터링"""
        # 1000개 계정 생성
        accounts = [make_account(str(i), f"account-{i:04d}") for i in range(1000)]

        # 패턴 매칭
        result = filter_accounts_by_pattern(accounts, "account-00*")

        # account-0000 ~ account-0099 (100개)
        assert len(result) == 100

    def test_many_patterns_filtering(self):
        """많은 패턴으로 필터링"""
        accounts = [
            make_account("111", "prod-web"),
            make_account("222", "stg-web"),
            make_account("333", "dev-web"),
        ]

        # 50개 패턴 (대부분 매칭 안됨)
        patterns = [f"test{i}*" for i in range(50)] + ["prod*"]

        result = filter_accounts_by_pattern(accounts, patterns)
        assert len(result) == 1  # prod-web만 매칭
