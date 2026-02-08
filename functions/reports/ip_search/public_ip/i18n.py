"""functions/reports/ip_search/public_ip/i18n.py - Public IP Search 국제화(i18n).

Public IP Search Tool의 한국어/영어 메시지 번역을 관리합니다.
MESSAGES 딕셔너리에 키별로 ko/en 번역을 정의하고,
t() 함수로 현재 언어에 맞는 메시지를 반환합니다.
"""

from __future__ import annotations

import contextlib

from core.cli.i18n import get_lang

# Message definitions with ko/en translations
MESSAGES = {
    # Title and description
    "title": {
        "ko": "클라우드 IP 대역 조회",
        "en": "Cloud IP Range Lookup",
    },
    "subtitle": {
        "ko": "IP가 어느 클라우드 소속인지 확인 (AWS, GCP, Azure, Oracle)",
        "en": "Check which cloud provider owns an IP (AWS, GCP, Azure, Oracle)",
    },
    # Menu
    "menu_search_ip": {
        "ko": "IP 검색",
        "en": "Search IP",
    },
    "menu_filter_search": {
        "ko": "필터 검색 (리전/서비스)",
        "en": "Filter Search (Region/Service)",
    },
    "menu_cache_manage": {
        "ko": "캐시 관리",
        "en": "Cache Management",
    },
    "menu_back": {
        "ko": "돌아가기",
        "en": "Go Back",
    },
    # Prompts
    "prompt_select": {
        "ko": "선택",
        "en": "Select",
    },
    "prompt_enter_ip": {
        "ko": "IP 주소 입력 (쉼표로 여러 개 가능)",
        "en": "Enter IP address (comma-separated for multiple)",
    },
    "prompt_select_provider": {
        "ko": "제공자 선택",
        "en": "Select Provider",
    },
    "prompt_enter_filter": {
        "ko": "필터 입력 (리전 또는 서비스, 부분 일치)",
        "en": "Enter filter (region or service, partial match)",
    },
    # Providers
    "provider_all": {
        "ko": "전체",
        "en": "All",
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
    "result_unknown_provider": {
        "ko": "알 수 없는 제공자",
        "en": "Unknown Provider",
    },
    # Table headers
    "header_ip": {
        "ko": "IP 주소",
        "en": "IP Address",
    },
    "header_provider": {
        "ko": "제공자",
        "en": "Provider",
    },
    "header_service": {
        "ko": "서비스",
        "en": "Service",
    },
    "header_ip_range": {
        "ko": "IP 범위",
        "en": "IP Range",
    },
    "header_region": {
        "ko": "리전",
        "en": "Region",
    },
    # Cache status
    "cache_status_title": {
        "ko": "캐시 상태",
        "en": "Cache Status",
    },
    "cache_valid": {
        "ko": "유효",
        "en": "Valid",
    },
    "cache_expired": {
        "ko": "만료",
        "en": "Expired",
    },
    "cache_none": {
        "ko": "없음",
        "en": "None",
    },
    "cache_refresh": {
        "ko": "캐시 새로고침",
        "en": "Refresh Cache",
    },
    "cache_refreshing": {
        "ko": "캐시 새로고침 중...",
        "en": "Refreshing cache...",
    },
    "cache_refresh_done": {
        "ko": "캐시 새로고침 완료",
        "en": "Cache refresh complete",
    },
    "cache_refresh_failed": {
        "ko": "캐시 새로고침 실패",
        "en": "Cache refresh failed",
    },
    "cache_expired_auto": {
        "ko": "캐시가 만료되었습니다. 새로고침이 필요합니다.",
        "en": "Cache has expired. Refresh is needed.",
    },
    "cache_none_auto": {
        "ko": "캐시가 없습니다. 먼저 캐시를 생성해야 합니다.",
        "en": "No cache found. Cache needs to be created first.",
    },
    "cache_refresh_confirm": {
        "ko": "캐시를 새로고침할까요?",
        "en": "Refresh cache now?",
    },
    "cache_refresh_all_failed": {
        "ko": "모든 캐시 새로고침에 실패했습니다",
        "en": "All cache refresh failed",
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
    # Filter search
    "filter_regions": {
        "ko": "리전 ({count}개)",
        "en": "Regions ({count})",
    },
    "filter_services": {
        "ko": "서비스 ({count}개)",
        "en": "Services ({count})",
    },
    "filter_more": {
        "ko": "외 {count}개",
        "en": "and {count} more",
    },
    # Status messages
    "searching": {
        "ko": "검색 중...",
        "en": "Searching...",
    },
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
    # Validation errors
    "validation_invalid_ip": {
        "ko": "'{ip}' - 올바르지 않은 IP 형식",
        "en": "'{ip}' - Invalid IP format",
    },
    "validation_errors_found": {
        "ko": "입력 오류 {count}개 발견:",
        "en": "{count} input error(s) found:",
    },
    "validation_valid_ips": {
        "ko": "유효한 IP {count}개로 검색합니다",
        "en": "Searching with {count} valid IP(s)",
    },
    "validation_no_valid_ips": {
        "ko": "유효한 IP가 없습니다. 올바른 IP 형식으로 입력하세요.",
        "en": "No valid IPs. Please enter IPs in correct format.",
    },
    # Detailed error messages
    "result_no_match_detail": {
        "ko": "검색 결과가 없습니다",
        "en": "No results found",
    },
    "result_no_match_hint_public": {
        "ko": "• {ip}는 알려진 클라우드 프로바이더 IP 범위에 속하지 않습니다",
        "en": "• {ip} is not in known cloud provider IP ranges",
    },
    "result_no_match_hint_private": {
        "ko": "• 프라이빗 IP인 경우 'Private IP Search'를 사용하세요",
        "en": "• For private IPs, use 'Private IP Search'",
    },
    "result_no_match_hint_check": {
        "ko": "• IP 주소가 정확한지 확인하세요",
        "en": "• Please verify the IP address is correct",
    },
    # Help
    "help_title": {
        "ko": "IP Search 도움말",
        "en": "IP Search Help",
    },
    "help_input_format": {
        "ko": "입력 형식:",
        "en": "Input Format:",
    },
    "help_single_ip": {
        "ko": "• 단일 IP: 52.94.76.1",
        "en": "• Single IP: 52.94.76.1",
    },
    "help_cidr": {
        "ko": "• CIDR 범위: 13.0.0.0/8, 52.94.0.0/16 (중첩 검색)",
        "en": "• CIDR range: 13.0.0.0/8, 52.94.0.0/16 (overlap search)",
    },
    "help_multi_ip": {
        "ko": "• 다중 입력: 52.94.76.1, 8.8.8.8, 13.0.0.0/8 (쉼표/공백 구분)",
        "en": "• Multiple: 52.94.76.1, 8.8.8.8, 13.0.0.0/8 (comma/space)",
    },
    "help_shortcuts": {
        "ko": "단축키:",
        "en": "Shortcuts:",
    },
    "help_shortcut_help": {
        "ko": "• ?  - 도움말 표시",
        "en": "• ?  - Show help",
    },
    "help_shortcut_export": {
        "ko": "• e  - 결과 내보내기",
        "en": "• e  - Export results",
    },
    "help_shortcut_back": {
        "ko": "• 0  - 돌아가기",
        "en": "• 0  - Go back",
    },
    "help_providers": {
        "ko": "지원 프로바이더: AWS, GCP, Azure, Oracle, Cloudflare, Fastly",
        "en": "Supported providers: AWS, GCP, Azure, Oracle, Cloudflare, Fastly",
    },
    # Filter options
    "help_filter_options": {
        "ko": "필터 옵션 (인라인):",
        "en": "Filter Options (inline):",
    },
    "help_filter_provider": {
        "ko": "• -p <csp>      CSP 필터 (aws, gcp, azure, oracle, cloudflare, fastly)",
        "en": "• -p <csp>      CSP filter (aws, gcp, azure, oracle, cloudflare, fastly)",
    },
    "help_filter_region": {
        "ko": "• -r <region>   리전 필터 (ap-northeast-2, us-east-1, ...)",
        "en": "• -r <region>   Region filter (ap-northeast-2, us-east-1, ...)",
    },
    "help_filter_service": {
        "ko": "• -s <service>  서비스 필터 (EC2, S3, CLOUDFRONT, ...)",
        "en": "• -s <service>  Service filter (EC2, S3, CLOUDFRONT, ...)",
    },
    "help_interactive_filter": {
        "ko": "대화형 필터:",
        "en": "Interactive filter:",
    },
    "help_filter_set": {
        "ko": "• f             필터 설정 (CSP/리전/서비스를 순차적으로 입력)",
        "en": "• f             Set filter (CSP/region/service sequentially)",
    },
    "help_filter_clear": {
        "ko": "• fc            필터 초기화",
        "en": "• fc            Clear filter",
    },
    "help_examples": {
        "ko": "사용 예시:",
        "en": "Usage Examples:",
    },
    "help_example_basic": {
        "ko": "  52.94.76.1                        → 모든 CSP에서 검색",
        "en": "  52.94.76.1                        → Search all CSPs",
    },
    "help_example_multi": {
        "ko": "  52.94.76.1, 8.8.8.8               → 다중 IP 검색 (쉼표/공백 구분)",
        "en": "  52.94.76.1, 8.8.8.8               → Multiple IPs (comma/space)",
    },
    "help_example_provider": {
        "ko": "  52.94.76.1 -p aws                 → AWS에서만 검색",
        "en": "  52.94.76.1 -p aws                 → Search AWS only",
    },
    "help_example_multi_provider": {
        "ko": "  52.94.76.1 -p aws,gcp             → AWS, GCP에서 검색",
        "en": "  52.94.76.1 -p aws,gcp             → Search AWS and GCP",
    },
    "help_example_region": {
        "ko": "  52.94.76.1 -p aws -r ap-northeast → AWS 서울 리전에서 검색",
        "en": "  52.94.76.1 -p aws -r ap-northeast → Search AWS Seoul region",
    },
    "help_example_service": {
        "ko": "  52.94.76.1 -p aws -s EC2          → AWS EC2 대역에서 검색",
        "en": "  52.94.76.1 -p aws -s EC2          → Search AWS EC2 ranges",
    },
    "help_example_combined": {
        "ko": "  8.8.8.8, 1.1.1.1 -p gcp,cloudflare → 복합 필터 검색",
        "en": "  8.8.8.8, 1.1.1.1 -p gcp,cloudflare → Combined filter search",
    },
    "help_example_cidr": {
        "ko": "  13.0.0.0/8 -p aws                 → CIDR 범위 중첩 검색",
        "en": "  13.0.0.0/8 -p aws                 → CIDR overlap search",
    },
    "help_interactive_example": {
        "ko": "대화형 필터 예시:",
        "en": "Interactive Filter Example:",
    },
    "help_interactive_step1": {
        "ko": "  f → aws → ap-northeast-2 → EC2   → 필터 설정 후 검색",
        "en": "  f → aws → ap-northeast-2 → EC2   → Set filter then search",
    },
    "help_interactive_step2": {
        "ko": "  fc                                → 필터 초기화",
        "en": "  fc                                → Clear all filters",
    },
    # Cache management
    "cache_refresh_all": {
        "ko": "전체 새로고침",
        "en": "Refresh all",
    },
    "cache_refresh_select": {
        "ko": "개별 새로고침 (예: 1 또는 1,3,5)",
        "en": "Refresh selected (e.g., 1 or 1,3,5)",
    },
    "cache_delete": {
        "ko": "캐시 삭제",
        "en": "Delete cache",
    },
    "cache_delete_all": {
        "ko": "전체 삭제",
        "en": "Delete all",
    },
    "cache_delete_select": {
        "ko": "개별 삭제 (예: 1 또는 1,3,5)",
        "en": "Delete selected (e.g., 1 or 1,3,5)",
    },
    "cache_deleted": {
        "ko": "캐시 삭제 완료: {providers}",
        "en": "Cache deleted: {providers}",
    },
    "cache_refreshing_providers": {
        "ko": "{providers} 캐시 새로고침 중...",
        "en": "Refreshing {providers} cache...",
    },
    # Filter state
    "filter_current": {
        "ko": "[필터 적용됨] {filters}",
        "en": "[Filter applied] {filters}",
    },
    "filter_cleared": {
        "ko": "필터가 초기화되었습니다",
        "en": "Filter cleared",
    },
    "filter_prompt_csp": {
        "ko": "CSP (aws,gcp,azure,oracle,cloudflare,fastly 또는 Enter=전체)",
        "en": "CSP (aws,gcp,azure,oracle,cloudflare,fastly or Enter=all)",
    },
    "filter_prompt_region": {
        "ko": "리전 (예: ap-northeast-2, Enter=전체)",
        "en": "Region (e.g., ap-northeast-2, Enter=all)",
    },
    "filter_prompt_service": {
        "ko": "서비스 (예: EC2, S3, Enter=전체)",
        "en": "Service (e.g., EC2, S3, Enter=all)",
    },
    "filter_set_success": {
        "ko": "필터가 설정되었습니다",
        "en": "Filter has been set",
    },
    # Menu display (short versions)
    "menu_help_short": {
        "ko": "도움말",
        "en": "Help",
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
