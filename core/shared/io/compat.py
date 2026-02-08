"""호환성 헬퍼 모듈

기존 플러그인에서 Excel과 HTML을 동시에 생성할 수 있도록 하는 래퍼 함수

Usage:
    from core.shared.io.compat import generate_reports

    def run(ctx) -> None:
        results = parallel_collect(ctx, _collect, service="ec2")

        # Excel + HTML 동시 생성 (ctx.output_config 설정에 따라)
        generate_reports(
            ctx,
            data=results.get_flat_data(),
            excel_generator=lambda d: _save_excel(results, d),
            html_config={
                "title": "EC2 미사용 인스턴스",
                "service": "EC2",
                "tool_name": "unused",
            },
        )
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext
    from core.shared.io.config import OutputConfig


def generate_reports(
    ctx: ExecutionContext,
    data: list[dict[str, Any]],
    excel_generator: Callable[[str], str] | None = None,
    html_config: dict[str, Any] | None = None,
    output_dir: str | None = None,
) -> dict[str, str]:
    """Excel과 HTML 리포트 동시 생성

    기존 플러그인의 Excel 생성 함수를 그대로 사용하면서
    HTML 리포트도 자동 생성할 수 있는 래퍼 함수.

    Args:
        ctx: 실행 컨텍스트
        data: 리포트에 표시할 데이터 (dict 리스트)
        excel_generator: Excel 생성 함수 (output_dir -> filepath)
            None이면 Excel 생성 스킵
        html_config: HTML 리포트 설정 (title, service, tool_name 등)
            None이면 HTML 생성 스킵
        output_dir: 출력 디렉토리 (None이면 자동 생성)

    Returns:
        생성된 파일 경로 딕셔너리 {"excel": "...", "html": "..."}

    Example:
        results = generate_reports(
            ctx,
            data=analysis_results,
            excel_generator=lambda d: _save_excel(data, d),
            html_config={
                "title": "EC2 미사용 인스턴스 분석",
                "service": "EC2",
                "tool_name": "unused",
                "total": 100,
                "found": 10,
                "savings": 500.0,
            },
        )
        print(f"Excel: {results.get('excel')}")
        print(f"HTML: {results.get('html')}")
    """
    from .html import open_in_browser

    results: dict[str, str] = {}

    # 출력 설정 가져오기
    output_config = _get_output_config(ctx)

    # 출력 디렉토리 결정
    if output_dir is None:
        output_dir = output_config.output_dir or _get_default_output_dir(ctx)

    # Excel 생성
    if output_config.should_output_excel() and excel_generator is not None:
        try:
            excel_path = excel_generator(output_dir)
            results["excel"] = excel_path

            # auto_open은 Excel에서 이미 처리됨 (Workbook.save()에서)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Excel 생성 실패: {e}")

    # HTML 생성
    if output_config.should_output_html() and html_config is not None and data:
        try:
            html_path = _generate_html_from_data(ctx, data, html_config, output_dir)
            results["html"] = html_path

            if output_config.auto_open:
                open_in_browser(html_path)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"HTML 생성 실패: {e}")

    return results


def _get_output_config(ctx: ExecutionContext) -> OutputConfig:
    """컨텍스트에서 출력 설정 가져오기

    Args:
        ctx: 실행 컨텍스트

    Returns:
        ctx.output_config가 있으면 반환, 없으면 기본 OutputConfig 생성
    """
    from .config import OutputConfig

    if hasattr(ctx, "output_config") and ctx.output_config is not None:
        return ctx.output_config

    # 기본값: Excel + HTML 모두 출력
    lang = getattr(ctx, "lang", "ko")
    return OutputConfig(lang=lang)


def _get_default_output_dir(ctx: ExecutionContext) -> str:
    """기본 출력 디렉토리 생성

    프로파일명, 카테고리, 도구명, 날짜를 조합하여 출력 경로를 자동 생성합니다.

    Args:
        ctx: 실행 컨텍스트

    Returns:
        생성된 출력 디렉토리 절대 경로
    """
    from .output import OutputPath
    from .output.helpers import get_context_identifier

    identifier = get_context_identifier(ctx)

    # 카테고리 및 도구명 추출
    category = ctx.category or "report"
    tool_name = "output"
    if ctx.tool:
        tool_name = getattr(ctx.tool, "name", "output").replace(" ", "_").lower()

    return OutputPath(identifier).sub(category, tool_name).with_date().build()


def _generate_html_from_data(
    ctx: ExecutionContext,
    data: list[dict[str, Any]],
    config: dict[str, Any],
    output_dir: str,
) -> str:
    """데이터에서 HTML 리포트 생성

    Args:
        ctx: 실행 컨텍스트
        data: 리포트 데이터
        config: HTML 설정 (title, service, tool_name, total, found, savings 등)
        output_dir: 출력 디렉토리

    Returns:
        생성된 HTML 파일 경로
    """
    from datetime import datetime

    from .html import create_aws_report

    title = config.get("title", "분석 결과")
    service = config.get("service", "AWS")
    tool_name = config.get("tool_name", "report")

    # 리포트 생성
    report = create_aws_report(
        title=title,
        service=service,
        tool_name=tool_name,
        ctx=ctx,
        resources=data,
        total=config.get("total"),
        found=config.get("found"),
        savings=config.get("savings", 0.0),
    )

    # 파일명 생성
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{service.lower()}_{tool_name}_{today}.html"
    filepath = Path(output_dir) / filename

    # 디렉토리 생성
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # 저장 (auto_open은 호출자가 처리)
    report.save(filepath, auto_open=False)

    return str(filepath)


def generate_dual_report(
    ctx: ExecutionContext,
    data: list[dict[str, Any]],
    output_dir: str,
    prefix: str,
    excel_builder: Callable[[], Any],
    html_config: dict[str, Any] | None = None,
    html_builder: Callable[[str], str] | None = None,
    region: str | None = None,
) -> dict[str, str]:
    """Excel과 HTML을 동시에 생성하는 고수준 API

    새 플러그인에서 사용하기 편리한 API.
    기존 generate_reports보다 더 명시적인 인터페이스 제공.

    Args:
        ctx: 실행 컨텍스트
        data: 리포트 데이터 (dict 리스트)
        output_dir: 출력 디렉토리
        prefix: 파일명 접두사 (예: "ec2_unused")
        excel_builder: Excel Workbook 생성 함수 (빌더 패턴)
            () -> Workbook (이미 데이터가 채워진 상태)
        html_config: HTML 리포트 설정 (자동 HTML 생성용)
            html_builder와 동시 사용 불가.
        html_builder: 커스텀 HTML 생성 함수 (output_dir -> filepath)
            복잡한 HTML 리포트가 필요한 경우 사용.
            html_config와 동시 사용 불가.
        region: 리전 (파일명에 포함, 옵션)

    Returns:
        생성된 파일 경로 딕셔너리 {"excel": "...", "html": "..."}

    Example:
        def build_workbook():
            wb = Workbook()
            sheet = wb.new_sheet("Results", columns)
            for row in data:
                sheet.add_row(row)
            return wb

        results = generate_dual_report(
            ctx,
            data=analysis_data,
            output_dir=output_path,
            prefix="ec2_unused",
            excel_builder=build_workbook,
            html_config={
                "title": "EC2 미사용 분석",
                "service": "EC2",
                "tool_name": "unused",
            },
            region="ap-northeast-2",
        )
    """
    from .html import open_in_browser

    results: dict[str, str] = {}
    output_config = _get_output_config(ctx)

    # 디렉토리 생성
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Excel 생성
    if output_config.should_output_excel():
        try:
            wb = excel_builder()
            excel_path = wb.save_as(output_dir, prefix, region)
            results["excel"] = str(excel_path)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Excel 생성 실패: {e}")

    # HTML 생성
    if output_config.should_output_html() and data:
        try:
            if html_builder is not None:
                html_path = html_builder(output_dir)
            elif html_config is not None:
                html_path = _generate_html_from_data(ctx, data, html_config, output_dir)
            else:
                html_path = None

            if html_path:
                results["html"] = html_path
                if output_config.auto_open:
                    open_in_browser(html_path)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"HTML 생성 실패: {e}")

    return results
