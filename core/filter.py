"""
core/filter.py - 계정/리소스 필터링

glob 패턴 기반 계정 필터링 기능을 제공합니다.
Headless CLI의 --target 옵션 구현에 사용됩니다.

Example:
    from core.filter import filter_accounts_by_pattern, parse_patterns

    # 단일 패턴
    filtered = filter_accounts_by_pattern(accounts, "prod*")

    # 다중 패턴 (OR 조건)
    filtered = filter_accounts_by_pattern(accounts, ["prod*", "stg-*"])

    # 문자열 파싱
    patterns = parse_patterns("prod*, dev-web, *-api")
    filtered = filter_accounts_by_pattern(accounts, patterns)
"""

import fnmatch
from collections.abc import Sequence

from core.auth.types import AccountInfo


def parse_patterns(pattern_str: str) -> list[str]:
    """패턴 문자열을 리스트로 파싱

    쉼표 또는 공백으로 구분된 패턴 문자열을 리스트로 변환합니다.

    Args:
        pattern_str: 패턴 문자열 (예: "prod*, dev-*" 또는 "prod* dev-*")

    Returns:
        패턴 리스트

    Example:
        >>> parse_patterns("prod*, dev-*, stg-*")
        ['prod*', 'dev-*', 'stg-*']

        >>> parse_patterns("prod*  dev-*")
        ['prod*', 'dev-*']
    """
    if not pattern_str:
        return []

    # 쉼표로 먼저 분리
    parts = pattern_str.split(",")

    patterns = []
    for part in parts:
        # 각 파트를 공백으로 분리
        for p in part.split():
            p = p.strip()
            if p:
                patterns.append(p)

    return patterns


def match_pattern(name: str, pattern: str, case_sensitive: bool = False) -> bool:
    """단일 패턴 매칭

    Args:
        name: 매칭할 이름
        pattern: glob 패턴 (*, ? 지원)
        case_sensitive: 대소문자 구분 여부 (기본: False)

    Returns:
        매칭되면 True

    Example:
        >>> match_pattern("prod-web", "prod*")
        True
        >>> match_pattern("dev-api", "*-api")
        True
        >>> match_pattern("staging", "stg*")
        False
    """
    if not case_sensitive:
        name = name.lower()
        pattern = pattern.lower()

    return fnmatch.fnmatch(name, pattern)


def match_any_pattern(
    name: str,
    patterns: Sequence[str],
    case_sensitive: bool = False,
) -> bool:
    """여러 패턴 중 하나라도 매칭되는지 확인 (OR 조건)

    Args:
        name: 매칭할 이름
        patterns: glob 패턴 리스트
        case_sensitive: 대소문자 구분 여부

    Returns:
        하나라도 매칭되면 True
    """
    if not patterns:
        return True  # 패턴 없으면 전체 선택

    return any(match_pattern(name, pattern, case_sensitive) for pattern in patterns)


def filter_accounts_by_pattern(
    accounts: list[AccountInfo],
    patterns: str | list[str] | None,
    case_sensitive: bool = False,
) -> list[AccountInfo]:
    """패턴으로 계정 필터링

    계정 이름(name) 또는 ID에 대해 glob 패턴 매칭을 수행합니다.

    Args:
        accounts: 계정 목록
        patterns: 패턴 또는 패턴 리스트 (None이면 전체 반환)
        case_sensitive: 대소문자 구분 여부

    Returns:
        필터링된 계정 목록

    Example:
        >>> accounts = [
        ...     AccountInfo(id="111", name="prod-web"),
        ...     AccountInfo(id="222", name="prod-api"),
        ...     AccountInfo(id="333", name="dev-web"),
        ... ]

        # prod로 시작하는 계정
        >>> filter_accounts_by_pattern(accounts, "prod*")
        [AccountInfo(id="111", ...), AccountInfo(id="222", ...)]

        # 여러 패턴 (OR 조건)
        >>> filter_accounts_by_pattern(accounts, ["prod*", "*-web"])
        [AccountInfo(id="111", ...), AccountInfo(id="222", ...), AccountInfo(id="333", ...)]
    """
    if patterns is None:
        return accounts

    # 문자열이면 파싱
    if isinstance(patterns, str):
        patterns = parse_patterns(patterns)

    if not patterns:
        return accounts

    result = []
    for account in accounts:
        # 이름으로 매칭
        if match_any_pattern(account.name, patterns, case_sensitive) or match_any_pattern(
            account.id, patterns, case_sensitive
        ):
            result.append(account)

    return result


def filter_strings_by_pattern(
    items: list[str],
    patterns: str | list[str] | None,
    case_sensitive: bool = False,
) -> list[str]:
    """문자열 리스트를 패턴으로 필터링

    프로파일명, 리전명 등 문자열 리스트 필터링에 사용합니다.

    Args:
        items: 문자열 리스트
        patterns: 패턴 또는 패턴 리스트
        case_sensitive: 대소문자 구분 여부

    Returns:
        필터링된 문자열 리스트

    Example:
        >>> regions = ["ap-northeast-1", "ap-northeast-2", "us-east-1"]
        >>> filter_strings_by_pattern(regions, "ap-*")
        ['ap-northeast-1', 'ap-northeast-2']
    """
    if patterns is None:
        return items

    if isinstance(patterns, str):
        patterns = parse_patterns(patterns)

    if not patterns:
        return items

    return [item for item in items if match_any_pattern(item, patterns, case_sensitive)]


def expand_region_pattern(pattern: str) -> list[str]:
    """리전 패턴을 실제 리전 목록으로 확장

    Args:
        pattern: 리전 패턴 (예: "ap-*", "all", "us-east-*")

    Returns:
        매칭되는 리전 목록

    Example:
        >>> expand_region_pattern("ap-northeast-*")
        ['ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3']

        >>> expand_region_pattern("all")
        ['us-east-1', 'us-east-2', ..., 'ap-northeast-2', ...]
    """
    from core.region import ALL_REGIONS

    if pattern.lower() == "all":
        return list(ALL_REGIONS)

    return filter_strings_by_pattern(list(ALL_REGIONS), pattern)


class AccountFilter:
    """계정 필터 클래스

    패턴 기반 필터링을 캡슐화합니다.

    Example:
        filter = AccountFilter(patterns=["prod*", "stg-*"])

        # 개별 확인
        if filter.matches(account):
            ...

        # 일괄 필터링
        filtered = filter.apply(accounts)
    """

    def __init__(
        self,
        patterns: str | list[str] | None = None,
        case_sensitive: bool = False,
    ):
        """초기화

        Args:
            patterns: 패턴 또는 패턴 리스트
            case_sensitive: 대소문자 구분 여부
        """
        self.case_sensitive = case_sensitive

        if patterns is None:
            self.patterns: list[str] = []
        elif isinstance(patterns, str):
            self.patterns = parse_patterns(patterns)
        else:
            self.patterns = list(patterns)

    @property
    def is_active(self) -> bool:
        """필터가 활성화되어 있는지"""
        return len(self.patterns) > 0

    def matches(self, account: AccountInfo) -> bool:
        """계정이 패턴과 매칭되는지 확인"""
        if not self.is_active:
            return True

        if match_any_pattern(account.name, self.patterns, self.case_sensitive):
            return True
        return bool(match_any_pattern(account.id, self.patterns, self.case_sensitive))

    def apply(self, accounts: list[AccountInfo]) -> list[AccountInfo]:
        """계정 목록에 필터 적용"""
        if not self.is_active:
            return accounts

        return [acc for acc in accounts if self.matches(acc)]

    def __repr__(self) -> str:
        if not self.is_active:
            return "AccountFilter(inactive)"
        return f"AccountFilter(patterns={self.patterns})"
