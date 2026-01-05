"""
core/tools/output/report_types.py - 보고서/도구 타입 상수 정의

출력 경로 표준화를 위한 타입 상수.
경로 구조: output/{profile}/{service}/{type}/{date}/

구조:
  Reports (상태 점검) - read-only
    └─ inventory, security, cost, unused, audit
       compliance, performance, network, backup, quota

  Tools (도구 모음) - active operations
    ├─ Analysis (조회/분석): log, search
    └─ Actions (실행/변경): cleanup, rotate, sync, ...
"""

from enum import Enum


class ReportType(str, Enum):
    """Reports - 상태 점검 보고서 타입 (read-only)"""

    # Core (5)
    INVENTORY = "inventory"  # 리소스 현황 파악
    SECURITY = "security"  # 보안 취약점 탐지
    COST = "cost"  # 비용 최적화 기회 발굴
    UNUSED = "unused"  # 미사용 리소스 식별
    AUDIT = "audit"  # 구성 설정 점검

    # Extended (5)
    COMPLIANCE = "compliance"  # 규정 준수 검증
    PERFORMANCE = "performance"  # 성능 병목 분석
    NETWORK = "network"  # 네트워크 구조 분석
    BACKUP = "backup"  # 백업 체계 점검
    QUOTA = "quota"  # 서비스 한도 모니터링


class ToolType(str, Enum):
    """Tools - 도구 타입 (active operations)"""

    # Analysis (조회/분석)
    LOG = "log"  # 로그 분석 및 검색
    SEARCH = "search"  # 리소스 역추적

    # Actions (실행/변경)
    CLEANUP = "cleanup"  # 리소스 정리/삭제
    TAG = "tag"  # 태그 일괄 적용
    SYNC = "sync"  # 설정/태그 동기화


# 타입 카테고리 분류
TOOL_CATEGORIES = {
    "analysis": [ToolType.LOG, ToolType.SEARCH],
    "actions": [ToolType.CLEANUP, ToolType.TAG, ToolType.SYNC],
}


# 타입 설명 (UI/문서용)
REPORT_TYPE_DESCRIPTIONS = {
    ReportType.INVENTORY: {
        "name": "인벤토리",
        "purpose": "리소스 현황 파악",
        "description": "AWS 계정 내 리소스 목록과 기본 속성을 수집. 전체 인프라 가시성 확보의 시작점.",
    },
    ReportType.SECURITY: {
        "name": "보안",
        "purpose": "보안 취약점 탐지",
        "description": "퍼블릭 노출, 과도한 권한, 암호화 미적용 등 보안 위험 요소 식별.",
    },
    ReportType.COST: {
        "name": "비용",
        "purpose": "비용 최적화 기회 발굴",
        "description": "RI/SP 미사용, 과다 프로비저닝, 비용 이상 징후 탐지. 삭제가 아닌 최적화 관점.",
    },
    ReportType.UNUSED: {
        "name": "미사용",
        "purpose": "미사용 리소스 식별",
        "description": "연결 없음, 트래픽 0, 장기 미접근 등 삭제 가능한 리소스 후보 추출.",
    },
    ReportType.AUDIT: {
        "name": "감사",
        "purpose": "구성 설정 점검",
        "description": "AWS Well-Architected, 보안 베스트 프랙티스 대비 설정 편차 분석.",
    },
    ReportType.COMPLIANCE: {
        "name": "컴플라이언스",
        "purpose": "규정 준수 검증",
        "description": "필수 태그, 암호화 정책, 리전 제한 등 조직 표준 준수 여부 점검.",
    },
    ReportType.PERFORMANCE: {
        "name": "성능",
        "purpose": "성능 병목 분석",
        "description": "CPU, 메모리, IOPS, 네트워크 사용률 기반 병목 구간 및 사이징 이슈 탐지.",
    },
    ReportType.NETWORK: {
        "name": "네트워크",
        "purpose": "네트워크 구조 분석",
        "description": "VPC, 서브넷, 라우팅, 피어링, 엔드포인트 등 연결 구조와 흐름 파악.",
    },
    ReportType.BACKUP: {
        "name": "백업",
        "purpose": "백업 체계 점검",
        "description": "자동 백업 설정, 보존 기간, 스냅샷 현황, 복구 가능성 검증.",
    },
    ReportType.QUOTA: {
        "name": "쿼터",
        "purpose": "서비스 한도 모니터링",
        "description": "서비스 쿼터 사용률 추적. 한도 임박 시 사전 경고로 장애 예방.",
    },
}

TOOL_TYPE_DESCRIPTIONS = {
    ToolType.LOG: {
        "name": "로그",
        "category": "analysis",
        "purpose": "로그 분석 및 검색",
        "description": "CloudWatch Logs, CloudTrail 등에서 패턴 검색, 이상 탐지, 시계열 분석 수행.",
    },
    ToolType.SEARCH: {
        "name": "검색",
        "category": "analysis",
        "purpose": "리소스 역추적",
        "description": "IP, ENI, 인스턴스 ID 등으로 연관 리소스 탐색. 장애 원인 추적, 연결 관계 파악.",
    },
    ToolType.CLEANUP: {
        "name": "정리",
        "category": "actions",
        "purpose": "리소스 정리/삭제",
        "description": "미사용 리소스 삭제, 오래된 스냅샷 정리, 고아 볼륨 제거 등 정리 작업 수행.",
    },
    ToolType.TAG: {
        "name": "태그",
        "category": "actions",
        "purpose": "태그 일괄 적용",
        "description": "리소스 태그 일괄 추가/수정/삭제. 태그 정책 적용, 누락 태그 보완.",
    },
    ToolType.SYNC: {
        "name": "동기화",
        "category": "actions",
        "purpose": "설정/태그 동기화",
        "description": "계정/리전 간 태그, 설정, 정책 동기화. 일관성 유지 및 표준화.",
    },
}


# 편의 함수
def get_all_types() -> list[str]:
    """모든 타입 문자열 반환"""
    return [t.value for t in ReportType] + [t.value for t in ToolType]


def get_report_types() -> list[str]:
    """Report 타입만 반환"""
    return [t.value for t in ReportType]


def get_tool_types() -> list[str]:
    """Tool 타입만 반환"""
    return [t.value for t in ToolType]


def is_valid_type(type_str: str) -> bool:
    """유효한 타입인지 확인"""
    return type_str in get_all_types()


def is_report_type(type_str: str) -> bool:
    """Report 타입인지 확인"""
    return type_str in get_report_types()


def is_tool_type(type_str: str) -> bool:
    """Tool 타입인지 확인"""
    return type_str in get_tool_types()
