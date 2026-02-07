"""
plugins/cost/unused_all/orchestrator.py - 병렬 수집 오케스트레이션

세션별 병렬 수집 및 결과 집계 로직
"""

from __future__ import annotations

import re
import threading
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from core.parallel import is_quiet, parallel_collect, quiet_mode, set_quiet
from shared.aws.metrics import SharedMetricCache
from shared.io.output import OutputPath, get_context_identifier, open_in_explorer

from .collectors import REGIONAL_COLLECTORS, collect_route53, collect_s3
from .report import generate_report
from .types import (
    RESOURCE_FIELD_MAP,
    WASTE_FIELDS,
    SessionCollectionResult,
    UnusedAllResult,
    UnusedResourceSummary,
)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

from cli.ui import (
    console,
    print_error,
    print_header,
    print_sub_info,
    print_sub_task_done,
    print_sub_warning,
    print_warning,
)

try:
    from cli.ui import parallel_progress
except ImportError:
    parallel_progress = None  # type: ignore[assignment]


# =============================================================================
# 전역 서비스 수집 동기화 (Thread-safe)
# =============================================================================

_global_lock = threading.Lock()
_global_collected: set = set()


def _reset_global_tracking() -> None:
    """전역 서비스 추적 초기화 (새 실행 시 호출)"""
    global _global_collected
    with _global_lock:
        _global_collected = set()


def _should_collect_global(account_id: str) -> bool:
    """해당 계정의 전역 서비스를 수집해야 하는지 확인 (thread-safe)"""
    with _global_lock:
        if account_id in _global_collected:
            return False
        _global_collected.add(account_id)
        return True


# =============================================================================
# 결과 적용 및 병합
# =============================================================================


def _apply_result(
    summary: UnusedResourceSummary,
    session_result: SessionCollectionResult,
    resource_type: str,
    data: dict[str, Any],
) -> None:
    """리소스 결과를 요약 및 세션 결과에 적용 (매핑 기반)"""
    if "error" in data:
        session_result.errors.append(data["error"])
        return

    cfg = RESOURCE_FIELD_MAP.get(resource_type)
    if not cfg:
        return

    # summary 필드 설정
    setattr(summary, cfg["total"], data.get("total", 0))
    setattr(summary, cfg["unused"], data.get(cfg["data_unused"], 0))
    if cfg["waste"]:
        setattr(summary, cfg["waste"], data.get("waste", 0.0))

    # session_result 필드 설정
    result_data = data.get(cfg["data_key"])
    if result_data:
        setattr(session_result, cfg["session"], result_data)


def _run_collector_quiet(collector, session, account_id, account_name, region, quiet):
    """워커 스레드에서 quiet 상태를 설정하고 collector 실행"""
    set_quiet(quiet)
    return collector(session, account_id, account_name, region)


def _run_global_collector_quiet(collector, session, account_id, account_name, quiet):
    """워커 스레드에서 quiet 상태를 설정하고 글로벌 collector 실행"""
    set_quiet(quiet)
    return collector(session, account_id, account_name)


def collect_session_resources(
    session,
    account_id: str,
    account_name: str,
    region: str,
    selected_resources: set | None = None,
) -> SessionCollectionResult:
    """단일 세션의 모든 리소스를 병렬로 수집

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: AWS 리전
        selected_resources: 스캔할 리소스 set (None이면 전체)

    Returns:
        SessionCollectionResult: 수집 결과

    Note:
        SharedMetricCache를 사용하여 세션 내 동일 메트릭 중복 조회 방지.
        SharedMetricCache는 스레드 간 공유가 가능하여 ThreadPoolExecutor
        워커들도 캐시에 접근할 수 있습니다.
    """
    summary = UnusedResourceSummary(
        account_id=account_id,
        account_name=account_name,
        region=region,
    )
    result = SessionCollectionResult(summary=summary)

    # 부모 스레드의 quiet 상태를 가져와서 워커에 전파
    parent_quiet = is_quiet()

    # 선택적 스캔: 선택된 리소스만 수집
    collectors_to_run = REGIONAL_COLLECTORS
    if selected_resources:
        collectors_to_run = {k: v for k, v in REGIONAL_COLLECTORS.items() if k in selected_resources}

    # SharedMetricCache로 세션 내 메트릭 캐싱 활성화 (스레드 간 공유 가능)
    with SharedMetricCache():
        # 리전별 리소스 병렬 수집 (최대 10개 동시 실행)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures_map: dict[Future[Any], str] = {}
            for name, collector in collectors_to_run.items():
                future = executor.submit(
                    _run_collector_quiet,
                    collector,
                    session,
                    account_id,
                    account_name,
                    region,
                    parent_quiet,
                )
                futures_map[future] = name

            for future in as_completed(futures_map):
                resource_type = futures_map[future]
                try:
                    data = future.result()
                    _apply_result(summary, result, resource_type, data)
                except Exception as e:
                    result.errors.append(f"{resource_type}: {e}")

        # 글로벌 서비스 (계정당 한 번만 수집)
        # 선택적 스캔: route53, s3가 선택되었는지 확인
        collect_route53_flag = not selected_resources or "route53" in selected_resources
        collect_s3_flag = not selected_resources or "s3" in selected_resources

        if _should_collect_global(account_id) and (collect_route53_flag or collect_s3_flag):
            with ThreadPoolExecutor(max_workers=2) as executor:
                global_futures: dict[str, Future[Any]] = {}

                if collect_route53_flag:
                    global_futures["route53"] = executor.submit(
                        _run_global_collector_quiet,
                        collect_route53,
                        session,
                        account_id,
                        account_name,
                        parent_quiet,
                    )

                if collect_s3_flag:
                    global_futures["s3"] = executor.submit(
                        _run_global_collector_quiet,
                        collect_s3,
                        session,
                        account_id,
                        account_name,
                        parent_quiet,
                    )

                for resource_type, future in global_futures.items():
                    try:
                        data = future.result()
                        _apply_result(summary, result, resource_type, data)
                    except Exception as e:
                        result.errors.append(f"{resource_type}: {e}")

    return result


def _merge_session_result(final: UnusedAllResult, session_result: SessionCollectionResult) -> None:
    """세션 결과를 최종 결과에 병합 (매핑 기반)"""
    final.summaries.append(session_result.summary)

    for cfg in RESOURCE_FIELD_MAP.values():
        session_field = cfg["session"]
        final_field = cfg["final"]
        session_data = getattr(session_result, session_field, None)

        if session_data:
            final_list = getattr(final, final_field)
            # findings는 리스트이므로 extend, 나머지는 단일 결과이므로 append
            if session_field.endswith("_findings"):
                final_list.extend(session_data)
            else:
                final_list.append(session_data)


# =============================================================================
# 옵션 수집 (CLI 프롬프트)
# =============================================================================


def collect_options(ctx: ExecutionContext) -> None:
    """미사용 리소스 분석 옵션 수집

    사용자에게 전체 스캔 또는 선택 스캔 옵션을 제공합니다.

    Args:
        ctx: ExecutionContext
    """
    import questionary

    print_header("미사용 리소스 종합 분석 설정")

    # 스캔 모드 선택
    scan_mode = questionary.select(
        "스캔 모드를 선택하세요:",
        choices=[
            questionary.Choice("전체 스캔 (모든 리소스)", value="all"),
            questionary.Choice("선택 스캔 (리소스 직접 선택)", value="select"),
        ],
        style=questionary.Style([("highlighted", "bold")]),
    ).ask()

    if scan_mode == "select":
        # 리소스 선택을 위한 체크박스
        resource_choices = [
            questionary.Choice(f"{cfg['display']} ({key})", value=key) for key, cfg in RESOURCE_FIELD_MAP.items()
        ]

        selected = questionary.checkbox(
            "분석할 리소스를 선택하세요 (Space로 선택, Enter로 확정):",
            choices=resource_choices,
            style=questionary.Style([("highlighted", "bold")]),
        ).ask()

        if selected:
            ctx.options["resources"] = selected
            print_sub_task_done(f"선택됨: {', '.join(selected)}")
        else:
            print_sub_warning("선택 없음 - 전체 스캔으로 진행합니다.")
            ctx.options["resources"] = None
    else:
        ctx.options["resources"] = None
        print_sub_task_done("전체 리소스 스캔으로 진행합니다.")


# =============================================================================
# 메인 실행
# =============================================================================


def run(ctx: ExecutionContext, resources: list[str] | None = None) -> None:
    """미사용 리소스 종합 분석 실행 (병렬 처리)

    Args:
        ctx: 실행 컨텍스트
        resources: 스캔할 리소스 목록 (None이면 전체)
                   예: ["nat", "ebs", "eip", "lambda"]
    """
    # ctx.options에서 리소스 목록 가져오기 (collect_options에서 설정)
    if resources is None:
        resources = ctx.options.get("resources")

    # 선택적 스캔 설정
    if resources:
        selected = set(resources)
        invalid = selected - set(RESOURCE_FIELD_MAP.keys())
        if invalid:
            print_error(f"알 수 없는 리소스: {', '.join(invalid)}")
            print_sub_info(f"사용 가능: {', '.join(RESOURCE_FIELD_MAP.keys())}")
            return
    else:
        selected = None

    # 전역 서비스 추적 초기화
    _reset_global_tracking()

    # 선택적 스캔을 위한 래퍼 함수
    def collect_wrapper(session, account_id, account_name, region):
        return collect_session_resources(session, account_id, account_name, region, selected_resources=selected)

    # 병렬 수집 실행 (quiet_mode로 콘솔 출력 억제)
    # timeline이 ctx에 있으면 parallel_collect가 자동으로 프로그레스 연결
    if parallel_progress is not None:
        with parallel_progress("리소스 수집", console=console) as tracker, quiet_mode():
            parallel_result = parallel_collect(
                ctx,
                collect_wrapper,
                max_workers=20,
                service="multi",
                progress_tracker=tracker,
            )
    else:
        with quiet_mode():
            parallel_result = parallel_collect(
                ctx,
                collect_wrapper,
                max_workers=20,
                service="multi",
            )

    # 결과 집계
    final_result = UnusedAllResult()
    all_errors: list[str] = []

    for task_result in parallel_result.results:
        if task_result.success and task_result.data:
            session_result = task_result.data
            _merge_session_result(final_result, session_result)

            # 세션별 에러 수집
            if session_result.errors:
                for err in session_result.errors:
                    all_errors.append(f"{task_result.identifier}/{task_result.region}: {err}")
        elif task_result.error:
            all_errors.append(str(task_result.error))

    if not final_result.summaries:
        print_warning("분석 결과 없음")
        return

    # 총 절감 가능 금액 계산 (WASTE_FIELDS 활용)
    total_waste = sum(sum(getattr(s, field, 0) for field in WASTE_FIELDS) for s in final_result.summaries)

    # 요약 출력 (RESOURCE_FIELD_MAP 활용)
    from cli.ui.console import print_rule

    print_rule("종합 결과")

    for resource_key, cfg in RESOURCE_FIELD_MAP.items():
        # 선택적 스캔인 경우 선택된 리소스만 출력
        if selected and resource_key not in selected:
            continue
        _print_summary(
            cfg["display"],
            final_result.summaries,
            cfg["total"],
            cfg["unused"],
            cfg["waste"],
        )

    if total_waste > 0:
        console.print(f"\n[bold yellow]총 월간 절감 가능: ${total_waste:,.2f}[/bold yellow]")

    # 실행 통계
    print_sub_info(f"계정/리전: {parallel_result.success_count}개 성공, {parallel_result.error_count}개 실패")

    # 보고서 생성

    identifier = get_context_identifier(ctx)

    output_path = OutputPath(identifier).sub("cost", "unused-all").with_date().build()
    filepath = generate_report(final_result, output_path)

    print_sub_task_done(f"저장 완료: {filepath}")

    if all_errors:
        _print_error_summary(all_errors)

    open_in_explorer(output_path)


def _print_error_summary(errors: list[str]) -> None:
    """오류 요약 출력 (유형별 그룹화)"""
    # 오류 코드별로 그룹화
    # 형식: "{profile}/{region}: {resource}: {message}"
    error_groups: dict[str, list[str]] = defaultdict(list)

    for err in errors:
        # 오류 코드 추출 시도
        # 예: "UnrecognizedClientException", "InvalidClientTokenId", "AuthFailure"
        code_match = re.search(
            r"(UnrecognizedClientException|InvalidClientTokenId|AuthFailure|"
            r"AccessDenied|ExpiredToken|InvalidAccessKeyId|SignatureDoesNotMatch|"
            r"ThrottlingException|ServiceUnavailable|InternalError|"
            r"UnauthorizedOperation|OptInRequired)",
            err,
        )

        # 알 수 없는 오류는 "기타"로 분류
        error_code = code_match.group(1) if code_match else "기타"

        # 리전 추출
        region_match = re.match(r"[^/]+/([^:]+):", err)
        region = region_match.group(1) if region_match else "unknown"

        error_groups[error_code].append(region)

    # 출력
    print_warning(f"오류 {len(errors)}건")

    for error_code, regions in sorted(error_groups.items(), key=lambda x: -len(x[1])):
        unique_regions = sorted(set(regions))
        if len(unique_regions) <= 3:
            region_str = ", ".join(unique_regions)
        else:
            region_str = f"{', '.join(unique_regions[:3])} 외 {len(unique_regions) - 3}개"
        print_sub_info(f"{error_code}: {region_str} ({len(regions)}건)")


def _print_summary(
    name: str,
    summaries: list,
    total_attr: str,
    unused_attr: str,
    waste_attr: str | None,
) -> None:
    """요약 출력 헬퍼"""
    total = sum(getattr(s, total_attr, 0) for s in summaries)
    unused = sum(getattr(s, unused_attr, 0) for s in summaries)
    waste = sum(getattr(s, waste_attr, 0) for s in summaries) if waste_attr else 0

    console.print(f"\n[bold]{name}[/bold]: 전체 {total}개", end="")
    if unused > 0:
        waste_str = f" (${waste:,.2f}/월)" if waste > 0 else ""
        console.print(f" / [red]미사용 {unused}개{waste_str}[/red]")
    else:
        console.print("")
