"""
plugins/vpc/ip_search/public_ip/i18n.py - Internationalization for Public IP Search
"""

from __future__ import annotations

import contextlib

from cli.i18n import get_lang

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
