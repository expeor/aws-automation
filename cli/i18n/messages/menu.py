"""
cli/i18n/messages/menu.py - Menu Messages

Contains translations for main menu, category selection, and tool listing.
"""

from __future__ import annotations

MENU_MESSAGES = {
    # =========================================================================
    # Main Menu
    # =========================================================================
    "main_title": {
        "ko": "AA - AWS Automation",
        "en": "AA - AWS Automation",
    },
    "search_placeholder": {
        "ko": "도구 검색 (이름, 키워드, 서비스명)",
        "en": "Search tools (name, keyword, service)",
    },
    "search_prompt": {
        "ko": "검색어 또는 번호 입력",
        "en": "Enter search term or number",
    },
    "no_search_results": {
        "ko": "검색 결과가 없습니다",
        "en": "No search results",
    },
    # =========================================================================
    # Menu Sections
    # =========================================================================
    "tool_navigation": {
        "ko": "도구 탐색",
        "en": "Tool Navigation",
    },
    "settings": {
        "ko": "설정",
        "en": "Settings",
    },
    "profiles": {
        "ko": "프로필",
        "en": "Profiles",
    },
    "search_keyword_hint": {
        "ko": "검색: 키워드 입력",
        "en": "Search: Enter keyword",
    },
    "all_tools": {
        "ko": "전체 도구",
        "en": "All Tools",
    },
    "aws_services": {
        "ko": "AWS 서비스",
        "en": "AWS Services",
    },
    "favorites": {
        "ko": "즐겨찾기",
        "en": "Favorites",
    },
    "recent": {
        "ko": "최근 사용",
        "en": "Recent",
    },
    "profile_groups": {
        "ko": "프로파일 그룹",
        "en": "Profile Groups",
    },
    # =========================================================================
    # Menu Actions
    # =========================================================================
    "add_to_favorites": {
        "ko": "즐겨찾기 추가",
        "en": "Add to Favorites",
    },
    "remove_from_favorites": {
        "ko": "즐겨찾기 제거",
        "en": "Remove from Favorites",
    },
    "added_to_favorites": {
        "ko": "즐겨찾기에 추가됨",
        "en": "Added to favorites",
    },
    "removed_from_favorites": {
        "ko": "즐겨찾기에서 제거됨",
        "en": "Removed from favorites",
    },
    "max_favorites_reached": {
        "ko": "즐겨찾기 최대 개수에 도달했습니다",
        "en": "Maximum favorites limit reached",
    },
    # =========================================================================
    # Tool Table Headers
    # =========================================================================
    "header_number": {
        "ko": "#",
        "en": "#",
    },
    "header_path": {
        "ko": "경로",
        "en": "Path",
    },
    "header_name": {
        "ko": "이름",
        "en": "Name",
    },
    "header_description": {
        "ko": "설명",
        "en": "Description",
    },
    "header_permission": {
        "ko": "권한",
        "en": "Permission",
    },
    "header_area": {
        "ko": "영역",
        "en": "Area",
    },
    "header_category": {
        "ko": "카테고리",
        "en": "Category",
    },
    # =========================================================================
    # Category Selection
    # =========================================================================
    "select_category": {
        "ko": "카테고리를 선택하세요",
        "en": "Select a category",
    },
    "select_tool": {
        "ko": "도구를 선택하세요",
        "en": "Select a tool",
    },
    "category_tools": {
        "ko": "{category} 도구 목록",
        "en": "{category} Tools",
    },
    # =========================================================================
    # Keyboard Shortcuts Help
    # =========================================================================
    "shortcuts_title": {
        "ko": "키보드 단축키",
        "en": "Keyboard Shortcuts",
    },
    "shortcut_search": {
        "ko": "s: 검색",
        "en": "s: Search",
    },
    "shortcut_all": {
        "ko": "a: 전체 도구",
        "en": "a: All tools",
    },
    "shortcut_category": {
        "ko": "c: 카테고리",
        "en": "c: Categories",
    },
    "shortcut_favorites": {
        "ko": "f: 즐겨찾기",
        "en": "f: Favorites",
    },
    "shortcut_groups": {
        "ko": "g: 그룹",
        "en": "g: Groups",
    },
    "shortcut_profile": {
        "ko": "p: 프로파일",
        "en": "p: Profile",
    },
    "shortcut_recent": {
        "ko": "t: 최근 사용",
        "en": "t: Recent",
    },
    "shortcut_help": {
        "ko": "h: 도움말",
        "en": "h: Help",
    },
    "shortcut_quit": {
        "ko": "q: 종료",
        "en": "q: Quit",
    },
    # =========================================================================
    # Permission Labels
    # =========================================================================
    "permission_read": {
        "ko": "읽기",
        "en": "Read",
    },
    "permission_write": {
        "ko": "쓰기",
        "en": "Write",
    },
    "permission_delete": {
        "ko": "삭제",
        "en": "Delete",
    },
    # =========================================================================
    # Profile Groups
    # =========================================================================
    "group_list_title": {
        "ko": "프로파일 그룹",
        "en": "Profile Groups",
    },
    "group_create": {
        "ko": "그룹 생성",
        "en": "Create Group",
    },
    "group_delete": {
        "ko": "그룹 삭제",
        "en": "Delete Group",
    },
    "group_name": {
        "ko": "그룹 이름",
        "en": "Group Name",
    },
    "group_profiles": {
        "ko": "프로파일",
        "en": "Profiles",
    },
    "group_saved": {
        "ko": "그룹 '{name}' 저장됨",
        "en": "Group '{name}' saved",
    },
    "group_deleted": {
        "ko": "그룹 '{name}' 삭제됨",
        "en": "Group '{name}' deleted",
    },
    "group_not_found": {
        "ko": "그룹을 찾을 수 없습니다: {name}",
        "en": "Group not found: {name}",
    },
    "no_groups": {
        "ko": "저장된 프로파일 그룹이 없습니다",
        "en": "No profile groups saved",
    },
    # =========================================================================
    # Utilities Section
    # =========================================================================
    "utilities": {
        "ko": "유틸리티",
        "en": "Utilities",
    },
    # =========================================================================
    # Favorites Management
    # =========================================================================
    "favorites_management": {
        "ko": "즐겨찾기 관리",
        "en": "Favorites Management",
    },
    "no_favorites_registered": {
        "ko": "등록된 즐겨찾기가 없습니다.",
        "en": "No favorites registered.",
    },
    "add": {
        "ko": "추가",
        "en": "Add",
    },
    "delete": {
        "ko": "삭제",
        "en": "Delete",
    },
    "move_up": {
        "ko": "위로",
        "en": "Up",
    },
    "move_down": {
        "ko": "아래로",
        "en": "Down",
    },
    "add_favorite": {
        "ko": "즐겨찾기 추가",
        "en": "Add Favorite",
    },
    "tool_name_or_keyword": {
        "ko": "도구명 또는 키워드 입력 (취소: Enter)",
        "en": "Enter tool name or keyword (Cancel: Enter)",
    },
    "already_registered": {
        "ko": "'{name}' 이미 등록됨",
        "en": "'{name}' already registered",
    },
    "added": {
        "ko": "'{name}' 추가됨",
        "en": "'{name}' added",
    },
    "add_failed_max": {
        "ko": "추가 실패 (최대 20개)",
        "en": "Add failed (max 20)",
    },
    "delete_number_prompt": {
        "ko": "삭제할 번호",
        "en": "Number to delete",
    },
    "deleted": {
        "ko": "'{name}' 삭제됨",
        "en": "'{name}' deleted",
    },
    "move_number_prompt": {
        "ko": "{direction} 이동할 번호",
        "en": "Number to move {direction}",
    },
    "moved": {
        "ko": "'{name}' 이동됨",
        "en": "'{name}' moved",
    },
    "already_at_top": {
        "ko": "이미 최상위",
        "en": "Already at top",
    },
    "already_at_bottom": {
        "ko": "이미 최하위",
        "en": "Already at bottom",
    },
    "cancel_enter_hint": {
        "ko": "취소: Enter",
        "en": "Cancel: Enter",
    },
    "edit_number_prompt": {
        "ko": "수정할 번호",
        "en": "Number to edit",
    },
    "edit_group": {
        "ko": "'{name}' 수정",
        "en": "Edit '{name}'",
    },
    "change_name": {
        "ko": "이름 변경",
        "en": "Change name",
    },
    "change_profiles": {
        "ko": "프로파일 변경",
        "en": "Change profiles",
    },
    "new_name_prompt": {
        "ko": "새 이름",
        "en": "New name",
    },
    "name_changed": {
        "ko": "이름 변경됨: {name}",
        "en": "Name changed: {name}",
    },
    "change_failed_duplicate": {
        "ko": "변경 실패 (이름 중복)",
        "en": "Change failed (duplicate name)",
    },
    "no_profiles_available": {
        "ko": "사용 가능한 프로파일이 없습니다.",
        "en": "No profiles available.",
    },
    "selection_hint": {
        "ko": "예: 1 2 3 또는 1,2,3 또는 1-3",
        "en": "e.g.: 1 2 3 or 1,2,3 or 1-3",
    },
    "select_new_profiles": {
        "ko": "새 프로파일 선택",
        "en": "Select new profiles",
    },
    "profiles_changed": {
        "ko": "프로파일 변경됨 ({count}개)",
        "en": "Profiles changed ({count})",
    },
    "number_prompt": {
        "ko": "번호",
        "en": "Number",
    },
    "selection_prompt": {
        "ko": "선택",
        "en": "Selection",
    },
    # =========================================================================
    # Profile Management
    # =========================================================================
    "aws_auth_profiles": {
        "ko": "AWS 인증 프로필",
        "en": "AWS Authentication Profiles",
    },
    "sso_session_multi": {
        "ko": "SSO 세션",
        "en": "SSO Session",
    },
    "sso_session_desc": {
        "ko": "멀티 계정",
        "en": "Multi-account",
    },
    "sso_profile_single": {
        "ko": "SSO 프로파일",
        "en": "SSO Profile",
    },
    "sso_profile_desc": {
        "ko": "고정 계정/역할",
        "en": "Fixed account/role",
    },
    "iam_access_key": {
        "ko": "IAM Access Key",
        "en": "IAM Access Key",
    },
    "static_credentials_desc": {
        "ko": "정적 자격 증명",
        "en": "Static credentials",
    },
    "other_unsupported": {
        "ko": "기타",
        "en": "Other",
    },
    "unsupported": {
        "ko": "미지원",
        "en": "Unsupported",
    },
    "no_profiles_configured": {
        "ko": "설정된 프로필이 없습니다.",
        "en": "No profiles configured.",
    },
    "check_aws_config": {
        "ko": "~/.aws/config 또는 ~/.aws/credentials를 확인하세요.",
        "en": "Check ~/.aws/config or ~/.aws/credentials.",
    },
    "profile_load_failed": {
        "ko": "프로필 로드 실패: {error}",
        "en": "Profile load failed: {error}",
    },
    # =========================================================================
    # Profile Groups Management
    # =========================================================================
    "profile_groups_management": {
        "ko": "프로파일 그룹 관리",
        "en": "Profile Groups Management",
    },
    "no_groups_saved": {
        "ko": "저장된 그룹이 없습니다.",
        "en": "No groups saved.",
    },
    "edit": {
        "ko": "수정",
        "en": "Edit",
    },
    "check_types": {
        "ko": "점검 유형",
        "en": "Check Types",
    },
    "aws_category": {
        "ko": "AWS 카테고리",
        "en": "AWS Categories",
    },
    "reports": {
        "ko": "종합 보고서",
        "en": "Reports",
    },
    "reports_desc": {
        "ko": "미사용 리소스, 인벤토리, IP 검색, 로그 분석",
        "en": "Unused resources, Inventory, IP search, Log analysis",
    },
    "no_reports_available": {
        "ko": "사용 가능한 보고서가 없습니다.",
        "en": "No reports available.",
    },
    # =========================================================================
    # Navigation & Prompts
    # =========================================================================
    "go_back": {
        "ko": "돌아가기",
        "en": "Go Back",
    },
    "leave": {
        "ko": "나가기",
        "en": "Exit",
    },
    "previous": {
        "ko": "이전",
        "en": "Prev",
    },
    "next": {
        "ko": "다음",
        "en": "Next",
    },
    "cancel": {
        "ko": "취소",
        "en": "Cancel",
    },
    "reset": {
        "ko": "초기화",
        "en": "Reset",
    },
    "enter_number_or_keyword": {
        "ko": "번호 입력 또는 키워드 검색",
        "en": "Enter number or search keyword",
    },
    "enter_number": {
        "ko": "숫자 입력",
        "en": "Enter number",
    },
    "range_info": {
        "ko": "{min}-{max} 범위",
        "en": "Range: {min}-{max}",
    },
    "count_suffix": {
        "ko": "{count}개",
        "en": "{count}",
    },
    "page_info": {
        "ko": "페이지 {current}/{total}",
        "en": "Page {current}/{total}",
    },
    # =========================================================================
    # Sub-service Menu
    # =========================================================================
    "sub_services": {
        "ko": "하위 서비스",
        "en": "Sub Services",
    },
    "all_items": {
        "ko": "전체",
        "en": "All",
    },
    "common_items": {
        "ko": "공통",
        "en": "Common",
    },
    "other": {
        "ko": "기타",
        "en": "Other",
    },
    # =========================================================================
    # Filter Labels
    # =========================================================================
    "permission_filter": {
        "ko": "권한필터",
        "en": "Perm Filter",
    },
    "area_filter": {
        "ko": "영역필터",
        "en": "Area Filter",
    },
    "filter_status": {
        "ko": "필터: {filters} ({filtered}/{total})",
        "en": "Filter: {filters} ({filtered}/{total})",
    },
    "no_filter_areas": {
        "ko": "필터 가능한 영역이 없습니다.",
        "en": "No areas available for filtering.",
    },
    "number_or_filter": {
        "ko": "숫자 또는 p/a/r",
        "en": "Number or p/a/r",
    },
    # =========================================================================
    # Table Headers
    # =========================================================================
    "header_service": {
        "ko": "서비스",
        "en": "Service",
    },
    "header_tools": {
        "ko": "도구",
        "en": "Tools",
    },
    # =========================================================================
    # Error Messages
    # =========================================================================
    "no_tools_registered": {
        "ko": "등록된 도구가 없습니다.",
        "en": "No tools registered.",
    },
    "category_not_found": {
        "ko": "'{name}' 카테고리를 찾을 수 없습니다.",
        "en": "Category '{name}' not found.",
    },
    "no_results": {
        "ko": "'{query}' 결과 없음",
        "en": "No results for '{query}'",
    },
    "first_page": {
        "ko": "첫 번째 페이지입니다.",
        "en": "This is the first page.",
    },
    "last_page": {
        "ko": "마지막 페이지입니다.",
        "en": "This is the last page.",
    },
    # =========================================================================
    # Tool Selection Prompts
    # =========================================================================
    "select_tool_prompt": {
        "ko": "번호 입력: 도구 선택 | 키워드 입력: 검색",
        "en": "Enter number to select | Enter keyword to search",
    },
    "select_tool_or_return": {
        "ko": "번호 입력: 도구 선택 | Enter: 목록으로 돌아가기",
        "en": "Enter number to select | Enter: return to list",
    },
    # =========================================================================
    # Search Messages
    # =========================================================================
    "search_engine_not_initialized": {
        "ko": "검색 엔진이 초기화되지 않았습니다.",
        "en": "Search engine not initialized.",
    },
    "search_no_results_hint": {
        "ko": "다른 키워드로 검색하거나 s 키로 카테고리를 탐색하세요.",
        "en": "Try another keyword or press 's' to browse services.",
    },
    "search_results_count": {
        "ko": "{count}건",
        "en": "{count} results",
    },
    "enter_range_number": {
        "ko": "1-{max} 범위의 번호를 입력하세요.",
        "en": "Enter a number between 1-{max}.",
    },
    "no_favorites": {
        "ko": "즐겨찾기가 없습니다.",
        "en": "No favorites.",
    },
    "search_init_failed": {
        "ko": "검색 엔진 초기화 실패",
        "en": "Search engine initialization failed",
    },
    "return_zero": {
        "ko": "0: 돌아가기",
        "en": "0: Return",
    },
    "no_tools_in_area": {
        "ko": "{area} 영역에 도구가 없습니다.",
        "en": "No tools in {area} area.",
    },
    "no_plugins_in_category": {
        "ko": "AWS 카테고리에 매핑된 플러그인이 없습니다.",
        "en": "No plugins mapped to AWS categories.",
    },
    "no_services_in_category": {
        "ko": "이 카테고리에 서비스가 없습니다.",
        "en": "No services in this category.",
    },
    "no_tools_in_service": {
        "ko": "이 서비스에 도구가 없습니다.",
        "en": "No tools in this service.",
    },
    "preparing": {
        "ko": "준비 중",
        "en": "Preparing",
    },
    "history_location": {
        "ko": "이력: {path}",
        "en": "History: {path}",
    },
    # =========================================================================
    # Help Section
    # =========================================================================
    "help_title": {
        "ko": "AWS Automation CLI 도움말",
        "en": "AWS Automation CLI Help",
    },
    "help_all_tools_desc": {
        "ko": "모든 도구를 한 화면에 표시",
        "en": "Show all tools in one view",
    },
    "help_services_desc": {
        "ko": "서비스별 목록 (EC2, ELB, VPC...)",
        "en": "List by service (EC2, ELB, VPC...)",
    },
    "help_categories_desc": {
        "ko": "카테고리별 탐색 (Compute, Storage...)",
        "en": "Browse by category (Compute, Storage...)",
    },
    "help_check_types_desc": {
        "ko": "영역별 (보안, 비용, 성능...)",
        "en": "By area (Security, Cost, Performance...)",
    },
    "help_reports_desc": {
        "ko": "종합 보고서 모음 (미사용, 인벤토리, IP, 로그)",
        "en": "Comprehensive reports collection",
    },
    "help_favorites_desc": {
        "ko": "자주 사용하는 도구 추가/제거",
        "en": "Add/remove frequently used tools",
    },
    "help_groups_desc": {
        "ko": "프로필 그룹 관리",
        "en": "Profile groups management",
    },
    "help_profiles_desc": {
        "ko": "AWS 프로필 전환 (SSO/Access Key)",
        "en": "Switch AWS profile (SSO/Access Key)",
    },
    "help_help_desc": {
        "ko": "이 화면 표시",
        "en": "Show this screen",
    },
    "help_quit_desc": {
        "ko": "프로그램 종료",
        "en": "Exit program",
    },
    "help_favorites_quick_desc": {
        "ko": "즐겨찾기 바로 실행",
        "en": "Quick access favorites",
    },
    "help_search_services": {
        "ko": "AWS 서비스명",
        "en": "AWS service name",
    },
    "help_search_keyword_ko": {
        "ko": "한글 키워드",
        "en": "Korean keywords",
    },
    "help_search_keyword_en": {
        "ko": "영문 키워드",
        "en": "English keywords",
    },
    "help_domain_filter": {
        "ko": "도메인 필터",
        "en": "Domain Filter",
    },
    "help_cli_direct": {
        "ko": "CLI 직접 실행",
        "en": "CLI Direct Execution",
    },
    "help_cli_interactive": {
        "ko": "대화형 메뉴",
        "en": "Interactive menu",
    },
    "help_cli_tool_list": {
        "ko": "도구 목록",
        "en": "Tool list",
    },
    "help_cli_service_help": {
        "ko": "도움말",
        "en": "Help",
    },
    "help_output_path": {
        "ko": "출력 경로",
        "en": "Output Path",
    },
    "help_output_location": {
        "ko": "결과 파일",
        "en": "Result files",
    },
    # =========================================================================
    # Scheduled Operations
    # =========================================================================
    "scheduled_operations": {
        "ko": "정기 작업",
        "en": "Scheduled Operations",
    },
    "comprehensive_reports": {
        "ko": "종합 보고서",
        "en": "Comprehensive Reports",
    },
    "header_cycle": {
        "ko": "주기",
        "en": "Cycle",
    },
    "task_check": {
        "ko": "점검",
        "en": "Check",
    },
    "task_apply": {
        "ko": "적용",
        "en": "Apply",
    },
    "task_cleanup": {
        "ko": "정리",
        "en": "Cleanup",
    },
    "permission_legend": {
        "ko": "권한",
        "en": "Permission",
    },
    "delete_task_warning": {
        "ko": "⚠ delete 작업은 실행 전 확인을 요청합니다.",
        "en": "⚠ Delete tasks require confirmation before execution.",
    },
    "delete_confirm_prompt": {
        "ko": "⚠ '{name}'은(는) 삭제 작업입니다. 실행하시겠습니까? (y/N)",
        "en": "⚠ '{name}' is a delete task. Execute? (y/N)",
    },
    "help_scheduled_desc": {
        "ko": "정기 작업 (일간/월간/분기/반기/연간)",
        "en": "Scheduled operations (Daily/Monthly/Quarterly...)",
    },
    "current_config": {
        "ko": "현재 설정",
        "en": "Current config",
    },
    "change_config": {
        "ko": "설정 변경",
        "en": "Change config",
    },
    "select_config": {
        "ko": "설정 프로필 선택",
        "en": "Select Config Profile",
    },
    "no_other_configs": {
        "ko": "다른 설정이 없습니다. config/ 폴더에 YAML 파일을 추가하세요.",
        "en": "No other configs. Add YAML files to config/ folder.",
    },
    "press_any_key": {
        "ko": "계속하려면 Enter...",
        "en": "Press Enter to continue...",
    },
}
