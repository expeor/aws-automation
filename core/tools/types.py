"""
core/tools/types.py - 도구 메타데이터 타입 정의

Area(영역) 분류의 단일 소스.
UI 레이어(main_menu, category step)는 이 모듈을 import해서 사용.
"""

from typing import Dict, List, TypedDict


class AreaInfo(TypedDict):
    """Area 메타데이터"""

    key: str  # 내부 키 (security, cost 등)
    command: str  # CLI 명령어 (/cost, /security)
    label: str  # 한글 라벨
    desc: str  # 설명
    color: str  # Rich 색상
    icon: str  # 이모지 아이콘


# Area 정의 (단일 소스) - 순서대로 UI에 표시
AREA_REGISTRY: List[AreaInfo] = [
    {"key": "cost", "command": "/cost", "label": "비용 절감", "desc": "미사용 리소스 탐지", "color": "yellow", "icon": "💰"},
    {"key": "security", "command": "/security", "label": "보안", "desc": "취약점, 암호화 점검", "color": "red", "icon": "🔒"},
    {"key": "operational", "command": "/ops", "label": "운영", "desc": "보고서, 모니터링", "color": "cyan", "icon": "📋"},
    {"key": "inventory", "command": "/inv", "label": "인벤토리", "desc": "리소스 목록", "color": "white", "icon": "📦"},
    {"key": "fault_tolerance", "command": "/ft", "label": "가용성", "desc": "백업, Multi-AZ", "color": "blue", "icon": "🛡️"},
    {"key": "log", "command": "/log", "label": "로그", "desc": "로그 분석", "color": "green", "icon": "📝"},
    {"key": "network", "command": "/net", "label": "네트워크", "desc": "네트워크 분석", "color": "magenta", "icon": "🌐"},
    {"key": "performance", "command": "/perf", "label": "성능", "desc": "성능 최적화", "color": "yellow", "icon": "⚡"},
    {"key": "service_limits", "command": "/limits", "label": "서비스 한도", "desc": "쿼터 모니터링", "color": "magenta", "icon": "📊"},
]

# /command → internal key 매핑 (자동 생성)
AREA_COMMANDS: Dict[str, str] = {}
for _area in AREA_REGISTRY:
    AREA_COMMANDS[_area["command"]] = _area["key"]
# 추가 별칭
AREA_COMMANDS["/sec"] = "security"
AREA_COMMANDS["/op"] = "operational"
AREA_COMMANDS["/inventory"] = "inventory"
AREA_COMMANDS["/network"] = "network"

# 한글 키워드 → internal key 매핑
AREA_KEYWORDS: Dict[str, str] = {
    # security
    "보안": "security",
    "취약": "security",
    "암호화": "security",
    "퍼블릭": "security",
    # cost
    "비용": "cost",
    "미사용": "cost",
    "절감": "cost",
    "유휴": "cost",
    # operational
    "운영": "operational",
    "보고서": "operational",
    "리포트": "operational",
    "현황": "operational",
    # inventory
    "목록": "inventory",
    "인벤토리": "inventory",
    "조회": "inventory",
    # fault_tolerance
    "가용성": "fault_tolerance",
    "백업": "fault_tolerance",
    "복구": "fault_tolerance",
    # log
    "로그": "log",
    # network
    "네트워크": "network",
    # performance
    "성능": "performance",
}

# 문자열 키 기반 AREA_DISPLAY (category.py 호환)
AREA_DISPLAY_BY_KEY: Dict[str, Dict[str, str]] = {
    a["key"]: {"label": a["label"], "color": a["color"], "icon": a["icon"]}
    for a in AREA_REGISTRY
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

    # 참조 (컬렉션용)
    ref: str  # 다른 카테고리 도구 참조 ("iam/unused_role")

    # 실행 제약 조건
    single_region_only: bool  # True면 단일 리전만 지원 (기본: False)
    single_account_only: bool  # True면 단일 계정만 지원 (기본: False)

    # 추가 메타
    meta: dict  # 추가 메타데이터 (cycle, internal_only 등)
    function: str  # 실행 함수명 (기본: "run")


class CategoryMeta(TypedDict, total=False):
    """카테고리 메타데이터 타입"""

    # 필수 필드
    name: str  # 카테고리 이름 (CLI 명령어, 폴더명)
    description: str  # 설명

    # 선택 필드
    display_name: str  # UI 표시 이름 (없으면 name 사용)
    aliases: List[str]  # 별칭 (예: ["gov"])
    group: str  # 그룹 ("aws" | "special" | "collection")
    icon: str  # 아이콘 (메뉴 표시용)

    # 컬렉션 전용
    collection: bool  # 컬렉션 여부 (True면 다른 도구 참조)
