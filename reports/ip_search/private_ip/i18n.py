"""
plugins/vpc/ip_search/private_ip/i18n.py - Internationalization for Private IP Search
"""

from __future__ import annotations

import contextlib

from cli.i18n import get_lang

# Message definitions with ko/en translations
MESSAGES = {
    # Title and description
    "title": {
        "ko": "내부 IP 리소스 조회",
        "en": "Internal IP Resource Lookup",
    },
    "subtitle": {
        "ko": "내부 IP가 어떤 AWS 리소스에 할당되어 있는지 확인",
        "en": "Find which AWS resource an internal IP belongs to",
    },
    # Menu
    "menu_search": {
        "ko": "검색",
        "en": "Search",
    },
    "menu_cache_select": {
        "ko": "캐시 선택",
        "en": "Select Cache",
    },
    "menu_cache_create": {
        "ko": "캐시 생성",
        "en": "Create Cache",
    },
    "menu_cache_delete": {
        "ko": "캐시 삭제",
        "en": "Delete Cache",
    },
    "menu_back": {
        "ko": "돌아가기",
        "en": "Go Back",
    },
    # Cache selection
    "cache_available": {
        "ko": "사용 가능한 캐시",
        "en": "Available Caches",
    },
    "cache_selected": {
        "ko": "선택된 캐시",
        "en": "Selected Caches",
    },
    "cache_none_available": {
        "ko": "사용 가능한 캐시가 없습니다. 먼저 캐시를 생성하세요.",
        "en": "No caches available. Create a cache first.",
    },
    "cache_none_auto": {
        "ko": "캐시가 없습니다. 검색을 위해 캐시를 생성해야 합니다.",
        "en": "No cache found. Cache needs to be created for search.",
    },
    "cache_expired_auto": {
        "ko": "모든 캐시가 만료되었습니다. 새 캐시를 생성해야 합니다.",
        "en": "All caches have expired. Need to create a new cache.",
    },
    "cache_create_confirm": {
        "ko": "지금 캐시를 생성할까요?",
        "en": "Create cache now?",
    },
    "cache_profile": {
        "ko": "프로파일",
        "en": "Profile",
    },
    "cache_account": {
        "ko": "계정",
        "en": "Account",
    },
    "cache_eni_count": {
        "ko": "ENI 수",
        "en": "ENI Count",
    },
    "cache_regions": {
        "ko": "리전",
        "en": "Regions",
    },
    "cache_created": {
        "ko": "생성일",
        "en": "Created",
    },
    "cache_status": {
        "ko": "상태",
        "en": "Status",
    },
    "cache_valid": {
        "ko": "유효",
        "en": "Valid",
    },
    "cache_expired": {
        "ko": "만료",
        "en": "Expired",
    },
    "cache_toggle_all": {
        "ko": "전체 선택/해제",
        "en": "Toggle All",
    },
    "cache_confirm_selection": {
        "ko": "선택 확인",
        "en": "Confirm Selection",
    },
    # Cache creation - profile/region selection
    "cache_select_profile": {
        "ko": "프로파일 선택",
        "en": "Select Profile",
    },
    "cache_select_regions": {
        "ko": "리전 선택",
        "en": "Select Regions",
    },
    "cache_all_regions": {
        "ko": "주요 리전 전체",
        "en": "All Major Regions",
    },
    "cache_custom_regions": {
        "ko": "직접 입력",
        "en": "Custom Input",
    },
    "cache_enter_regions": {
        "ko": "리전 입력 (쉼표 구분)",
        "en": "Enter regions (comma-separated)",
    },
    # Cache creation
    "cache_creating": {
        "ko": "캐시 생성 중...",
        "en": "Creating cache...",
    },
    "cache_creating_for": {
        "ko": "{profile} / {account} 캐시 생성 중...",
        "en": "Creating cache for {profile} / {account}...",
    },
    "cache_created_success": {
        "ko": "캐시 생성 완료: {count}개 ENI",
        "en": "Cache created: {count} ENIs",
    },
    "cache_create_failed": {
        "ko": "캐시 생성 실패",
        "en": "Cache creation failed",
    },
    # Cache deletion
    "cache_delete_confirm": {
        "ko": "선택한 캐시를 삭제하시겠습니까?",
        "en": "Delete selected caches?",
    },
    "cache_deleted": {
        "ko": "{count}개 캐시 삭제됨",
        "en": "{count} cache(s) deleted",
    },
    # Search
    "search_prompt": {
        "ko": "검색어 입력 (IP, CIDR, VPC ID, 텍스트)",
        "en": "Enter search (IP, CIDR, VPC ID, text)",
    },
    "search_examples": {
        "ko": "예: 10.0.1.50, 10.0.0.0/24, vpc-abc123, my-server",
        "en": "e.g.: 10.0.1.50, 10.0.0.0/24, vpc-abc123, my-server",
    },
    "searching": {
        "ko": "검색 중...",
        "en": "Searching...",
    },
    # Detail mode
    "detail_mode": {
        "ko": "상세 모드",
        "en": "Detail Mode",
    },
    "detail_mode_desc": {
        "ko": "API 호출로 리소스 상세 정보 조회 (느림)",
        "en": "Fetch resource details via API (slower)",
    },
    "detail_mode_on": {
        "ko": "상세 모드 ON",
        "en": "Detail Mode ON",
    },
    "detail_mode_off": {
        "ko": "상세 모드 OFF",
        "en": "Detail Mode OFF",
    },
    "fetching_details": {
        "ko": "리소스 상세 정보 조회 중...",
        "en": "Fetching resource details...",
    },
    # Results
    "result_title": {
        "ko": "검색 결과",
        "en": "Search Results",
    },
    "result_count": {
        "ko": "{count}건",
        "en": "{count} results",
    },
    "result_no_match": {
        "ko": "검색 결과가 없습니다",
        "en": "No results found",
    },
    # Table headers
    "header_ip": {
        "ko": "IP 주소",
        "en": "IP Address",
    },
    "header_profile": {
        "ko": "프로파일",
        "en": "Profile",
    },
    "header_account": {
        "ko": "계정",
        "en": "Account",
    },
    "header_region": {
        "ko": "리전",
        "en": "Region",
    },
    "header_resource": {
        "ko": "리소스",
        "en": "Resource",
    },
    "header_eni_id": {
        "ko": "ENI ID",
        "en": "ENI ID",
    },
    "header_vpc_id": {
        "ko": "VPC ID",
        "en": "VPC ID",
    },
    "header_public_ip": {
        "ko": "Public IP",
        "en": "Public IP",
    },
    # Export options
    "export_title": {
        "ko": "결과 저장",
        "en": "Save Results",
    },
    "export_csv": {
        "ko": "CSV로 저장",
        "en": "Save as CSV",
    },
    "export_excel": {
        "ko": "Excel로 저장",
        "en": "Save as Excel",
    },
    "export_clipboard": {
        "ko": "클립보드에 복사",
        "en": "Copy to Clipboard",
    },
    "export_clipboard_simple": {
        "ko": "클립보드에 복사 (간략)",
        "en": "Copy to Clipboard (Simple)",
    },
    "export_continue": {
        "ko": "계속 검색",
        "en": "Continue Search",
    },
    "export_saved": {
        "ko": "저장 완료: {path}",
        "en": "Saved: {path}",
    },
    "export_copied": {
        "ko": "클립보드에 복사되었습니다",
        "en": "Copied to clipboard",
    },
    "export_failed": {
        "ko": "저장/복사 실패 (필요한 패키지가 설치되지 않았을 수 있습니다)",
        "en": "Save/copy failed (required package may not be installed)",
    },
    # Prompts
    "prompt_select": {
        "ko": "선택",
        "en": "Select",
    },
    "prompt_enter": {
        "ko": "입력",
        "en": "Enter",
    },
    "prompt_yes_no": {
        "ko": "(y/n)",
        "en": "(y/n)",
    },
    # Status messages
    "loading": {
        "ko": "로딩 중...",
        "en": "Loading...",
    },
    "done": {
        "ko": "완료",
        "en": "Done",
    },
    "error": {
        "ko": "오류",
        "en": "Error",
    },
    "exit_message": {
        "ko": "검색을 종료합니다",
        "en": "Exiting search",
    },
    # Hints
    "hint_toggle_detail": {
        "ko": "d=상세모드",
        "en": "d=Detail",
    },
    "hint_back": {
        "ko": "0=돌아가기",
        "en": "0=Back",
    },
    # Validation errors
    "validation_invalid_query": {
        "ko": "'{query}' - 올바르지 않은 형식",
        "en": "'{query}' - Invalid format",
    },
    "validation_errors_found": {
        "ko": "입력 오류:",
        "en": "Input error:",
    },
    # Detailed error messages
    "result_no_match_detail": {
        "ko": "검색 결과가 없습니다",
        "en": "No results found",
    },
    "result_no_match_hint_cache": {
        "ko": "• 캐시에 해당 IP가 존재하지 않습니다",
        "en": "• IP not found in cache",
    },
    "result_no_match_hint_refresh": {
        "ko": "• 캐시를 새로고침하거나 다른 리전의 캐시를 생성해 보세요",
        "en": "• Try refreshing cache or creating cache for other regions",
    },
    "result_no_match_hint_public": {
        "ko": "• 퍼블릭 IP인 경우 'Public IP Search'를 사용하세요",
        "en": "• For public IPs, use 'Public IP Search'",
    },
    "result_no_match_hint_format": {
        "ko": "• 지원 형식: IP, CIDR, VPC ID, ENI ID, 텍스트",
        "en": "• Supported formats: IP, CIDR, VPC ID, ENI ID, text",
    },
    # Help
    "help_title": {
        "ko": "Private IP Search 도움말",
        "en": "Private IP Search Help",
    },
    "help_input_format": {
        "ko": "입력 형식:",
        "en": "Input Format:",
    },
    "help_ip": {
        "ko": "• IP: 10.0.1.50",
        "en": "• IP: 10.0.1.50",
    },
    "help_cidr": {
        "ko": "• CIDR: 10.0.0.0/24",
        "en": "• CIDR: 10.0.0.0/24",
    },
    "help_vpc": {
        "ko": "• VPC ID: vpc-abc123",
        "en": "• VPC ID: vpc-abc123",
    },
    "help_eni": {
        "ko": "• ENI ID: eni-abc123",
        "en": "• ENI ID: eni-abc123",
    },
    "help_text": {
        "ko": "• 텍스트: 이름, 설명 등으로 검색",
        "en": "• Text: Search by name, description, etc.",
    },
    "help_shortcuts": {
        "ko": "단축키:",
        "en": "Shortcuts:",
    },
    "help_shortcut_help": {
        "ko": "• ?  - 도움말 표시",
        "en": "• ?  - Show help",
    },
    "help_shortcut_detail": {
        "ko": "• d  - 상세 모드 토글 (API 호출로 리소스 정보 조회)",
        "en": "• d  - Toggle detail mode (fetch resource info via API)",
    },
    "help_shortcut_back": {
        "ko": "• 0  - 돌아가기",
        "en": "• 0  - Go back",
    },
    "help_note_cache": {
        "ko": "참고: 검색은 로컬 캐시를 사용합니다. 캐시를 먼저 생성하세요.",
        "en": "Note: Search uses local cache. Create a cache first.",
    },
    "hint_help": {
        "ko": "?=도움말",
        "en": "?=Help",
    },
    # Detail mode restrictions
    "detail_mode_single_cache_only": {
        "ko": "Detail Mode는 단일 캐시 선택 시에만 사용 가능합니다. '캐시 선택'에서 1개만 선택하세요.",
        "en": "Detail Mode is only available with a single cache. Select only 1 cache in 'Select Cache'.",
    },
    "detail_mode_auth_failed": {
        "ko": "인증 실패. Detail Mode를 비활성화합니다.",
        "en": "Authentication failed. Disabling Detail Mode.",
    },
}


def t(key: str, **kwargs) -> str:
    """Get translated message for the current language.

    Args:
        key: Message key
        **kwargs: Format arguments

    Returns:
        Translated message string
    """
    lang = get_lang()
    msg_dict = MESSAGES.get(key, {})

    if not msg_dict:
        return key

    text = msg_dict.get(lang) or msg_dict.get("ko", key)

    if kwargs:
        with contextlib.suppress(KeyError, ValueError):
            text = text.format(**kwargs)

    return text
