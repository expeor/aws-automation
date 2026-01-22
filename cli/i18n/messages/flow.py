"""
cli/i18n/messages/flow.py - Flow Step Messages

Contains translations for authentication flow, profile/account/region/role selection.
"""

from __future__ import annotations

FLOW_MESSAGES = {
    # =========================================================================
    # Profile Selection
    # =========================================================================
    "no_profiles_available": {
        "ko": "사용 가능한 AWS 프로파일이 없습니다.",
        "en": "No AWS profiles available.",
    },
    "run_aws_configure": {
        "ko": "'aws configure' 또는 'aws configure sso'를 실행해주세요.",
        "en": "Please run 'aws configure' or 'aws configure sso'.",
    },
    "profile_label": {
        "ko": "프로파일:",
        "en": "Profile:",
    },
    "auth_label": {
        "ko": "인증:",
        "en": "Auth:",
    },
    "select_auth_type": {
        "ko": "인증 방식 선택",
        "en": "Select Authentication Type",
    },
    "saved_profile_groups": {
        "ko": "저장된 프로파일 그룹",
        "en": "Saved Profile Groups",
    },
    "select_profile_group": {
        "ko": "프로파일 그룹 선택",
        "en": "Select Profile Group",
    },
    "group_label": {
        "ko": "그룹:",
        "en": "Group:",
    },
    "select_single_multi": {
        "ko": "1) 단일 선택  2) 다중 선택",
        "en": "1) Single  2) Multiple",
    },
    "enter_1_or_2": {
        "ko": "1 또는 2 입력",
        "en": "Enter 1 or 2",
    },
    "profile_selection": {
        "ko": "{name} 선택 ({count}개)",
        "en": "Select {name} ({count})",
    },
    "nav_search_clear": {
        "ko": "{nav}/검색 | c: 해제",
        "en": "{nav}/search | c: clear",
    },
    "nav_all_done": {
        "ko": "{nav}a: 전체 | d: 완료 ({count}개)",
        "en": "{nav}a: all | d: done ({count})",
    },
    "min_one_selection": {
        "ko": "최소 1개 선택",
        "en": "Select at least 1",
    },
    "enter_number_range_pattern": {
        "ko": "숫자, 범위, 패턴 입력",
        "en": "Enter number, range, or pattern",
    },
    "selected_count": {
        "ko": "{count}개 선택됨",
        "en": "{count} selected",
    },
    "group_not_found": {
        "ko": "그룹을 찾을 수 없습니다: {name}",
        "en": "Group not found: {name}",
    },
    "group_profiles_not_found": {
        "ko": "그룹 '{name}'의 프로파일을 찾을 수 없습니다.",
        "en": "Profiles in group '{name}' not found.",
    },
    "profiles_deleted_or_renamed": {
        "ko": "프로파일이 삭제되었거나 이름이 변경되었을 수 있습니다.",
        "en": "Profiles may have been deleted or renamed.",
    },
    "some_profiles_not_found": {
        "ko": "일부 프로파일을 찾을 수 없음: {profiles}",
        "en": "Some profiles not found: {profiles}",
    },
    "group_profiles_count": {
        "ko": "그룹 '{name}': {count}개 프로파일",
        "en": "Group '{name}': {count} profiles",
    },
    "sequential_execution": {
        "ko": "{count}개 프로파일 순차 실행",
        "en": "Sequential execution of {count} profiles",
    },
    "auth_module_load_failed": {
        "ko": "internal.auth 모듈 로드 실패",
        "en": "Failed to load internal.auth module",
    },
    "authenticating": {
        "ko": "인증 중...",
        "en": "Authenticating...",
    },
    "auth_complete": {
        "ko": "인증 완료",
        "en": "Authentication complete",
    },
    "auth_failed": {
        "ko": "인증 실패: {error}",
        "en": "Authentication failed: {error}",
    },
    "loading_accounts": {
        "ko": "계정 로드 중...",
        "en": "Loading accounts...",
    },
    "accounts_count": {
        "ko": "{count}개 계정",
        "en": "{count} accounts",
    },
    "account_load_failed": {
        "ko": "계정 로드 실패: {error}",
        "en": "Failed to load accounts: {error}",
    },
    # =========================================================================
    # Account Selection
    # =========================================================================
    "no_accounts": {
        "ko": "계정 목록이 없습니다.",
        "en": "No accounts available.",
    },
    "account_label": {
        "ko": "계정:",
        "en": "Account:",
    },
    "account_selection": {
        "ko": "계정 선택 ({count}개)",
        "en": "Select Account ({count})",
    },
    "single_account_only": {
        "ko": "단일 계정만 지원",
        "en": "Single account only",
    },
    "enter_number_range": {
        "ko": "번호 입력 (1-{max})",
        "en": "Enter number (1-{max})",
    },
    "number_range_all": {
        "ko": "번호 (1,2,3 / 1-5) | all: 전체",
        "en": "Number (1,2,3 / 1-5) | all: all",
    },
    "all_selected": {
        "ko": "{count}개 전체 선택",
        "en": "All {count} selected",
    },
    "enter_valid_number": {
        "ko": "올바른 번호 입력",
        "en": "Enter valid number",
    },
    "accounts_selected": {
        "ko": "{count}개 계정 선택",
        "en": "{count} accounts selected",
    },
    # =========================================================================
    # Role Selection
    # =========================================================================
    "no_roles_available": {
        "ko": "사용 가능한 Role이 없습니다.",
        "en": "No roles available.",
    },
    "all_accounts_use_role": {
        "ko": "모든 계정에서 '{role}' 사용",
        "en": "Using '{role}' for all accounts",
    },
    "collecting_roles": {
        "ko": "Role 수집 중...",
        "en": "Collecting roles...",
    },
    "roles_count": {
        "ko": "{count}개 Role",
        "en": "{count} roles",
    },
    "role_selection": {
        "ko": "Role 선택 ({count}개)",
        "en": "Select Role ({count})",
    },
    "role_unsupported_accounts": {
        "ko": "{role} 미지원 계정: {count}개",
        "en": "{role} unsupported in {count} accounts",
    },
    "no_fallback_skip": {
        "ko": "Fallback 없음 - 해당 계정 스킵 필요",
        "en": "No fallback - need to skip accounts",
    },
    "skip_accounts_confirm": {
        "ko": "{count}개 계정 제외하고 진행? (y: 진행 / n: 취소)",
        "en": "Proceed excluding {count} accounts? (y: proceed / n: cancel)",
    },
    "fallback_setup": {
        "ko": "Fallback 설정",
        "en": "Fallback Setup",
    },
    "recommended_covers": {
        "ko": "권장, {count}개 커버",
        "en": "Recommended, covers {count}",
    },
    "select_other_role": {
        "ko": "다른 Role 선택",
        "en": "Select other role",
    },
    "skip_accounts": {
        "ko": "{count}개 계정 스킵",
        "en": "Skip {count} accounts",
    },
    "select_fallback_role": {
        "ko": "Fallback Role 선택",
        "en": "Select Fallback Role",
    },
    "covers_count": {
        "ko": "{count}개 커버",
        "en": "covers {count}",
    },
    "no_roles_error": {
        "ko": "Role 없음",
        "en": "No roles",
    },
    "user_cancelled": {
        "ko": "사용자 취소",
        "en": "User cancelled",
    },
    "role_label": {
        "ko": "Role:",
        "en": "Role:",
    },
    "fallback_label": {
        "ko": "Fallback:",
        "en": "Fallback:",
    },
    "skipped_count": {
        "ko": "스킵: {count}개",
        "en": "Skipped: {count}",
    },
    "count_pct": {
        "ko": "{count}개 ({pct}%)",
        "en": "{count} ({pct}%)",
    },
    "enter_1_to_3": {
        "ko": "1-3 입력",
        "en": "Enter 1-3",
    },
    # =========================================================================
    # Region Selection
    # =========================================================================
    "region_label": {
        "ko": "리전:",
        "en": "Region:",
    },
    "region_selection": {
        "ko": "리전 선택",
        "en": "Select Region",
    },
    "single_region_only": {
        "ko": "단일 리전만 지원",
        "en": "Single region only",
    },
    "region_count": {
        "ko": "리전 ({count}개)",
        "en": "Region ({count})",
    },
    "number_comma_all": {
        "ko": "번호 (쉼표 구분) | a: 전체",
        "en": "Number (comma separated) | a: all",
    },
    "select_2_or_more": {
        "ko": "2개 이상 선택해주세요",
        "en": "Please select 2 or more",
    },
    "all_regions_count": {
        "ko": "전체 {count}개",
        "en": "All {count}",
    },
    "regions_count": {
        "ko": "{count}개",
        "en": "{count}",
    },
    "region_global": {
        "ko": "Global (us-east-1)",
        "en": "Global (us-east-1)",
    },
    "current_region": {
        "ko": "현재 리전 ({region})",
        "en": "Current region ({region})",
    },
    "select_other_region": {
        "ko": "다른 리전 선택",
        "en": "Select other region",
    },
    "select_other_region_single": {
        "ko": "다른 리전 1개 선택",
        "en": "Select one other region",
    },
    "select_multiple_regions": {
        "ko": "여러 리전 선택 (2개 이상)",
        "en": "Select multiple regions (2+)",
    },
    "all_regions": {
        "ko": "모든 리전 ({count}개)",
        "en": "All regions ({count})",
    },
    # =========================================================================
    # Common Flow Messages
    # =========================================================================
    "enter_number": {
        "ko": "숫자 입력",
        "en": "Enter number",
    },
    "number_range_hint": {
        "ko": "1-{max} 범위",
        "en": "Range: 1-{max}",
    },
    "back": {
        "ko": "뒤로",
        "en": "Back",
    },
    "cancelled": {
        "ko": "취소됨",
        "en": "Cancelled",
    },
    "terminated": {
        "ko": "종료",
        "en": "Terminated",
    },
    "completed": {
        "ko": "완료: {success}개 성공, {failed}개 실패",
        "en": "Completed: {success} succeeded, {failed} failed",
    },
    # =========================================================================
    # Headless Mode
    # =========================================================================
    "tool_not_found": {
        "ko": "도구를 찾을 수 없습니다: {category}/{tool}",
        "en": "Tool not found: {category}/{tool}",
    },
    "sso_session_not_supported": {
        "ko": "SSO Session은 headless 모드에서 지원하지 않습니다: {profile}",
        "en": "SSO Session is not supported in headless mode: {profile}",
    },
    "use_sso_or_access_key": {
        "ko": "SSO Profile 또는 Access Key 프로파일을 사용하세요.",
        "en": "Use SSO Profile or Access Key profile.",
    },
    "unsupported_profile_type": {
        "ko": "지원하지 않는 프로파일 유형: {type}",
        "en": "Unsupported profile type: {type}",
    },
    "profile_not_found": {
        "ko": "프로파일을 찾을 수 없습니다: {profile}",
        "en": "Profile not found: {profile}",
    },
    "available_profiles": {
        "ko": "사용 가능한 프로파일:",
        "en": "Available profiles:",
    },
    "using_sso_profile": {
        "ko": "SSO 프로파일 사용: {profile}",
        "en": "Using SSO profile: {profile}",
    },
    "using_static_profile": {
        "ko": "Static 프로파일 사용: {profile}",
        "en": "Using static profile: {profile}",
    },
    "tool_load_failed": {
        "ko": "도구 로드 실패: {category}/{tool}",
        "en": "Tool load failed: {category}/{tool}",
    },
    "tool_no_run_function": {
        "ko": "도구에 run 함수가 없습니다",
        "en": "Tool has no run function",
    },
    "invalid_tool_path": {
        "ko": "잘못된 도구 경로: {path}",
        "en": "Invalid tool path: {path}",
    },
    "tool_path_format_hint": {
        "ko": "형식: category/tool_module (예: ec2/ebs_audit)",
        "en": "Format: category/tool_module (e.g., ec2/ebs_audit)",
    },
    # =========================================================================
    # Category Selection
    # =========================================================================
    "discovery_load_failed": {
        "ko": "discovery 모듈 로드 실패: {error}",
        "en": "Discovery module load failed: {error}",
    },
    "no_tools_registered": {
        "ko": "등록된 도구가 없습니다.",
        "en": "No tools registered.",
    },
    "add_tools_hint": {
        "ko": "internal/tools/ 하위에 CATEGORY, TOOLS가 정의된 폴더를 추가하세요.",
        "en": "Add folders with CATEGORY and TOOLS defined under internal/tools/.",
    },
    "category_not_found": {
        "ko": "'{name}' 카테고리를 찾을 수 없습니다.",
        "en": "Category '{name}' not found.",
    },
    # =========================================================================
    # Error Messages
    # =========================================================================
    "error_label": {
        "ko": "오류: {message}",
        "en": "Error: {message}",
    },
}
