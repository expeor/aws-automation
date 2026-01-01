"""
core/tools/types.py - 도구 메타데이터 타입 정의

Trusted Advisor 스타일의 영역(Area) 분류 및 도구 타입 정의.
"""

from enum import Enum
from typing import List, Optional, TypedDict


class ToolArea(str, Enum):
    """도구 영역 분류 (Trusted Advisor 스타일)

    각 도구가 어떤 관점의 검사/분석을 수행하는지 나타냅니다.
    """

    # 보안 (Security) - 취약점, 노출, 암호화, 접근 제어
    SECURITY = "security"

    # 비용 최적화 (Cost Optimization) - 미사용 리소스, 비용 절감
    COST = "cost"

    # 성능 (Performance) - 성능 병목, 최적화 기회
    PERFORMANCE = "performance"

    # 내결함성/고가용성 (Fault Tolerance) - 복원력, 가용성, 백업
    FAULT_TOLERANCE = "fault_tolerance"

    # 서비스 할당량 (Service Limits) - 쿼터, 한도 모니터링
    SERVICE_LIMITS = "service_limits"

    # 운영 우수성 (Operational Excellence) - 베스트 프랙티스, 거버넌스
    OPERATIONAL = "operational"

    # 인벤토리/정보 수집 (Inventory) - 리소스 목록, 현황 파악
    INVENTORY = "inventory"


# 영역별 아이콘 및 한글명
AREA_DISPLAY = {
    ToolArea.SECURITY: {"icon": "🔒", "name": "보안", "color": "red"},
    ToolArea.COST: {"icon": "💰", "name": "비용 최적화", "color": "green"},
    ToolArea.PERFORMANCE: {"icon": "⚡", "name": "성능", "color": "yellow"},
    ToolArea.FAULT_TOLERANCE: {"icon": "🛡️", "name": "내결함성", "color": "blue"},
    ToolArea.SERVICE_LIMITS: {"icon": "📊", "name": "서비스 한도", "color": "magenta"},
    ToolArea.OPERATIONAL: {"icon": "📋", "name": "운영 우수성", "color": "cyan"},
    ToolArea.INVENTORY: {"icon": "📦", "name": "인벤토리", "color": "white"},
}


def get_area_display(area: str | ToolArea) -> dict:
    """영역 표시 정보 반환

    Args:
        area: 영역 문자열 또는 ToolArea enum

    Returns:
        {"icon": "🔒", "name": "보안", "color": "red"}
    """
    if isinstance(area, str):
        try:
            area = ToolArea(area)
        except ValueError:
            return {"icon": "❓", "name": area, "color": "white"}

    return AREA_DISPLAY.get(area, {"icon": "❓", "name": str(area), "color": "white"})


def format_area_badge(area: str | ToolArea) -> str:
    """영역 배지 문자열 생성 (Rich 마크업)

    Args:
        area: 영역 문자열 또는 ToolArea enum

    Returns:
        "[red]🔒 보안[/red]" 형태의 문자열
    """
    display = get_area_display(area)
    return (
        f"[{display['color']}]{display['icon']} {display['name']}[/{display['color']}]"
    )


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


# 영역별 권장 조치 설명
AREA_RECOMMENDATIONS = {
    ToolArea.SECURITY: "보안 취약점을 즉시 해결하여 데이터 유출 및 무단 접근을 방지하세요.",
    ToolArea.COST: "미사용 리소스를 정리하고 적절한 크기로 조정하여 비용을 절감하세요.",
    ToolArea.PERFORMANCE: "병목 지점을 해소하고 최신 세대로 업그레이드하여 성능을 개선하세요.",
    ToolArea.FAULT_TOLERANCE: "Multi-AZ 구성 및 백업을 활성화하여 장애 복원력을 확보하세요.",
    ToolArea.SERVICE_LIMITS: "서비스 한도에 도달하기 전에 미리 증가를 요청하세요.",
    ToolArea.OPERATIONAL: "AWS 모범 사례를 따라 운영 효율성과 거버넌스를 강화하세요.",
    ToolArea.INVENTORY: "리소스 현황을 파악하여 관리 및 계획 수립에 활용하세요.",
}
