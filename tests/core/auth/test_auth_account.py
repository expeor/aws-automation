# tests/test_auth_account.py
"""
core/auth/account.py 테스트

테스트 대상:
- get_account_display_name: Account Alias 또는 ID 반환
- get_account_display_name_from_ctx: Context 기반 표시명
- get_account_id: Account ID 반환
- get_account_alias: Account Alias 반환
- get_account_info: ID와 Alias 튜플 반환
- format_account_identifier: 포맷된 식별자 반환
"""

from unittest.mock import MagicMock, patch

import pytest

from core.auth.account import (
    format_account_identifier,
    get_account_alias,
    get_account_display_name,
    get_account_display_name_from_ctx,
    get_account_id,
    get_account_info,
)


class TestGetAccountDisplayName:
    """get_account_display_name 함수 테스트"""

    def test_returns_alias_when_available(self):
        """Alias가 있을 때 Alias 반환"""
        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_iam.list_account_aliases.return_value = {
            "AccountAliases": ["my-account-alias"]
        }
        mock_session.client.return_value = mock_iam

        result = get_account_display_name(mock_session)

        assert result == "my-account-alias"
        mock_session.client.assert_called_with("iam")

    def test_returns_account_id_when_no_alias(self):
        """Alias가 없을 때 Account ID 반환"""
        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_sts = MagicMock()

        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        mock_session.client.side_effect = lambda service: {
            "iam": mock_iam,
            "sts": mock_sts,
        }[service]

        result = get_account_display_name(mock_session)

        assert result == "123456789012"

    def test_returns_fallback_on_error(self):
        """오류 발생 시 fallback 반환"""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("API Error")

        result = get_account_display_name(mock_session, fallback="error-fallback")

        assert result == "error-fallback"

    def test_returns_default_fallback(self):
        """기본 fallback 값 ('unknown')"""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("API Error")

        result = get_account_display_name(mock_session)

        assert result == "unknown"


class TestGetAccountDisplayNameFromCtx:
    """get_account_display_name_from_ctx 함수 테스트"""

    def test_returns_name_from_ctx_for_sso_session(self):
        """SSO Session일 때 ctx.accounts에서 이름 반환"""
        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True

        # 계정 목록 설정
        mock_account = MagicMock()
        mock_account.id = "111111111111"
        mock_account.name = "Production Account"
        mock_ctx.accounts = [mock_account]

        mock_session = MagicMock()

        result = get_account_display_name_from_ctx(
            mock_ctx, mock_session, "111111111111"
        )

        assert result == "Production Account"
        # SSO Session이면 API 호출하지 않음
        mock_session.client.assert_not_called()

    def test_returns_identifier_when_account_not_found_in_ctx(self):
        """SSO Session이지만 계정을 찾지 못할 때 identifier 반환"""
        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True

        mock_account = MagicMock()
        mock_account.id = "222222222222"
        mock_account.name = "Other Account"
        mock_ctx.accounts = [mock_account]

        mock_session = MagicMock()

        result = get_account_display_name_from_ctx(
            mock_ctx, mock_session, "111111111111"
        )

        assert result == "111111111111"

    def test_falls_back_to_api_when_no_accounts_in_ctx(self):
        """SSO Session이지만 계정 목록이 없을 때 API 호출로 fallback"""
        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True
        mock_ctx.accounts = []  # 빈 리스트는 falsy

        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "111111111111"}
        mock_session.client.side_effect = lambda service: {
            "iam": mock_iam,
            "sts": mock_sts,
        }[service]

        result = get_account_display_name_from_ctx(
            mock_ctx, mock_session, "111111111111"
        )

        # 빈 accounts 리스트면 API 호출로 fallback
        assert result == "111111111111"
        mock_session.client.assert_called()

    def test_calls_get_account_display_name_for_non_sso(self):
        """SSO Session이 아닐 때 API 호출"""
        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.accounts = []

        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}
        mock_session.client.return_value = mock_iam

        result = get_account_display_name_from_ctx(
            mock_ctx, mock_session, "profile-name"
        )

        assert result == "my-alias"
        mock_session.client.assert_called()


class TestGetAccountId:
    """get_account_id 함수 테스트"""

    def test_returns_account_id(self):
        """Account ID 정상 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session.client.return_value = mock_sts

        result = get_account_id(mock_session)

        assert result == "123456789012"
        mock_session.client.assert_called_with("sts")

    def test_returns_fallback_on_error(self):
        """오류 발생 시 fallback 반환"""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("STS Error")

        result = get_account_id(mock_session, fallback="error")

        assert result == "error"

    def test_returns_default_fallback(self):
        """기본 fallback 값"""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("STS Error")

        result = get_account_id(mock_session)

        assert result == "unknown"


class TestGetAccountAlias:
    """get_account_alias 함수 테스트"""

    def test_returns_alias_when_available(self):
        """Alias가 있을 때 반환"""
        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}
        mock_session.client.return_value = mock_iam

        result = get_account_alias(mock_session)

        assert result == "my-alias"

    def test_returns_none_when_no_alias(self):
        """Alias가 없을 때 None 반환"""
        mock_session = MagicMock()
        mock_iam = MagicMock()
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}
        mock_session.client.return_value = mock_iam

        result = get_account_alias(mock_session)

        assert result is None

    def test_returns_none_on_error(self):
        """오류 발생 시 None 반환"""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("IAM Error")

        result = get_account_alias(mock_session)

        assert result is None


class TestGetAccountInfo:
    """get_account_info 함수 테스트"""

    def test_returns_both_id_and_alias(self):
        """ID와 Alias 모두 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = get_account_info(mock_session)

        assert result == ("123456789012", "my-alias")

    def test_returns_id_with_none_alias(self):
        """ID만 있고 Alias 없을 때"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = get_account_info(mock_session)

        assert result == ("123456789012", None)

    def test_returns_fallback_when_sts_fails(self):
        """STS 실패 시 fallback ID 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.side_effect = Exception("STS Error")
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = get_account_info(mock_session, fallback="fallback-id")

        assert result == ("fallback-id", "my-alias")

    def test_returns_none_alias_when_iam_fails(self):
        """IAM 실패 시 None Alias 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.side_effect = Exception("IAM Error")

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = get_account_info(mock_session)

        assert result == ("123456789012", None)


class TestFormatAccountIdentifier:
    """format_account_identifier 함수 테스트"""

    def test_format_alias_or_id_returns_alias(self):
        """alias_or_id 포맷: Alias 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="alias_or_id")

        assert result == "my-alias"

    def test_format_alias_or_id_returns_id_when_no_alias(self):
        """alias_or_id 포맷: Alias 없으면 ID 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="alias_or_id")

        assert result == "123456789012"

    def test_format_id_only(self):
        """id 포맷: ID만 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="id")

        assert result == "123456789012"

    def test_format_alias_only(self):
        """alias 포맷: Alias만 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="alias")

        assert result == "my-alias"

    def test_format_alias_returns_fallback_when_no_alias(self):
        """alias 포맷: Alias 없으면 fallback 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(
            mock_session, fallback="no-alias", format="alias"
        )

        assert result == "no-alias"

    def test_format_both_with_alias(self):
        """both 포맷: Alias와 ID 모두 표시"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": ["my-alias"]}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="both")

        assert result == "my-alias (123456789012)"

    def test_format_both_without_alias(self):
        """both 포맷: Alias 없으면 ID만 표시"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {"AccountAliases": []}

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="both")

        assert result == "123456789012"

    def test_default_format_is_alias_or_id(self):
        """기본 포맷은 alias_or_id"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {
            "AccountAliases": ["default-test-alias"]
        }

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session)

        assert result == "default-test-alias"

    def test_unknown_format_uses_alias_or_id(self):
        """알 수 없는 포맷은 alias_or_id로 처리"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_iam = MagicMock()

        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_iam.list_account_aliases.return_value = {
            "AccountAliases": ["unknown-format-alias"]
        }

        mock_session.client.side_effect = lambda service: {
            "sts": mock_sts,
            "iam": mock_iam,
        }[service]

        result = format_account_identifier(mock_session, format="unknown_format")

        assert result == "unknown-format-alias"
