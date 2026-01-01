"""
plugins/vpc/sg_audit.py - Security Group Audit 도구

SG 현황 및 미사용 SG/규칙 분석

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from botocore.exceptions import ClientError
from rich.console import Console

from core.auth import SessionIterator
from core.tools.output import OutputPath, open_in_explorer

from .sg_audit_analysis import SGAnalyzer, SGCollector, SGExcelReporter

console = Console()


def run(ctx) -> None:
    """Security Group Audit 실행"""
    console.print("[bold]Security Group Audit 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: Security Group 데이터 수집 중...[/cyan]")

    # Account ID -> Name 매핑 생성
    account_names = {}
    if hasattr(ctx, "accounts") and ctx.accounts:
        for acc in ctx.accounts:
            account_names[acc.id] = acc.name

    collector = SGCollector()
    all_sgs = []
    skipped_regions = []

    # 중복 방지를 위한 수집 완료 추적
    collected_keys = set()

    with SessionIterator(ctx) as sessions:
        for session, identifier, region in sessions:
            try:
                # STS로 실제 Account ID 조회
                sts = session.client("sts")
                account_id = sts.get_caller_identity()["Account"]
                account_name = account_names.get(account_id, identifier)

                # 중복 수집 방지
                collect_key = f"{account_id}/{region}"
                if collect_key in collected_keys:
                    console.print(f"  [dim yellow]SKIP (중복): {account_name} / {region}[/dim yellow]")
                    continue
                collected_keys.add(collect_key)

                console.print(f"  [dim]{account_name} ({account_id}) / {region}[/dim]")
                sgs = collector.collect(session, account_id, account_name, region)
                all_sgs.extend(sgs)

            except ClientError as e:
                # Opt-in 리전 또는 비활성화된 리전은 건너뜀
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                skipped_regions.append(f"{region}: {error_code}")
                continue
            except Exception as e:
                skipped_regions.append(f"{region}: {str(e)}")
                continue

    # 건너뛴 리전 출력
    if skipped_regions:
        console.print(f"[dim]  (접근 불가 리전 {len(skipped_regions)}개 건너뜀)[/dim]")

    if not all_sgs:
        console.print("[yellow]수집된 Security Group이 없습니다.[/yellow]")
        if collector.errors:
            console.print("[red]오류 목록:[/red]")
            for err in collector.errors:
                console.print(f"  - {err}")
        return

    console.print(f"[green]총 {len(all_sgs)}개 Security Group 수집 완료[/green]")

    # 2. 분석
    console.print("[cyan]Step 2: 미사용 SG 및 Stale Rule 분석 중...[/cyan]")

    analyzer = SGAnalyzer(all_sgs)
    sg_results, rule_results = analyzer.analyze()
    summary = analyzer.get_summary(sg_results)

    # 통계 출력
    unused_count = sum(1 for r in sg_results if r.status.value == "Unused")
    stale_count = sum(1 for r in rule_results if r.status.value != "Active")
    high_count = sum(1 for r in rule_results if r.risk_level == "HIGH")
    medium_count = sum(1 for r in rule_results if r.risk_level == "MEDIUM")
    low_count = sum(1 for r in rule_results if r.risk_level == "LOW")

    console.print(f"  - 미사용 SG: [yellow]{unused_count}[/yellow]개")
    console.print(f"  - Stale 규칙: [yellow]{stale_count}[/yellow]개")
    if high_count > 0:
        console.print(f"  - [red bold]HIGH 위험 규칙: {high_count}개[/red bold] (위험 포트 노출)")
    if medium_count > 0:
        console.print(f"  - [yellow]MEDIUM 위험 규칙: {medium_count}개[/yellow] (일반 포트 노출)")
    if low_count > 0:
        console.print(f"  - [dim]LOW 규칙: {low_count}개[/dim] (웹 포트 - 일반적 허용)")

    # 3. Excel 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = SGExcelReporter(sg_results, rule_results, summary)
    filepath = reporter.generate(output_path)

    console.print(f"[bold green]보고서 생성 완료![/bold green]")
    console.print(f"  경로: {filepath}")

    # 오류 출력
    if collector.errors:
        console.print(f"\n[yellow]수집 중 오류 {len(collector.errors)}건:[/yellow]")
        for err in collector.errors[:5]:
            console.print(f"  - {err}")
        if len(collector.errors) > 5:
            console.print(f"  ... 외 {len(collector.errors) - 5}건")

    # 폴더 열기
    open_in_explorer(output_path)


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    # identifier 결정
    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("sg-audit").with_date().build()
    return output_path
