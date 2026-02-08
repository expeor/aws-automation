"""
cli/i18n/messages/runner.py - Flow Runner Messages

Contains translations for flow execution, progress, and error messages.
"""

from __future__ import annotations

RUNNER_MESSAGES = {
    # =========================================================================
    # Execution Flow
    # =========================================================================
    "execution_failed": {
        "ko": "실행 실패: {message}",
        "en": "Execution failed: {message}",
    },
    "run_another": {
        "ko": "다른 보고서를 실행하시겠습니까? [Y/n]",
        "en": "Run another report? [Y/n]",
    },
    "executing": {
        "ko": "실행 중...",
        "en": "Executing...",
    },
    "done": {
        "ko": "완료",
        "en": "Done",
    },
    "cancelled": {
        "ko": "취소됨",
        "en": "Cancelled",
    },
    "ctrl_c_hint": {
        "ko": "Ctrl+C: 취소",
        "en": "Ctrl+C: Cancel",
    },
    # =========================================================================
    # Tool Discovery
    # =========================================================================
    "tool_not_found": {
        "ko": "'{path}' 도구를 찾을 수 없습니다.",
        "en": "Tool '{path}' not found.",
    },
    "tool_load_failed": {
        "ko": "도구 로드 실패: {error}",
        "en": "Failed to load tool: {error}",
    },
    "no_run_function": {
        "ko": "도구에 run 함수가 없습니다",
        "en": "Tool has no run function",
    },
    "tool_config_check_failed": {
        "ko": "도구 설정 확인 실패: {error}",
        "en": "Failed to check tool config: {error}",
    },
    "tool_or_category_not_selected": {
        "ko": "도구 또는 카테고리가 선택되지 않음",
        "en": "Tool or category not selected",
    },
    # =========================================================================
    # Execution Summary
    # =========================================================================
    "execution_summary": {
        "ko": "실행 요약",
        "en": "Execution Summary",
    },
    "summary_tool": {
        "ko": "도구",
        "en": "Tool",
    },
    "summary_profile": {
        "ko": "프로파일",
        "en": "Profile",
    },
    "summary_role": {
        "ko": "Role",
        "en": "Role",
    },
    "summary_region": {
        "ko": "리전",
        "en": "Region",
    },
    "summary_regions_count": {
        "ko": "{count}개",
        "en": "{count} regions",
    },
    "summary_accounts": {
        "ko": "계정",
        "en": "Accounts",
    },
    "summary_accounts_count": {
        "ko": "{count}개",
        "en": "{count} accounts",
    },
    "required_permissions": {
        "ko": "필요 권한:",
        "en": "Required permissions:",
    },
    # =========================================================================
    # Permission Errors
    # =========================================================================
    "permission_error_title": {
        "ko": "권한 오류",
        "en": "Permission Error",
    },
    "permission_missing": {
        "ko": "{code}: 필요한 권한이 없습니다.",
        "en": "{code}: Required permissions missing.",
    },
    "tool_required_permissions": {
        "ko": "이 도구에 필요한 권한:",
        "en": "Permissions required for this tool:",
    },
    "permission_read": {
        "ko": "Read:",
        "en": "Read:",
    },
    "permission_write": {
        "ko": "Write:",
        "en": "Write:",
    },
    "contact_admin": {
        "ko": "IAM 정책에 위 권한을 추가하거나 관리자에게 문의하세요.",
        "en": "Add these permissions to your IAM policy or contact your administrator.",
    },
    # =========================================================================
    # History
    # =========================================================================
    "history_save_failed": {
        "ko": "이력 저장 실패: {error}",
        "en": "Failed to save history: {error}",
    },
}
