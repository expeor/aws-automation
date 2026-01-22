"""
cli/i18n/messages/common.py - Common Messages

Contains translations for authentication, progress, errors, and general UI.
"""

from __future__ import annotations

COMMON_MESSAGES = {
    # =========================================================================
    # Authentication
    # =========================================================================
    "select_profile": {
        "ko": "AWS 프로필을 선택하세요",
        "en": "Select AWS profile",
    },
    "select_auth_type": {
        "ko": "인증 방식을 선택하세요",
        "en": "Select authentication type",
    },
    "sso_session": {
        "ko": "SSO Session (멀티 계정)",
        "en": "SSO Session (Multi-account)",
    },
    "sso_profile": {
        "ko": "SSO Profile (단일 계정)",
        "en": "SSO Profile (Single account)",
    },
    "static_credentials": {
        "ko": "IAM Access Key",
        "en": "IAM Access Key",
    },
    "auth_failed": {
        "ko": "인증에 실패했습니다",
        "en": "Authentication failed",
    },
    "auth_expired": {
        "ko": "인증이 만료되었습니다. 다시 로그인하세요.",
        "en": "Authentication expired. Please login again.",
    },
    "no_profiles_found": {
        "ko": "사용 가능한 프로파일이 없습니다",
        "en": "No available profiles found",
    },
    "logging_in": {
        "ko": "로그인 중...",
        "en": "Logging in...",
    },
    "login_success": {
        "ko": "로그인 성공",
        "en": "Login successful",
    },
    # =========================================================================
    # Account & Role Selection
    # =========================================================================
    "select_accounts": {
        "ko": "계정을 선택하세요",
        "en": "Select accounts",
    },
    "select_role": {
        "ko": "역할(Role)을 선택하세요",
        "en": "Select a role",
    },
    "all_accounts": {
        "ko": "전체 계정",
        "en": "All accounts",
    },
    "account_count": {
        "ko": "{count}개 계정",
        "en": "{count} accounts",
    },
    "selected_accounts": {
        "ko": "선택된 계정: {count}개",
        "en": "Selected accounts: {count}",
    },
    # =========================================================================
    # Region Selection
    # =========================================================================
    "select_region": {
        "ko": "리전을 선택하세요",
        "en": "Select region",
    },
    "all_regions": {
        "ko": "전체 리전",
        "en": "All regions",
    },
    "region_count": {
        "ko": "{count}개 리전",
        "en": "{count} regions",
    },
    "single_region_only": {
        "ko": "이 도구는 단일 리전만 지원합니다",
        "en": "This tool supports single region only",
    },
    # =========================================================================
    # Progress & Status
    # =========================================================================
    "collecting": {
        "ko": "리소스 수집 중...",
        "en": "Collecting resources...",
    },
    "processing": {
        "ko": "처리 중...",
        "en": "Processing...",
    },
    "analyzing": {
        "ko": "분석 중...",
        "en": "Analyzing...",
    },
    "completed": {
        "ko": "완료",
        "en": "Completed",
    },
    "failed": {
        "ko": "실패",
        "en": "Failed",
    },
    "skipped": {
        "ko": "건너뜀",
        "en": "Skipped",
    },
    "loading": {
        "ko": "로딩 중...",
        "en": "Loading...",
    },
    "please_wait": {
        "ko": "잠시만 기다려주세요...",
        "en": "Please wait...",
    },
    # =========================================================================
    # Results
    # =========================================================================
    "found_items": {
        "ko": "{count}개 항목 발견",
        "en": "Found {count} items",
    },
    "no_items_found": {
        "ko": "발견된 항목 없음",
        "en": "No items found",
    },
    "total_count": {
        "ko": "총 {count}개",
        "en": "Total: {count}",
    },
    "result_summary": {
        "ko": "결과 요약",
        "en": "Result Summary",
    },
    # =========================================================================
    # File Operations
    # =========================================================================
    "file_saved": {
        "ko": "파일 저장됨: {path}",
        "en": "File saved: {path}",
    },
    "open_in_explorer": {
        "ko": "탐색기에서 열기",
        "en": "Open in Explorer",
    },
    "open_folder_prompt": {
        "ko": "폴더를 여시겠습니까?",
        "en": "Open folder?",
    },
    "excel_exported": {
        "ko": "Excel 파일이 저장되었습니다",
        "en": "Excel file has been saved",
    },
    # =========================================================================
    # Errors
    # =========================================================================
    "error": {
        "ko": "오류",
        "en": "Error",
    },
    "error_occurred": {
        "ko": "오류가 발생했습니다: {message}",
        "en": "An error occurred: {message}",
    },
    "invalid_selection": {
        "ko": "잘못된 선택입니다",
        "en": "Invalid selection",
    },
    "operation_cancelled": {
        "ko": "작업이 취소되었습니다",
        "en": "Operation cancelled",
    },
    "permission_denied": {
        "ko": "권한이 없습니다",
        "en": "Permission denied",
    },
    "resource_not_found": {
        "ko": "리소스를 찾을 수 없습니다",
        "en": "Resource not found",
    },
    "api_error": {
        "ko": "AWS API 오류: {message}",
        "en": "AWS API error: {message}",
    },
    "timeout_error": {
        "ko": "시간 초과",
        "en": "Timeout",
    },
    # =========================================================================
    # User Input
    # =========================================================================
    "enter_number": {
        "ko": "번호 입력",
        "en": "Enter number",
    },
    "enter_selection": {
        "ko": "선택",
        "en": "Selection",
    },
    "press_any_key": {
        "ko": "아무 키나 눌러 계속...",
        "en": "Press any key to continue...",
    },
    "press_any_key_to_return": {
        "ko": "아무 키나 눌러 돌아가기...",
        "en": "Press any key to return...",
    },
    "confirm_yes_no": {
        "ko": "계속하시겠습니까? (y/n)",
        "en": "Continue? (y/n)",
    },
    "yes": {
        "ko": "예",
        "en": "Yes",
    },
    "no": {
        "ko": "아니오",
        "en": "No",
    },
    "cancel": {
        "ko": "취소",
        "en": "Cancel",
    },
    "back": {
        "ko": "뒤로",
        "en": "Back",
    },
    "exit": {
        "ko": "종료",
        "en": "Exit",
    },
    # =========================================================================
    # Misc
    # =========================================================================
    "version": {
        "ko": "버전",
        "en": "Version",
    },
    "help": {
        "ko": "도움말",
        "en": "Help",
    },
    "search": {
        "ko": "검색",
        "en": "Search",
    },
    "filter": {
        "ko": "필터",
        "en": "Filter",
    },
    "sort": {
        "ko": "정렬",
        "en": "Sort",
    },
    "refresh": {
        "ko": "새로고침",
        "en": "Refresh",
    },
    # =========================================================================
    # Banner & UI
    # =========================================================================
    "profile_not_set": {
        "ko": "프로필 미설정",
        "en": "No profile set",
    },
    "help_quit_hint": {
        "ko": "h: 도움말 | q: 종료",
        "en": "h: Help | q: Quit",
    },
    "color_legend": {
        "ko": "색상 범례:",
        "en": "Color legend:",
    },
    "color_yellow": {
        "ko": "노란색",
        "en": "Yellow",
    },
    "color_red": {
        "ko": "빨간색",
        "en": "Red",
    },
    "color_green": {
        "ko": "초록색",
        "en": "Green",
    },
    "color_blue": {
        "ko": "파란색",
        "en": "Blue",
    },
    "color_cyan": {
        "ko": "청록색",
        "en": "Cyan",
    },
    "color_magenta": {
        "ko": "보라색",
        "en": "Magenta",
    },
    "color_orange": {
        "ko": "주황색",
        "en": "Orange",
    },
    "color_gray": {
        "ko": "회색",
        "en": "Gray",
    },
}
