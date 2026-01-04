"""
AWS 계정 정보 유틸리티

Account Alias, Account ID, Account Name 조회 및 표시용 식별자 생성.
모든 도구에서 공통으로 사용.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext


def get_account_display_name(session, fallback: str = "unknown") -> str:
    """Account Alias 또는 Account ID 반환 (표시용)

    Note:
        SSO 환경에서는 get_account_display_name_from_ctx() 사용 권장.
        ctx.accounts에서 Account Name을 가져올 수 있어 API 호출 불필요.

    Args:
        session: boto3 Session
        fallback: 조회 실패 시 반환할 기본값

    Returns:
        Account Alias (있으면) 또는 Account ID

    Example:
        >>> name = get_account_display_name(session)
        >>> print(name)  # "my-account-alias" 또는 "123456789012"
    """
    try:
        # 1. Account Alias 조회 시도
        iam = session.client("iam")
        aliases = iam.list_account_aliases().get("AccountAliases", [])
        if aliases:
            alias: str = aliases[0]
            return alias

        # 2. Alias 없으면 Account ID 반환
        sts = session.client("sts")
        account_id: str = sts.get_caller_identity()["Account"]
        return account_id
    except Exception:
        return fallback


def get_account_display_name_from_ctx(
    ctx: "ExecutionContext",
    session,
    identifier: str,
) -> str:
    """Context 기반 Account 표시명 반환 (SSO 최적화)

    SSO Session인 경우 ctx.accounts에서 Account Name을 가져옴 (API 호출 없음).
    그 외의 경우 Account Alias 조회 후 없으면 Account ID 반환.

    Args:
        ctx: ExecutionContext (Flow에서 전달)
        session: boto3 Session
        identifier: SessionIterator에서 받은 identifier
            - SSO Session: account_id
            - 그 외: profile_name

    Returns:
        Account Name (SSO) 또는 Alias 또는 Account ID

    Example:
        >>> name = get_account_display_name_from_ctx(ctx, session, identifier)
        >>> print(name)  # "Production Account" (SSO) 또는 "my-alias" 또는 "123456789012"
    """
    # SSO Session인 경우: ctx.accounts에서 Account Name 조회 (API 호출 없음)
    if ctx.is_sso_session() and ctx.accounts:
        for account in ctx.accounts:
            if account.id == identifier:
                return account.name
        # 못 찾으면 identifier (account_id) 그대로 반환
        return identifier

    # 그 외: Account Alias 조회
    return get_account_display_name(session, fallback=identifier)


def get_account_id(session, fallback: str = "unknown") -> str:
    """Account ID 반환

    Args:
        session: boto3 Session
        fallback: 조회 실패 시 반환할 기본값

    Returns:
        12자리 Account ID
    """
    try:
        sts = session.client("sts")
        account_id: str = sts.get_caller_identity()["Account"]
        return account_id
    except Exception:
        return fallback


def get_account_alias(session) -> str | None:
    """Account Alias 반환 (없으면 None)

    Args:
        session: boto3 Session

    Returns:
        Account Alias 또는 None
    """
    try:
        iam = session.client("iam")
        aliases = iam.list_account_aliases().get("AccountAliases", [])
        return aliases[0] if aliases else None
    except Exception:
        return None


def get_account_info(session, fallback: str = "unknown") -> tuple[str, str | None]:
    """Account ID와 Alias 모두 반환

    Args:
        session: boto3 Session
        fallback: Account ID 조회 실패 시 반환할 기본값

    Returns:
        (account_id, account_alias) 튜플
        alias가 없으면 (account_id, None)
    """
    account_id = fallback
    account_alias = None

    try:
        sts = session.client("sts")
        account_id = sts.get_caller_identity()["Account"]
    except Exception:
        pass

    try:
        iam = session.client("iam")
        aliases = iam.list_account_aliases().get("AccountAliases", [])
        if aliases:
            account_alias = aliases[0]
    except Exception:
        pass

    return account_id, account_alias


def format_account_identifier(session, fallback: str = "unknown", format: str = "alias_or_id") -> str:
    """포맷된 계정 식별자 반환

    Args:
        session: boto3 Session
        fallback: 조회 실패 시 반환할 기본값
        format: 출력 포맷
            - "alias_or_id": Alias 우선, 없으면 ID (기본값)
            - "id": Account ID만
            - "alias": Alias만 (없으면 fallback)
            - "both": "Alias (ID)" 또는 ID만

    Returns:
        포맷된 계정 식별자

    Example:
        >>> format_account_identifier(session, format="both")
        "my-alias (123456789012)"

        >>> format_account_identifier(session, format="alias_or_id")
        "my-alias"
    """
    account_id, account_alias = get_account_info(session, fallback)

    if format == "id":
        return account_id
    elif format == "alias":
        return account_alias or fallback
    elif format == "both":
        if account_alias:
            return f"{account_alias} ({account_id})"
        return account_id
    else:  # alias_or_id (default)
        return account_alias or account_id
