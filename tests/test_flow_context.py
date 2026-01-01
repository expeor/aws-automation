# tests/test_flow_context.py
"""
internal/flow/context.py 단위 테스트

ExecutionContext, RoleSelection 등 컨텍스트 클래스 테스트.
"""

from unittest.mock import MagicMock

import pytest

from cli.flow.context import (
    BackToMenu,
    ExecutionContext,
    FallbackStrategy,
    FlowResult,
    ProviderKind,
    RoleSelection,
    ToolInfo,
)

# =============================================================================
# BackToMenu 예외 테스트
# =============================================================================


class TestBackToMenu:
    """BackToMenu 예외 테스트"""

    def test_is_exception(self):
        """Exception 상속 확인"""
        assert issubclass(BackToMenu, Exception)

    def test_can_be_raised(self):
        """raise 가능 확인"""
        with pytest.raises(BackToMenu):
            raise BackToMenu()


# =============================================================================
# ProviderKind Enum 테스트
# =============================================================================


class TestProviderKind:
    """ProviderKind Enum 테스트"""

    def test_all_kinds_defined(self):
        """모든 종류 정의 확인"""
        assert ProviderKind.SSO_SESSION.value == "sso_session"
        assert ProviderKind.SSO_PROFILE.value == "sso_profile"
        assert ProviderKind.STATIC_CREDENTIALS.value == "static"

    def test_kinds_count(self):
        """종류 개수 확인"""
        assert len(ProviderKind) == 3


# =============================================================================
# FallbackStrategy Enum 테스트
# =============================================================================


class TestFallbackStrategy:
    """FallbackStrategy Enum 테스트"""

    def test_strategies_defined(self):
        """전략 정의 확인"""
        assert FallbackStrategy.USE_FALLBACK.value == "use_fallback"
        assert FallbackStrategy.SKIP_ACCOUNT.value == "skip"


# =============================================================================
# RoleSelection 테스트
# =============================================================================


class TestRoleSelection:
    """RoleSelection 클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        rs = RoleSelection(primary_role="AdminRole")

        assert rs.primary_role == "AdminRole"
        assert rs.fallback_role is None
        assert rs.fallback_strategy == FallbackStrategy.USE_FALLBACK
        assert rs.role_account_map == {}
        assert rs.skipped_accounts == []

    def test_with_fallback(self):
        """Fallback 설정 확인"""
        rs = RoleSelection(
            primary_role="AdminRole",
            fallback_role="ReadOnlyRole",
            fallback_strategy=FallbackStrategy.USE_FALLBACK,
        )

        assert rs.fallback_role == "ReadOnlyRole"
        assert rs.fallback_strategy == FallbackStrategy.USE_FALLBACK

    def test_with_role_account_map(self):
        """Role-Account 매핑 확인"""
        rs = RoleSelection(
            primary_role="AdminRole",
            role_account_map={
                "AdminRole": ["111111111111", "222222222222"],
                "ReadOnlyRole": ["333333333333"],
            },
        )

        assert len(rs.role_account_map["AdminRole"]) == 2
        assert "111111111111" in rs.role_account_map["AdminRole"]

    def test_with_skipped_accounts(self):
        """스킵 계정 설정 확인"""
        rs = RoleSelection(
            primary_role="AdminRole",
            skipped_accounts=["999999999999"],
        )

        assert "999999999999" in rs.skipped_accounts


# =============================================================================
# ToolInfo 테스트
# =============================================================================


class TestToolInfo:
    """ToolInfo 클래스 테스트"""

    def test_required_fields(self):
        """필수 필드 확인"""
        tool = ToolInfo(
            name="테스트 도구",
            description="테스트 설명",
            category="test",
            permission="read",
        )

        assert tool.name == "테스트 도구"
        assert tool.description == "테스트 설명"
        assert tool.category == "test"
        assert tool.permission == "read"

    def test_default_values(self):
        """기본값 확인"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
        )

        assert tool.runner is None
        assert tool.options_collector is None
        assert tool.supports_single_region_only is False
        assert tool.supports_single_account_only is False

    def test_with_runner(self):
        """runner 함수 설정 확인"""

        def mock_runner(ctx):
            return "result"

        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="test",
            permission="read",
            runner=mock_runner,
        )

        assert tool.runner is not None
        assert tool.runner(None) == "result"


# =============================================================================
# ExecutionContext 테스트
# =============================================================================


class TestExecutionContext:
    """ExecutionContext 클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        ctx = ExecutionContext()

        assert ctx.category is None
        assert ctx.tool is None
        assert ctx.profile_name is None
        assert ctx.profiles == []
        assert ctx.provider_kind is None
        assert ctx.provider is None
        assert ctx.role_selection is None
        assert ctx.accounts == []
        assert ctx.regions == []
        assert ctx.options == {}
        assert ctx.result is None
        assert ctx.error is None

    def test_with_values(self):
        """값 설정 확인"""
        tool = ToolInfo(
            name="테스트",
            description="설명",
            category="ebs",
            permission="read",
        )

        ctx = ExecutionContext(
            category="ebs",
            tool=tool,
            profile_name="dev",
            regions=["ap-northeast-2", "us-east-1"],
        )

        assert ctx.category == "ebs"
        assert ctx.tool.name == "테스트"
        assert ctx.profile_name == "dev"
        assert len(ctx.regions) == 2

    # -------------------------------------------------------------------------
    # is_sso 메서드 테스트
    # -------------------------------------------------------------------------

    def test_is_sso_with_sso_session(self):
        """SSO Session일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.is_sso() is True

    def test_is_sso_with_sso_profile(self):
        """SSO Profile일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_PROFILE)
        assert ctx.is_sso() is True

    def test_is_sso_with_static(self):
        """Static Credentials일 때 False"""
        ctx = ExecutionContext(provider_kind=ProviderKind.STATIC_CREDENTIALS)
        assert ctx.is_sso() is False

    # -------------------------------------------------------------------------
    # is_sso_session 메서드 테스트
    # -------------------------------------------------------------------------

    def test_is_sso_session_true(self):
        """SSO Session일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.is_sso_session() is True

    def test_is_sso_session_false_for_profile(self):
        """SSO Profile일 때 False"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_PROFILE)
        assert ctx.is_sso_session() is False

    # -------------------------------------------------------------------------
    # is_sso_profile 메서드 테스트
    # -------------------------------------------------------------------------

    def test_is_sso_profile_true(self):
        """SSO Profile일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_PROFILE)
        assert ctx.is_sso_profile() is True

    def test_is_sso_profile_false_for_session(self):
        """SSO Session일 때 False"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.is_sso_profile() is False

    # -------------------------------------------------------------------------
    # is_multi_profile 메서드 테스트
    # -------------------------------------------------------------------------

    def test_is_multi_profile_with_multiple_profiles(self):
        """다중 프로파일이 선택된 경우 True"""
        ctx = ExecutionContext(
            provider_kind=ProviderKind.STATIC_CREDENTIALS,
            profiles=["dev", "prod"],
        )
        assert ctx.is_multi_profile() is True

    def test_is_multi_profile_with_single_profile(self):
        """단일 프로파일만 있는 경우 False"""
        ctx = ExecutionContext(
            provider_kind=ProviderKind.STATIC_CREDENTIALS,
            profiles=["dev"],
        )
        assert ctx.is_multi_profile() is False

    def test_is_multi_profile_with_empty_profiles(self):
        """프로파일 목록이 비어있으면 False"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.is_multi_profile() is False

    def test_is_multi_profile_with_sso_profile_multi(self):
        """SSO Profile 다중 선택 시 True"""
        ctx = ExecutionContext(
            provider_kind=ProviderKind.SSO_PROFILE,
            profiles=["profile-account-a", "profile-account-b"],
        )
        assert ctx.is_multi_profile() is True

    # -------------------------------------------------------------------------
    # is_multi_account 메서드 테스트
    # -------------------------------------------------------------------------

    def test_is_multi_account_with_sso_session(self):
        """SSO Session일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.is_multi_account() is True

    def test_is_multi_account_with_sso_profile(self):
        """SSO Profile일 때 False (계정/역할 고정)"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_PROFILE)
        assert ctx.is_multi_account() is False

    def test_is_multi_account_with_static(self):
        """Static일 때 False"""
        ctx = ExecutionContext(provider_kind=ProviderKind.STATIC_CREDENTIALS)
        assert ctx.is_multi_account() is False

    # -------------------------------------------------------------------------
    # needs_role_selection 메서드 테스트
    # -------------------------------------------------------------------------

    def test_needs_role_selection_with_sso_session(self):
        """SSO Session일 때 True"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_SESSION)
        assert ctx.needs_role_selection() is True

    def test_needs_role_selection_with_sso_profile(self):
        """SSO Profile일 때 False (역할 고정)"""
        ctx = ExecutionContext(provider_kind=ProviderKind.SSO_PROFILE)
        assert ctx.needs_role_selection() is False

    # -------------------------------------------------------------------------
    # get_effective_role 메서드 테스트
    # -------------------------------------------------------------------------

    def test_get_effective_role_no_selection(self):
        """role_selection 없으면 None"""
        ctx = ExecutionContext()
        assert ctx.get_effective_role("111111111111") is None

    def test_get_effective_role_primary(self):
        """Primary Role 사용 가능하면 반환"""
        ctx = ExecutionContext(
            role_selection=RoleSelection(
                primary_role="AdminRole",
                role_account_map={
                    "AdminRole": ["111111111111", "222222222222"],
                },
            )
        )

        assert ctx.get_effective_role("111111111111") == "AdminRole"
        assert ctx.get_effective_role("222222222222") == "AdminRole"

    def test_get_effective_role_fallback(self):
        """Primary 없으면 Fallback 사용"""
        ctx = ExecutionContext(
            role_selection=RoleSelection(
                primary_role="AdminRole",
                fallback_role="ReadOnlyRole",
                fallback_strategy=FallbackStrategy.USE_FALLBACK,
                role_account_map={
                    "AdminRole": ["111111111111"],
                    "ReadOnlyRole": ["222222222222"],
                },
            )
        )

        assert ctx.get_effective_role("111111111111") == "AdminRole"
        assert ctx.get_effective_role("222222222222") == "ReadOnlyRole"

    def test_get_effective_role_skip_strategy(self):
        """SKIP 전략일 때 None 반환"""
        ctx = ExecutionContext(
            role_selection=RoleSelection(
                primary_role="AdminRole",
                fallback_strategy=FallbackStrategy.SKIP_ACCOUNT,
                role_account_map={
                    "AdminRole": ["111111111111"],
                },
            )
        )

        assert ctx.get_effective_role("111111111111") == "AdminRole"
        # 매핑되지 않은 계정은 None (스킵)
        assert ctx.get_effective_role("999999999999") is None

    # -------------------------------------------------------------------------
    # get_target_accounts 메서드 테스트
    # -------------------------------------------------------------------------

    def test_get_target_accounts_no_selection(self):
        """role_selection 없으면 전체 accounts 반환"""
        mock_acc1 = MagicMock()
        mock_acc1.id = "111111111111"
        mock_acc2 = MagicMock()
        mock_acc2.id = "222222222222"

        ctx = ExecutionContext(accounts=[mock_acc1, mock_acc2])

        targets = ctx.get_target_accounts()
        assert len(targets) == 2

    def test_get_target_accounts_with_skipped(self):
        """skipped_accounts 제외"""
        mock_acc1 = MagicMock()
        mock_acc1.id = "111111111111"
        mock_acc2 = MagicMock()
        mock_acc2.id = "222222222222"

        ctx = ExecutionContext(
            accounts=[mock_acc1, mock_acc2],
            role_selection=RoleSelection(
                primary_role="AdminRole",
                skipped_accounts=["222222222222"],
            ),
        )

        targets = ctx.get_target_accounts()
        assert len(targets) == 1
        assert targets[0].id == "111111111111"


# =============================================================================
# FlowResult 테스트
# =============================================================================


class TestFlowResult:
    """FlowResult 클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        ctx = ExecutionContext()
        result = FlowResult(success=True, context=ctx)

        assert result.success is True
        assert result.context == ctx
        assert result.message == ""
        assert result.next_action == "home"

    def test_with_failure(self):
        """실패 결과 확인"""
        ctx = ExecutionContext()
        result = FlowResult(
            success=False,
            context=ctx,
            message="도구 실행 실패",
        )

        assert result.success is False
        assert result.message == "도구 실행 실패"

    def test_with_next_action(self):
        """next_action 설정 확인"""
        ctx = ExecutionContext()
        result = FlowResult(
            success=True,
            context=ctx,
            next_action="repeat",
        )

        assert result.next_action == "repeat"
