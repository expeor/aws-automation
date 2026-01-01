"""
core/tools/discovery.py - 플러그인 자동 발견 시스템

카테고리/도구를 자동으로 발견하여 menu.py 수동 관리 제거.
새 도구 추가: 폴더 생성 + __init__.py 작성만 하면 자동 등록.

폴더 구조:
    plugins/
    ├── analysis/        # 통합 분석 플랫폼 (cost, security, inventory, network, compliance, log, report)
    ├── {service}/       # AWS 서비스별 도구 (rds, ec2, s3, iam, kms, ...)

Usage:
    from core.tools.discovery import discover_categories, load_tool

    # 모든 카테고리/도구 발견
    categories = discover_categories()

    # 도구 동적 로드
    tool = load_tool("cost", "미사용 EBS 볼륨")
    tool["run"](ctx)
"""

import importlib
import logging
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.config import (
    get_plugins_path,
    get_project_root,
    settings,
    validate_tool_metadata,
)
from core.exceptions import DiscoveryError, MetadataValidationError, PluginLoadError

logger = logging.getLogger(__name__)

# =============================================================================
# 폴더 경로 설정 (core.config에서 중앙 관리)
# =============================================================================

# 프로젝트 루트 경로 (core.config 사용)
PROJECT_ROOT = get_project_root()

# 플러그인 폴더 경로 (core.config 사용)
PLUGINS_PATH = get_plugins_path()

# 스캔 대상 경로
SCAN_PATHS = [
    ("plugins", PLUGINS_PATH),  # 모든 플러그인 (analysis + {service})
]

# =============================================================================
# 캐시 설정
# =============================================================================

# 캐시 데이터 저장소 (Thread-safe)
_discovery_cache: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
_cache_lock = threading.RLock()


def _get_cache_key(include_aws_services: bool, only_analysis: bool) -> str:
    """캐시 키 생성"""
    return f"categories_{include_aws_services}_{only_analysis}"


def _is_cache_valid(cache_time: float) -> bool:
    """캐시 유효성 검사"""
    return (time.time() - cache_time) < settings.DISCOVERY_CACHE_TTL


def clear_discovery_cache() -> None:
    """디스커버리 캐시 초기화

    플러그인이 추가/수정되었을 때 호출하여 캐시를 갱신합니다.
    """
    global _discovery_cache
    with _cache_lock:
        _discovery_cache.clear()
    logger.debug("디스커버리 캐시 초기화됨")


# =============================================================================
# 분석 플랫폼 카테고리 우선순위 (core.config에서 가져옴)
# =============================================================================

# 분석 플랫폼 카테고리 우선순위 (메인 메뉴에 표시되는 순서)
ANALYSIS_CATEGORIES = list(settings.ANALYSIS_CATEGORIES)

# AWS 서비스 카테고리 이름들 (UI 필터링용)
# plugins/{service}/ 폴더명과 매칭
AWS_SERVICE_NAMES = {
    # Compute
    "ec2",
    "lambda",
    "elasticbeanstalk",
    # Containers
    "ecr",
    "ecs",
    "eks",
    # Storage
    "s3",
    "ebs",
    "efs",
    "fsx",
    "aws_backup",
    # Database
    "rds",
    "dynamodb",
    "documentdb",
    "elasticache",
    "opensearch",
    # Networking
    "vpc",
    "elb",
    "route53",
    "apigateway",
    # Security
    "iam",
    "kms",
    "waf",
    "guardduty",
    "secretsmanager",
    "acm",
    "cognito",
    # Management
    "cloudwatch",
    "cloudtrail",
    "config",
    "ssm",
    "trusted_advisor",
    "identity_center",
    # Analytics
    "kinesis",
    "glue",
    # Integration
    "sns",
    "sqs",
    "eventbridge",
    "stepfunctions",
    # Developer Tools
    "cloudformation",
    "codecommit",
    # ML
    "bedrock",
}


def _validate_category_metadata(
    module_path: str,
    category: Dict[str, Any],
    tools: List[Dict[str, Any]],
    strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """카테고리 및 도구 메타데이터 검증

    Args:
        module_path: 모듈 경로
        category: CATEGORY 딕셔너리
        tools: TOOLS 리스트
        strict: True면 검증 실패 시 예외 발생

    Returns:
        (검증된 카테고리 정보, 경고 메시지 리스트)

    Raises:
        MetadataValidationError: strict=True이고 검증 실패 시
    """
    warnings = []

    # 카테고리 필수 필드 검사
    if "name" not in category:
        warnings.append(f"{module_path}: CATEGORY에 'name' 필드 누락")
    if "description" not in category:
        warnings.append(f"{module_path}: CATEGORY에 'description' 필드 누락")

    # 도구 메타데이터 검증
    validated_tools = []
    for i, tool in enumerate(tools):
        tool_errors = validate_tool_metadata(tool)
        if tool_errors:
            tool_name = tool.get("name", f"tool[{i}]")
            for error in tool_errors:
                warnings.append(f"{module_path}/{tool_name}: {error}")

            if strict:
                raise MetadataValidationError(
                    plugin_name=module_path,
                    errors=tool_errors,
                )
        validated_tools.append(tool)

    # 검증된 카테고리 정보 반환
    cat_info = category.copy()
    cat_info["tools"] = validated_tools

    return cat_info, warnings


def discover_categories(
    include_aws_services: bool = False,
    only_analysis: bool = False,
    use_cache: bool = True,
    validate: bool = True,
) -> List[Dict[str, Any]]:
    """모든 스캔 경로에서 카테고리/도구 자동 발견

    각 카테고리 폴더의 __init__.py에서 CATEGORY, TOOLS를 읽어옴.
    서브폴더도 재귀적으로 스캔함.

    Args:
        include_aws_services: True면 AWS 서비스 카테고리도 포함 (기본: 분석 도구만)
        only_analysis: True면 분석 플랫폼 카테고리(cost, security 등)만 반환
        use_cache: True면 캐시 사용 (기본값: True)
        validate: True면 메타데이터 검증 수행 (기본값: True)

    Returns:
        [
            {
                "name": "cost",
                "description": "비용 최적화",
                "tools": [...],
                "module_path": "core.analysis.cost",
                "_source": "analysis",  # 출처: analysis, aws_services, tools
            },
            ...
        ]
    """
    # 캐시 확인
    if use_cache:
        cache_key = _get_cache_key(include_aws_services, only_analysis)
        with _cache_lock:
            if cache_key in _discovery_cache:
                cached_data, cache_time = _discovery_cache[cache_key]
                if _is_cache_valid(cache_time):
                    logger.debug(f"캐시 히트: {cache_key}")
                    return cached_data.copy()

    categories = []
    validation_warnings = []

    # 제외할 폴더/파일 (core.config 사용)
    exclude = settings.PLUGIN_EXCLUDE_DIRS

    def scan_directory(path: Path, base_module_path: str, source: str):
        """재귀적으로 디렉토리를 스캔"""
        if not path.exists():
            return

        for item in sorted(path.iterdir()):
            # 폴더만, _나 .로 시작하지 않는 것만
            if not item.is_dir():
                continue
            if item.name.startswith(("_", ".")) or item.name in exclude:
                continue

            try:
                module_path = f"{base_module_path}.{item.name}"
                module = importlib.import_module(module_path)

                # CATEGORY와 TOOLS가 정의되어 있어야 함
                if hasattr(module, "CATEGORY") and hasattr(module, "TOOLS"):
                    raw_category = module.CATEGORY
                    raw_tools = module.TOOLS

                    # 메타데이터 검증
                    if validate:
                        cat_info, warnings = _validate_category_metadata(
                            module_path, raw_category, raw_tools
                        )
                        validation_warnings.extend(warnings)
                    else:
                        cat_info = raw_category.copy()
                        cat_info["tools"] = raw_tools

                    cat_info["module_path"] = module_path
                    cat_info["_source"] = source

                    categories.append(cat_info)
                    logger.debug(f"카테고리 발견: {module_path} (source={source})")
                else:
                    logger.debug(f"스킵 (메타데이터 없음): {module_path}")

                # 서브디렉토리도 스캔 (재귀)
                scan_directory(item, module_path, source)

            except ImportError as e:
                logger.warning(f"카테고리 로드 실패: {item.name} - {e}")
            except MetadataValidationError as e:
                logger.error(f"메타데이터 검증 실패: {e}")
            except Exception as e:
                logger.warning(f"카테고리 로드 오류: {item.name} - {e}")

    # 모든 경로 스캔
    for base_module, path in SCAN_PATHS:
        source = path.name  # analysis, aws_services, tools
        scan_directory(path, base_module, source)

    # 검증 경고 로깅
    if validation_warnings:
        for warning in validation_warnings[:10]:  # 최대 10개만 로그
            logger.warning(warning)
        if len(validation_warnings) > 10:
            logger.warning(f"... 외 {len(validation_warnings) - 10}개 검증 경고")

    # 필터링 적용
    if only_analysis:
        # 분석 플랫폼 카테고리만
        categories = [c for c in categories if c.get("name") in ANALYSIS_CATEGORIES]
    elif not include_aws_services:
        # AWS 서비스 카테고리 제외 (분석 카테고리만)
        categories = [c for c in categories if c.get("name") not in AWS_SERVICE_NAMES]

    # 우선순위 정렬
    def sort_key(cat):
        name = cat.get("name", "")
        # 분석 카테고리 우선
        if name in ANALYSIS_CATEGORIES:
            return (0, ANALYSIS_CATEGORIES.index(name))
        # 나머지 (AWS 서비스 등)
        return (1, name)

    categories.sort(key=sort_key)

    # 캐시 저장
    if use_cache:
        cache_key = _get_cache_key(include_aws_services, only_analysis)
        with _cache_lock:
            _discovery_cache[cache_key] = (categories.copy(), time.time())
            logger.debug(f"캐시 저장: {cache_key}")

    return categories


def discover_all_categories() -> List[Dict[str, Any]]:
    """모든 카테고리 발견 (AWS 서비스 포함)

    개발자/AI가 기존 코드를 참조할 때 사용.

    Returns:
        모든 카테고리 목록 (AWS 서비스 포함)
    """
    return discover_categories(include_aws_services=True)


def get_category(
    name: str, include_aws_services: bool = True
) -> Optional[Dict[str, Any]]:
    """카테고리 이름 또는 별칭으로 조회

    Args:
        name: 카테고리 이름 또는 별칭 (예: "cost", "gov")
        include_aws_services: AWS 서비스 카테고리도 조회 (기본값 True - 내부 참조용)

    Returns:
        카테고리 정보 또는 None
    """
    for cat in discover_categories(include_aws_services=include_aws_services):
        if cat["name"] == name:
            return cat
        # 별칭(aliases) 지원
        aliases = cat.get("aliases", [])
        if name in aliases:
            return cat
    return None


def load_tool(category_name: str, tool_name: str) -> Optional[Dict[str, Callable]]:
    """도구 동적 로드

    Args:
        category_name: 카테고리 이름 (예: "ebs")
        tool_name: 도구 이름 (예: "미사용 볼륨")

    Returns:
        {
            "run": <실행 함수>,
            "collect_options": <옵션 수집 함수> 또는 None,
            "meta": <도구 메타데이터>,
        }
        또는 None (찾을 수 없는 경우)
    """
    category = get_category(category_name)
    if not category:
        logger.warning(f"카테고리를 찾을 수 없음: {category_name}")
        return None

    # 도구 찾기
    tool_meta = None
    for tool in category["tools"]:
        if tool["name"] == tool_name:
            tool_meta = tool
            break

    if not tool_meta:
        logger.warning(f"도구를 찾을 수 없음: {category_name}/{tool_name}")
        return None

    # 참조(ref) 필드가 있으면 원본 도구 로드
    if "ref" in tool_meta:
        return _load_referenced_tool(tool_meta)

    # 모듈 로드
    try:
        module_name = tool_meta.get("module", tool_name)
        full_module_path = f"{category['module_path']}.{module_name}"
        module = importlib.import_module(full_module_path)

        # run 함수 (필수)
        run_func_name = tool_meta.get("function", "run")
        if not hasattr(module, run_func_name):
            logger.error(f"run 함수 없음: {full_module_path}.{run_func_name}")
            return None

        run_func = getattr(module, run_func_name)

        # collect_options 함수 (선택)
        collect_func = getattr(module, "collect_options", None)

        return {
            "run": run_func,
            "collect_options": collect_func,
            "meta": tool_meta,
        }

    except ImportError as e:
        logger.error(f"도구 모듈 로드 실패: {full_module_path} - {e}")
        return None
    except Exception as e:
        logger.error(f"도구 로드 오류: {category_name}/{tool_name} - {e}")
        return None


def _load_referenced_tool(tool_meta: Dict[str, Any]) -> Optional[Dict[str, Callable]]:
    """참조된 도구 로드 (Collection용)

    Args:
        tool_meta: ref 필드를 포함한 도구 메타데이터
            예: {"name": "미사용 Role", "ref": "iam/unused_role"}

    Returns:
        참조된 원본 도구의 로드 결과
    """
    ref = tool_meta.get("ref", "")
    if "/" not in ref:
        logger.error(f"잘못된 ref 형식: {ref} (예: 'iam/unused_role')")
        return None

    ref_category, ref_module = ref.split("/", 1)

    # 원본 카테고리 조회
    original_category = get_category(ref_category)
    if not original_category:
        logger.warning(f"참조 카테고리를 찾을 수 없음: {ref_category}")
        return None

    # 원본 도구 찾기 (module 이름으로 매칭)
    original_tool = None
    for tool in original_category["tools"]:
        if tool.get("module") == ref_module:
            original_tool = tool
            break

    if not original_tool:
        logger.warning(f"참조 도구를 찾을 수 없음: {ref}")
        return None

    # 원본 도구 로드
    try:
        full_module_path = f"{original_category['module_path']}.{ref_module}"
        module = importlib.import_module(full_module_path)

        run_func_name = original_tool.get("function", "run")
        if not hasattr(module, run_func_name):
            logger.error(f"run 함수 없음: {full_module_path}.{run_func_name}")
            return None

        run_func = getattr(module, run_func_name)
        collect_func = getattr(module, "collect_options", None)

        # 메타데이터는 컬렉션의 것과 원본을 병합 (컬렉션이 우선)
        merged_meta = {**original_tool, **tool_meta}
        merged_meta["_original_ref"] = ref  # 원본 참조 정보 유지

        return {
            "run": run_func,
            "collect_options": collect_func,
            "meta": merged_meta,
        }

    except ImportError as e:
        logger.error(f"참조 도구 모듈 로드 실패: {full_module_path} - {e}")
        return None
    except Exception as e:
        logger.error(f"참조 도구 로드 오류: {ref} - {e}")
        return None


def list_categories() -> List[str]:
    """카테고리 이름 목록 반환"""
    return [cat["name"] for cat in discover_categories()]


def list_tools(category_name: str) -> List[str]:
    """카테고리 내 도구 이름 목록 반환"""
    category = get_category(category_name)
    if not category:
        return []
    return [tool["name"] for tool in category["tools"]]


def list_tools_by_area(area: str) -> List[Dict[str, Any]]:
    """영역(area)별 도구 목록 반환

    Args:
        area: 영역 문자열 (security, cost, performance, fault_tolerance,
              service_limits, operational, inventory)

    Returns:
        [
            {
                "category": "ebs",
                "tool": {...},  # 도구 메타데이터
            },
            ...
        ]
    """
    results = []
    for category in discover_categories():
        for tool in category["tools"]:
            if tool.get("area") == area:
                results.append(
                    {
                        "category": category["name"],
                        "category_description": category.get("description", ""),
                        "tool": tool,
                    }
                )
    return results


def get_area_summary() -> Dict[str, int]:
    """영역별 도구 개수 요약

    Returns:
        {"security": 15, "cost": 12, ...}
    """
    summary: Dict[str, int] = {}
    for category in discover_categories():
        for tool in category["tools"]:
            area = tool.get("area", "unknown")
            summary[area] = summary.get(area, 0) + 1
    return summary
