"""ALB 로그 분석 - 대화형 프롬프트 함수

ALB 선택, S3 버킷 입력, 시간 범위 선택 등 사용자 인터랙션 처리
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pytz
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.parallel import get_client

console = Console()
logger = logging.getLogger(__name__)


def _select_alb_with_pagination(
    alb_list: list[dict[str, Any]],
    page_size: int = 20,
) -> dict[str, Any] | None:
    """페이지네이션으로 ALB 선택

    Args:
        alb_list: ALB 정보 리스트 [{"lb": ..., "name": ..., "scheme": ..., "status": ...}, ...]
        page_size: 페이지당 항목 수 (기본 20)

    Returns:
        선택된 ALB의 lb 객체 또는 None

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    if not alb_list:
        return None

    total = len(alb_list)
    (total + page_size - 1) // page_size
    current_page = 0
    filtered_list = alb_list  # 검색 필터링된 리스트

    while True:
        # 현재 페이지 항목 계산
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(filtered_list))
        page_items = filtered_list[start_idx:end_idx]

        # 테이블 출력
        table = Table(
            title=f"[bold #FF9900]ALB 목록[/bold #FF9900] (페이지 {current_page + 1}/{max(1, (len(filtered_list) + page_size - 1) // page_size)}, 총 {len(filtered_list)}개)",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("No.", style="dim", width=5, justify="right")
        table.add_column("ALB 이름", style="#FF9900", min_width=30)
        table.add_column("Scheme", width=16, justify="center")
        table.add_column("로그", width=4, justify="center")

        for i, item in enumerate(page_items, start=start_idx + 1):
            table.add_row(
                str(i),
                item["name"],
                item["scheme"],
                item["status"],
            )

        console.print()
        console.print(table)

        # 네비게이션 안내
        nav_hints = []
        if current_page > 0:
            nav_hints.append("[dim]p: 이전[/dim]")
        if end_idx < len(filtered_list):
            nav_hints.append("[dim]n: 다음[/dim]")
        nav_hints.append("[dim]/검색어: 검색[/dim]")
        nav_hints.append("[dim]q: 취소[/dim]")

        console.print(" | ".join(nav_hints))

        # 입력 받기
        try:
            user_input = questionary.text(
                "번호 입력 또는 명령:",
            ).ask()
        except KeyboardInterrupt:
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        if user_input is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        user_input = user_input.strip()

        # 빈 입력 무시
        if not user_input:
            continue

        # 명령어 처리
        if user_input.lower() == "q":
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        if user_input.lower() == "n":
            if end_idx < len(filtered_list):
                current_page += 1
            else:
                console.print("[yellow]마지막 페이지입니다.[/yellow]")
            continue

        if user_input.lower() == "p":
            if current_page > 0:
                current_page -= 1
            else:
                console.print("[yellow]첫 번째 페이지입니다.[/yellow]")
            continue

        # 검색 처리 (/로 시작)
        if user_input.startswith("/"):
            search_term = user_input[1:].strip().lower()
            if search_term:
                filtered_list = [item for item in alb_list if search_term in item["name"].lower()]
                current_page = 0
                if not filtered_list:
                    console.print(f"[yellow]'{search_term}' 검색 결과가 없습니다. 전체 목록으로 복원합니다.[/yellow]")
                    filtered_list = alb_list
                else:
                    console.print(f"[green]'{search_term}' 검색 결과: {len(filtered_list)}개[/green]")
            else:
                # 빈 검색어는 전체 목록 복원
                filtered_list = alb_list
                current_page = 0
                console.print("[green]전체 목록으로 복원합니다.[/green]")
            continue

        # 번호 입력 처리
        try:
            selected_num = int(user_input)
            if 1 <= selected_num <= len(filtered_list):
                selected_item = filtered_list[selected_num - 1]
                console.print(f"[green]✓ 선택됨: {selected_item['name']}[/green]")
                return dict(selected_item["lb"])
            else:
                console.print(f"[red]1~{len(filtered_list)} 범위의 번호를 입력하세요.[/red]")
        except ValueError:
            console.print("[yellow]번호, 명령어(n/p/q), 또는 /검색어를 입력하세요.[/yellow]")


def _get_bucket_input_with_options(session, ctx) -> str | None:
    """S3 버킷 경로 입력 방식 선택

    Returns:
        S3 버킷 경로 또는 None (취소 시)

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    choices = [
        questionary.Choice("ALB 로그 경로 자동 탐색", value="auto"),
        questionary.Choice("ALB 로그 경로 수동 입력", value="manual"),
    ]

    choice = questionary.select(
        "S3 버킷 경로 입력 방식을 선택하세요:",
        choices=choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "auto":
        return _get_lb_and_build_path(session, ctx)
    else:
        return _get_bucket_input_manual()


def _get_lb_and_build_path(session, ctx) -> str | None:
    """ALB를 선택하고 액세스 로그 S3 경로를 자동 생성한다.

    ALB 목록 조회 -> 사용자 선택 -> 로그 설정 확인 -> S3 경로 조합.

    Args:
        session: boto3 session.
        ctx: ExecutionContext.

    Returns:
        자동 생성된 S3 경로 또는 None (실패 시 수동 입력으로 전환).
    """
    from botocore.exceptions import ClientError

    elbv2_client = get_client(session, "elbv2")

    # ALB 목록 조회
    try:
        console.print("[#FF9900]Application Load Balancer 목록을 조회하는 중...[/#FF9900]")
        response = elbv2_client.describe_load_balancers()

        albs = [lb for lb in response["LoadBalancers"] if lb["Type"] == "application"]

        if not albs:
            console.print("[yellow]! 이 계정에 ALB가 없습니다. 수동 입력으로 전환합니다.[/yellow]")
            return _get_bucket_input_manual()

        console.print(f"[green]✓ {len(albs)}개의 ALB를 발견했습니다.[/green]")

    except ClientError as e:
        if "AccessDenied" in str(e):
            console.print("[yellow]! ELB API 접근 권한이 없습니다. 수동 입력으로 전환합니다.[/yellow]")
        else:
            console.print(f"[yellow]! ALB 조회 실패: {e}. 수동 입력으로 전환합니다.[/yellow]")
        return _get_bucket_input_manual()

    # ALB 선택 - 목록 생성
    alb_list: list[dict[str, Any]] = []

    for lb in sorted(albs, key=lambda x: x["LoadBalancerName"]):
        # 로그 설정 확인
        try:
            attrs = elbv2_client.describe_load_balancer_attributes(LoadBalancerArn=lb["LoadBalancerArn"])
            log_enabled = any(
                attr["Key"] == "access_logs.s3.enabled" and attr["Value"] == "true" for attr in attrs["Attributes"]
            )
            status = "[green]✓[/green]" if log_enabled else "[red]✗[/red]"
        except Exception as e:
            logger.debug("Failed to get ALB log status: %s", e)
            status = "[dim]?[/dim]"

        alb_list.append(
            {
                "lb": lb,
                "name": lb["LoadBalancerName"],
                "scheme": lb["Scheme"],
                "status": status,
            }
        )

    # 페이지네이션으로 ALB 선택
    selected_lb = _select_alb_with_pagination(alb_list)

    if not selected_lb:
        return _get_bucket_input_manual()

    # 로그 설정 확인
    try:
        attrs = elbv2_client.describe_load_balancer_attributes(LoadBalancerArn=selected_lb["LoadBalancerArn"])

        log_config = {}
        for attr in attrs["Attributes"]:
            if attr["Key"] == "access_logs.s3.enabled":
                log_config["enabled"] = attr["Value"] == "true"
            elif attr["Key"] == "access_logs.s3.bucket":
                log_config["bucket"] = attr["Value"]
            elif attr["Key"] == "access_logs.s3.prefix":
                log_config["prefix"] = attr["Value"]

        if not log_config.get("enabled"):
            console.print(
                f"[yellow]⚠️ '{selected_lb['LoadBalancerName']}'의 액세스 로그가 비활성화되어 있습니다.[/yellow]"
            )
            return _get_bucket_input_manual()

        if not log_config.get("bucket"):
            console.print(f"[yellow]⚠️ '{selected_lb['LoadBalancerName']}'의 로그 버킷 정보가 없습니다.[/yellow]")
            return _get_bucket_input_manual()

        # S3 경로 생성
        bucket_name = log_config["bucket"]
        prefix = log_config.get("prefix", "")

        # 계정 ID 추출
        try:
            sts = get_client(session, "sts")
            account_id = sts.get_caller_identity()["Account"]
        except Exception as e:
            logger.debug("Failed to get account ID: %s", e)
            account_id = "unknown"

        # 리전 추출
        region = selected_lb["AvailabilityZones"][0]["ZoneName"][:-1]

        # S3 경로 생성
        if prefix:
            s3_path = f"s3://{bucket_name}/{prefix}/AWSLogs/{account_id}/elasticloadbalancing/{region}/"
        else:
            s3_path = f"s3://{bucket_name}/AWSLogs/{account_id}/elasticloadbalancing/{region}/"

        console.print(f"[green]✓ 자동 생성된 S3 경로: {s3_path}[/green]")
        return s3_path

    except ClientError as e:
        console.print(f"[yellow]! 로그 설정 조회 실패: {e}. 수동 입력으로 전환합니다.[/yellow]")
        return _get_bucket_input_manual()


def _get_bucket_input_manual() -> str | None:
    """수동으로 S3 버킷 경로 입력

    Returns:
        S3 버킷 경로 또는 None (취소 시)
    """
    console.print(
        Panel(
            "[bold #FF9900]S3 버킷 경로 형식:[/bold #FF9900]\n"
            "s3://bucket-name/prefix\n\n"
            "[bold #FF9900]예시:[/bold #FF9900]\n"
            "s3://my-alb-logs/AWSLogs/123456789012/elasticloadbalancing/ap-northeast-2",
            title="[bold]버킷 경로 안내[/bold]",
        )
    )

    while True:
        bucket = questionary.text(
            "S3 버킷 경로를 입력하세요 (s3://...):",
        ).ask()

        # Ctrl+C 또는 ESC로 취소한 경우
        if bucket is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        if not bucket.strip():
            console.print("[red]S3 버킷 경로를 입력해주세요.[/red]")
            continue

        if not bucket.startswith("s3://"):
            bucket = f"s3://{bucket}"

        # 기본 검증
        parts = bucket.split("/")
        if len(parts) < 3 or not parts[2]:
            console.print("[red]유효하지 않은 S3 경로입니다.[/red]")
            continue

        # 필수 경로 확인
        required = ["/AWSLogs/", "/elasticloadbalancing/"]
        missing = [p for p in required if p not in bucket]
        if missing:
            console.print(f"[yellow]⚠️ 필수 경로가 누락됨: {', '.join(missing)}[/yellow]")
            confirm = questionary.confirm("그래도 이 경로를 사용하시겠습니까?", default=False).ask()
            if confirm is None:
                raise KeyboardInterrupt("사용자가 취소했습니다.")
            if not confirm:
                continue

        return str(bucket)


def _get_time_range_input() -> tuple[datetime, datetime]:
    """시간 범위 입력

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    console.print("\n[bold #FF9900]분석 시간 범위 설정[/bold #FF9900]")
    console.print(f"[dim]기본값: {yesterday.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}[/dim]")

    # 빠른 선택 (기본값인 24시간을 첫 번째에 배치)
    quick_choices = [
        questionary.Choice("최근 24시간", value="24h"),
        questionary.Choice("최근 1시간", value="1h"),
        questionary.Choice("최근 6시간", value="6h"),
        questionary.Choice("최근 7일", value="7d"),
        questionary.Choice("직접 입력", value="custom"),
    ]

    choice = questionary.select(
        "시간 범위를 선택하세요:",
        choices=quick_choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "custom":
        # 직접 입력
        start_str = questionary.text(
            "시작 시간 (YYYY-MM-DD HH:MM):",
        ).ask()
        if start_str is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        end_str = questionary.text(
            "종료 시간 (YYYY-MM-DD HH:MM):",
        ).ask()
        if end_str is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        try:
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print("[yellow]⚠️ 잘못된 형식. 기본값(24시간)을 사용합니다.[/yellow]")
            start_time = yesterday
            end_time = now
    else:
        # 빠른 선택
        time_deltas = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
        }
        delta = time_deltas.get(choice, timedelta(days=1))
        start_time = now - delta
        end_time = now

    console.print(
        f"[green]✓ 분석 기간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}[/green]"
    )
    return start_time, end_time


def _get_timezone_input() -> str:
    """타임존 입력

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    tz_choices = [
        questionary.Choice("Asia/Seoul (한국)", value="Asia/Seoul"),
        questionary.Choice("UTC", value="UTC"),
        questionary.Choice("America/New_York", value="America/New_York"),
        questionary.Choice("Europe/London", value="Europe/London"),
        questionary.Choice("직접 입력", value="custom"),
    ]

    choice = questionary.select(
        "타임존을 선택하세요:",
        choices=tz_choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "custom":
        tz = questionary.text("타임존 입력:", default="Asia/Seoul").ask()
        if tz is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")
        try:
            pytz.timezone(tz)
            return str(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            console.print("[yellow]⚠️ 잘못된 타임존. Asia/Seoul을 사용합니다.[/yellow]")
            return "Asia/Seoul"

    return str(choice)
