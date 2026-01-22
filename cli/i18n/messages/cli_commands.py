"""
cli/i18n/messages/cli_commands.py - CLI Command Messages

Contains translations for Click CLI commands, help text, and error messages.
"""

from __future__ import annotations

CLI_MESSAGES = {
    # =========================================================================
    # Help Text Section Names
    # =========================================================================
    "section_utilities": {
        "ko": "유틸리티",
        "en": "Utilities",
    },
    "section_aws_services": {
        "ko": "AWS 서비스",
        "en": "AWS Services",
    },
    # =========================================================================
    # CLI Help Text
    # =========================================================================
    "help_intro": {
        "ko": "AWS 리소스 분석, 비용 최적화, 보안 점검 등\nAWS 운영 업무를 자동화하는 CLI 도구입니다.",
        "en": "A CLI tool for AWS resource analysis, cost optimization,\nsecurity audits, and operations automation.",
    },
    "help_basic_usage": {
        "ko": "[기본 사용법]",
        "en": "[Basic Usage]",
    },
    "help_interactive_menu": {
        "ko": "대화형 메뉴 (검색/탐색/즐겨찾기)",
        "en": "Interactive menu (search/browse/favorites)",
    },
    "help_service_run": {
        "ko": "특정 서비스 도구 실행",
        "en": "Run tools for a specific service",
    },
    "help_headless_mode": {
        "ko": "[Headless 모드 (CI/CD용)]",
        "en": "[Headless Mode (for CI/CD)]",
    },
    "help_run_tool": {
        "ko": "도구 실행",
        "en": "Run a tool",
    },
    "help_list_tools": {
        "ko": "도구 목록 조회",
        "en": "List available tools",
    },
    "help_examples": {
        "ko": "예시:",
        "en": "Examples:",
    },
    "help_profile_groups": {
        "ko": "[프로파일 그룹]",
        "en": "[Profile Groups]",
    },
    "help_cli_examples": {
        "ko": "[예시]",
        "en": "[Examples]",
    },
    "help_ec2_tools": {
        "ko": "EC2 도구 실행",
        "en": "Run EC2 tools",
    },
    "help_iam_audit": {
        "ko": "IAM 보안 감사",
        "en": "IAM security audit",
    },
    "help_cost_analysis": {
        "ko": "비용 최적화 분석",
        "en": "Cost optimization analysis",
    },
    # =========================================================================
    # Run Command
    # =========================================================================
    "run_profile_required": {
        "ko": "오류: -p/--profile 또는 -g/--profile-group 중 하나를 지정하세요.",
        "en": "Error: Please specify either -p/--profile or -g/--profile-group.",
    },
    "run_profile_conflict": {
        "ko": "오류: -p/--profile과 -g/--profile-group은 동시에 사용할 수 없습니다.",
        "en": "Error: Cannot use -p/--profile and -g/--profile-group together.",
    },
    "run_group_not_found": {
        "ko": "오류: 그룹을 찾을 수 없습니다: {name}",
        "en": "Error: Group not found: {name}",
    },
    "run_group_list_hint": {
        "ko": "사용 가능한 그룹: aa group list",
        "en": "Available groups: aa group list",
    },
    # =========================================================================
    # List Tools Command
    # =========================================================================
    "category_not_found": {
        "ko": "카테고리를 찾을 수 없습니다: {name}",
        "en": "Category not found: {name}",
    },
    "available_tools": {
        "ko": "사용 가능한 도구",
        "en": "Available Tools",
    },
    "col_path": {
        "ko": "경로",
        "en": "Path",
    },
    "col_name": {
        "ko": "이름",
        "en": "Name",
    },
    "col_permission": {
        "ko": "권한",
        "en": "Permission",
    },
    "col_type": {
        "ko": "타입",
        "en": "Type",
    },
    "col_profiles": {
        "ko": "프로파일",
        "en": "Profiles",
    },
    "usage_hint": {
        "ko": "사용법: aa run <경로> -p <프로파일> -r <리전>",
        "en": "Usage: aa run <path> -p <profile> -r <region>",
    },
    # =========================================================================
    # Profile Group Commands
    # =========================================================================
    "no_groups_saved": {
        "ko": "저장된 프로파일 그룹이 없습니다.",
        "en": "No profile groups saved.",
    },
    "group_create_hint": {
        "ko": "aa group create 로 새 그룹을 만드세요.",
        "en": "Use 'aa group create' to create a new group.",
    },
    "profile_groups_title": {
        "ko": "프로파일 그룹",
        "en": "Profile Groups",
    },
    "and_n_more": {
        "ko": "외 {count}개",
        "en": "+{count} more",
    },
    "group_not_found": {
        "ko": "그룹을 찾을 수 없습니다: {name}",
        "en": "Group not found: {name}",
    },
    "label_name": {
        "ko": "이름:",
        "en": "Name:",
    },
    "label_type": {
        "ko": "타입:",
        "en": "Type:",
    },
    "label_created": {
        "ko": "생성:",
        "en": "Created:",
    },
    "label_profiles": {
        "ko": "프로파일:",
        "en": "Profiles:",
    },
    "group_title": {
        "ko": "그룹: {name}",
        "en": "Group: {name}",
    },
    "sso_profile": {
        "ko": "SSO 프로파일",
        "en": "SSO Profile",
    },
    "iam_access_key": {
        "ko": "IAM Access Key",
        "en": "IAM Access Key",
    },
    # =========================================================================
    # Group Create
    # =========================================================================
    "create_group_title": {
        "ko": "프로파일 그룹 생성",
        "en": "Create Profile Group",
    },
    "select_auth_type": {
        "ko": "그룹에 포함할 인증 타입을 선택하세요:",
        "en": "Select authentication type for the group:",
    },
    "select_prompt": {
        "ko": "선택",
        "en": "Select",
    },
    "no_profiles_available": {
        "ko": "사용 가능한 {type}이 없습니다.",
        "en": "No {type} available.",
    },
    "select_profiles_title": {
        "ko": "{type} 선택",
        "en": "Select {type}",
    },
    "select_2_or_more": {
        "ko": "(2개 이상 선택)",
        "en": "(select 2 or more)",
    },
    "selection_hint": {
        "ko": "예: 1 2 3 또는 1,2,3 또는 1-3",
        "en": "e.g.: 1 2 3 or 1,2,3 or 1-3",
    },
    "min_2_profiles": {
        "ko": "그룹은 2개 이상 프로파일이 필요합니다. (1개면 단일 선택 사용)",
        "en": "Groups require 2+ profiles. (Use single profile selection for 1)",
    },
    "selected_profiles": {
        "ko": "선택된 프로파일:",
        "en": "Selected profiles:",
    },
    "group_name_prompt": {
        "ko": "그룹 이름",
        "en": "Group name",
    },
    "group_saved": {
        "ko": "그룹 '{name}' 저장됨 ({count}개 프로파일)",
        "en": "Group '{name}' saved ({count} profiles)",
    },
    "group_save_failed": {
        "ko": "그룹 저장 실패 (이미 존재하거나 최대 개수 초과)",
        "en": "Failed to save group (already exists or max limit reached)",
    },
    # =========================================================================
    # Group Delete
    # =========================================================================
    "confirm_delete_group": {
        "ko": "그룹 '{name}' ({count}개 프로파일)을 삭제하시겠습니까?",
        "en": "Delete group '{name}' ({count} profiles)?",
    },
    "delete_prompt": {
        "ko": "삭제",
        "en": "Delete",
    },
    "cancelled": {
        "ko": "취소됨",
        "en": "Cancelled",
    },
    "group_deleted": {
        "ko": "그룹 '{name}' 삭제됨",
        "en": "Group '{name}' deleted",
    },
    "delete_failed": {
        "ko": "삭제 실패",
        "en": "Delete failed",
    },
    # =========================================================================
    # Tool List
    # =========================================================================
    "tool_list": {
        "ko": "도구 목록:",
        "en": "Tool list:",
    },
    # =========================================================================
    # IP Search
    # =========================================================================
    "no_profiles_hint": {
        "ko": "사용 가능한 프로파일이 없습니다. -p 옵션으로 지정하세요.",
        "en": "No profiles available. Please specify one with -p option.",
    },
    "no_eni_cache": {
        "ko": "ENI 캐시가 없습니다. Private 검색이 제한됩니다.",
        "en": "No ENI cache. Private search will be limited.",
    },
    "eni_cache_hint": {
        "ko": "전체 검색을 원하면 'aa ip'로 대화형 모드 진입 후 'cache' 명령 사용",
        "en": "For full search, use 'aa ip' interactive mode and run 'cache' command",
    },
    "searching_public_ip": {
        "ko": "Public IP 범위 검색 중...",
        "en": "Searching Public IP ranges...",
    },
    "searching_private_eni": {
        "ko": "Private ENI 검색 중...",
        "en": "Searching Private ENIs...",
    },
    "fetching_resource_detail": {
        "ko": "리소스 상세 정보 조회 중...",
        "en": "Fetching resource details...",
    },
    "error_with_message": {
        "ko": "오류: {message}",
        "en": "Error: {message}",
    },
}
