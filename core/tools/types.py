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


# ============================================================================
# AWS Trusted Advisor 5대 영역만 사용
# - 새로운 영역을 추가하지 마세요
# - 참조: https://docs.aws.amazon.com/awssupport/latest/user/trusted-advisor.html
# ============================================================================
AREA_REGISTRY: List[AreaInfo] = [
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
        "desc": "미사용 리소스 탐지",
        "color": "cyan",
        "icon": "💰",
    },
    {
        "key": "fault_tolerance",
        "command": "/ft",
        "label": "내결함성",
        "desc": "백업, Multi-AZ",
        "color": "blue",
        "icon": "🛡️",
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
        "key": "operational",
        "command": "/ops",
        "label": "운영",
        "desc": "보고서, 모니터링",
        "color": "bright_blue",
        "icon": "📋",
    },
]

# /command → internal key 매핑 (자동 생성)
AREA_COMMANDS: Dict[str, str] = {}
for _area in AREA_REGISTRY:
    AREA_COMMANDS[_area["command"]] = _area["key"]
# 추가 별칭
AREA_COMMANDS["/sec"] = "security"
AREA_COMMANDS["/op"] = "operational"

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
    # fault_tolerance
    "내결함성": "fault_tolerance",
    "가용성": "fault_tolerance",
    "백업": "fault_tolerance",
    "복구": "fault_tolerance",
    # performance
    "성능": "performance",
    # operational
    "운영": "operational",
    "보고서": "operational",
    "리포트": "operational",
    "현황": "operational",
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

    # 하위 서비스 분류 (예: elb→alb/nlb/gwlb, elasticache→redis/memcached)
    sub_service: str  # 하위 서비스명 (예: "alb", "nlb", "redis")

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

    # 하위 서비스 (예: elb→["alb", "nlb", "gwlb", "clb"])
    # sub_services에 정의된 이름으로 CLI 명령어 자동 등록
    # 각 도구의 sub_service 필드와 매칭되어 필터링됨
    sub_services: List[str]

    # 컬렉션 전용
    collection: bool  # 컬렉션 여부 (True면 다른 도구 참조)
