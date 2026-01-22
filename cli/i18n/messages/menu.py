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
}
