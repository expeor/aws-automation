"""
core/tools/types.py - 도구 메타데이터 타입 정의

Area(영역) 분류의 단일 소스.
UI 레이어(main_menu, category step)는 이 모듈을 import해서 사용.
"""

from typing import TypedDict


class AreaInfo(TypedDict):
    """Area 메타데이터"""

    key: str  # 내부 키 (security, cost 등)
    command: str  # CLI 명령어 (/cost, /security)
    label: str  # 한글 라벨
    desc: str  # 설명
    color: str  # Rich 색상
    icon: str  # 이모지 아이콘


# ============================================================================
# Area 분류 체계
# - ReportType (10): 상태 점검 보고서 타입
# - ToolType (5): 도구 타입 (분석/액션)
# - 참조: core/tools/output/report_types.py
# ============================================================================
AREA_REGISTRY: list[AreaInfo] = [
    # === ReportType - Core (5) ===
    {
        "key": "unused",
        "command": "/unused",
        "label": "미사용",
        "desc": "미사용 리소스 식별",
        "color": "red",
        "icon": "🗑️",
    },
    {
        "key": "security",
        "command": "/security",
        "label": "보안",
        "desc": "취약점, 암호화 점검",
        "color": "magenta",
        "icon": "🔒",
    },
    {
        "key": "cost",
        "command": "/cost",
        "label": "비용",
        "desc": "비용 최적화 기회",
        "color": "cyan",
        "icon": "💰",
    },
    {
        "key": "audit",
        "command": "/audit",
        "label": "감사",
        "desc": "구성 설정 점검",
        "color": "yellow",
        "icon": "📋",
    },
    {
        "key": "inventory",
        "command": "/inventory",
        "label": "인벤토리",
        "desc": "리소스 현황 파악",
        "color": "green",
        "icon": "📦",
    },
    # === ReportType - Extended (5) ===
    {
        "key": "backup",
        "command": "/backup",
        "label": "백업",
        "desc": "백업 체계 점검",
        "color": "blue",
        "icon": "💾",
    },
    {
        "key": "compliance",
        "command": "/compliance",
        "label": "컴플라이언스",
        "desc": "규정 준수 검증",
        "color": "bright_magenta",
        "icon": "✅",
    },
    {
        "key": "performance",
        "command": "/perf",
        "label": "성능",
        "desc": "성능 최적화",
        "color": "purple",
        "icon": "⚡",
    },
    {
        "key": "network",
        "command": "/network",
        "label": "네트워크",
        "desc": "네트워크 구조 분석",
        "color": "bright_blue",
        "icon": "🌐",
    },
    {
        "key": "quota",
        "command": "/quota",
        "label": "쿼터",
        "desc": "서비스 한도 모니터링",
        "color": "bright_yellow",
        "icon": "📊",
    },
    # === ToolType - Analysis (2) ===
    {
        "key": "log",
        "command": "/log",
        "label": "로그",
        "desc": "로그 분석 및 검색",
        "color": "dim",
        "icon": "📜",
    },
    {
        "key": "search",
        "command": "/search",
        "label": "검색",
        "desc": "리소스 역추적",
        "color": "bright_cyan",
        "icon": "🔍",
    },
    # === ToolType - Actions (3) ===
    {
        "key": "cleanup",
        "command": "/cleanup",
        "label": "정리",
        "desc": "리소스 정리/삭제",
        "color": "bright_red",
        "icon": "🧹",
    },
    {
        "key": "tag",
        "command": "/tag",
        "label": "태그",
        "desc": "태그 일괄 적용",
        "color": "bright_green",
        "icon": "🏷️",
    },
    {
        "key": "sync",
        "command": "/sync",
        "label": "동기화",
        "desc": "설정/태그 동기화",
        "color": "bright_white",
        "icon": "🔄",
    },
]

# /command → internal key 매핑 (자동 생성)
AREA_COMMANDS: dict[str, str] = {}
for _area in AREA_REGISTRY:
    AREA_COMMANDS[_area["command"]] = _area["key"]
# 추가 별칭
AREA_COMMANDS["/sec"] = "security"

# 한글 키워드 → internal key 매핑
AREA_KEYWORDS: dict[str, str] = {
    # unused
    "미사용": "unused",
    "유휴": "unused",
    "고아": "unused",
    # security
    "보안": "security",
    "취약": "security",
    "암호화": "security",
    "퍼블릭": "security",
    # cost
    "비용": "cost",
    "절감": "cost",
    "최적화": "cost",
    # audit
    "감사": "audit",
    "점검": "audit",
    # inventory
    "현황": "inventory",
    "인벤토리": "inventory",
    "목록": "inventory",
    # backup
    "백업": "backup",
    "복구": "backup",
    # performance
    "성능": "performance",
    # search
    "검색": "search",
    "추적": "search",
    # cleanup
    "정리": "cleanup",
    "삭제": "cleanup",
    # tag
    "태그": "tag",
    # sync
    "동기화": "sync",
}

# 문자열 키 기반 AREA_DISPLAY (category.py 호환)
AREA_DISPLAY_BY_KEY: dict[str, dict[str, str]] = {
    a["key"]: {"label": a["label"], "color": a["color"], "icon": a["icon"]} for a in AREA_REGISTRY
}


class ToolMeta(TypedDict, total=False):
    """도구 메타데이터 타입"""

    # 필수 필드
    name: str  # 도구 이름 (메뉴에 표시)
    description: str  # 설명
    permission: str  # "read" | "write" | "delete"
    module: str  # 모듈 경로 (파일명 또는 폴더.파일명)

    # 영역 분류
    area: str  # ToolArea 값 (security, cost, performance 등)

    # 하위 서비스 분류 (예: elb→alb/nlb/gwlb, elasticache→redis/memcached)
    sub_service: str  # 하위 서비스명 (예: "alb", "nlb", "redis")

    # 참조 (컬렉션용)
    ref: str  # 다른 카테고리 도구 참조 ("iam/unused_role")

    # 실행 제약 조건
    single_region_only: bool  # True면 단일 리전만 지원 (기본: False)
    single_account_only: bool  # True면 단일 계정만 지원 (기본: False)

    # 추가 메타
    meta: dict[str, str]  # 추가 메타데이터 (cycle, internal_only 등)
    function: str  # 실행 함수명 (기본: "run")


class CategoryMeta(TypedDict, total=False):
    """카테고리 메타데이터 타입"""

    # 필수 필드
    name: str  # 카테고리 이름 (CLI 명령어, 폴더명)
    description: str  # 설명

    # 선택 필드
    display_name: str  # UI 표시 이름 (없으면 name 사용)
    aliases: list[str]  # 별칭 (예: ["gov"])
    group: str  # 그룹 ("aws" | "special" | "collection")
    icon: str  # 아이콘 (메뉴 표시용)

    # 하위 서비스 (예: elb→["alb", "nlb", "gwlb", "clb"])
    # sub_services에 정의된 이름으로 CLI 명령어 자동 등록
    # 각 도구의 sub_service 필드와 매칭되어 필터링됨
    sub_services: list[str]

    # 컬렉션 전용
    collection: bool  # 컬렉션 여부 (True면 다른 도구 참조)
