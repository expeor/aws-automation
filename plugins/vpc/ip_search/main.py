"""
plugins/vpc/ip_search/main.py - IP 검색 메인 모듈

통합 검색: Public (클라우드 대역) + Private (AWS ENI) 동시 검색
다양한 쿼리 지원: IP, CIDR, ENI ID, VPC ID, Instance ID, 텍스트 등
"""

import csv
import os
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.parallel import parallel_collect
from core.tools.output.builder import OutputPath

console = Console()


# =============================================================================
# 세션 및 출력 경로
# =============================================================================

_current_session_name = "default"


def _get_output_dir() -> str:
    """출력 디렉토리 경로: output/{session_name}/ip_search/{date}/"""
    return OutputPath(_current_session_name).sub("ip_search").with_date("daily").build()


# =============================================================================
# 캐시 관리
# =============================================================================


def _get_cache(session_name: str):
    """ENI 캐시 인스턴스 가져오기 (존재하면)"""
    from plugins.vpc.ip_search.private import ENICache

    cache = ENICache(session_name=session_name)
    if cache.is_valid():
        return cache
    return None


def _collect_enis(session, account_id: str, account_name: str, region: str) -> list:
    """단일 계정/리전의 ENI 수집 (병렬 실행용)"""
    from plugins.vpc.ip_search.private import fetch_enis_from_account

    interfaces = fetch_enis_from_account(
        session=session,
        account_id=account_id,
        account_name=account_name,
        regions=[region],
    )
    return interfaces if interfaces else []


def _build_cache(ctx, session_name: str, force_refresh: bool = False):
    """ENI 캐시 생성/새로고침"""
    from plugins.vpc.ip_search.private import ENICache

    cache = ENICache(session_name=session_name)

    if force_refresh:
        console.print("\n[cyan]ENI 캐시를 새로고침 중...[/cyan]")
        cache.clear()
    else:
        console.print("\n[cyan]ENI 데이터를 수집 중...[/cyan]")

    with console.status("[bold green]모든 리전에서 ENI 수집 중..."):
        result = parallel_collect(ctx, _collect_enis, max_workers=20, service="ec2")

    total_count = 0
    for interfaces in result.get_data():
        if interfaces:
            cache.update(interfaces)
            total_count += len(interfaces)

    cache.save()
    console.print(f"[green]✓ {total_count}개 ENI 캐시 완료[/green]")

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")

    return cache


def _show_cache_menu(ctx, session_name: str):
    """통합 캐시 관리 메뉴"""
    from plugins.vpc.ip_search.private import ENICache
    from plugins.vpc.ip_search.public import (
        clear_public_cache,
        get_public_cache_status,
        refresh_public_cache,
    )

    eni_cache = ENICache(session_name=session_name)

    console.print("\n[bold cyan]━━━ 캐시 관리 ━━━[/bold cyan]")
    console.print("[dim]• Private: 선택한 계정/리전의 ENI (AWS 인증 필요)[/dim]")
    console.print("[dim]• Public: 클라우드 IP 대역 (인증 불필요, 공용)[/dim]")

    # Private (ENI) 캐시 상태
    console.print("\n[bold]Private (ENI)[/bold]")
    if eni_cache.is_valid():
        mtime = os.path.getmtime(eni_cache.cache_file)
        cache_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        console.print(
            f"  상태: [green]유효[/green] | ENI: [cyan]{eni_cache.count()}[/cyan]개 | 생성: [dim]{cache_time}[/dim]"
        )
    else:
        console.print("  상태: [yellow]없음 또는 만료[/yellow]")

    # Public (클라우드 대역) 캐시 상태
    console.print("\n[bold]Public (클라우드 대역)[/bold]")
    pub_status = get_public_cache_status()
    if pub_status["total_files"] > 0:
        for provider, info in pub_status["providers"].items():
            if info.get("cached"):
                valid = "[green]✓[/green]" if info.get("valid") else "[yellow]만료[/yellow]"
                console.print(f"  {provider}: {valid} {info.get('count', 0)}개 ({info.get('time', '')})")
    else:
        console.print("  상태: [yellow]캐시 없음[/yellow]")

    console.print()
    console.print("  [cyan](1)[/cyan] Private 캐시 새로고침 (선택한 계정/리전)")
    console.print("  [cyan](2)[/cyan] Public 캐시 새로고침 (AWS/GCP/Azure/Oracle)")
    console.print("  [cyan](3)[/cyan] Private 캐시 삭제")
    console.print("  [cyan](4)[/cyan] Public 캐시 삭제")
    console.print("  [cyan](5)[/cyan] 전체 캐시 삭제")
    console.print("  [dim](0)[/dim] 돌아가기")

    choice = Prompt.ask("\n선택", choices=["1", "2", "3", "4", "5", "0"], default="0")

    if choice == "1":
        _build_cache(ctx, session_name, force_refresh=True)
    elif choice == "2":
        with console.status("[bold yellow]Public IP 범위 다운로드 중 (AWS, GCP, Azure, Oracle)..."):
            result = refresh_public_cache()

        if result["success"]:
            counts = ", ".join(f"{p}: {result['counts'].get(p, 0)}개" for p in result["success"])
            console.print("[green]✓ Public 캐시 새로고침 완료[/green]")
            console.print(f"  [dim]{counts}[/dim]")
        if result["failed"]:
            console.print(f"[yellow]  실패: {', '.join(result['failed'])}[/yellow]")
    elif choice == "3":
        eni_cache.clear()
        console.print("[green]✓ Private 캐시가 삭제되었습니다.[/green]")
    elif choice == "4":
        count = clear_public_cache()
        console.print(f"[green]✓ Public 캐시 {count}개 삭제 완료[/green]")
    elif choice == "5":
        eni_cache.clear()
        count = clear_public_cache()
        console.print(f"[green]✓ 전체 캐시 삭제 완료 (Private + Public {count}개)[/green]")


# =============================================================================
# 통합 검색
# =============================================================================


def _search_all(queries: list[str], cache, public_mode: bool = True) -> dict:
    """
    Public + Private 통합 검색

    Args:
        queries: 검색 쿼리 목록
        cache: ENI 캐시
        public_mode: Public 검색 활성화 여부

    Returns:
        {"public": [...], "private": [...]}
    """
    from plugins.vpc.ip_search.private import QueryType, parse_query, search_by_query
    from plugins.vpc.ip_search.public import search_public_ip

    results: dict[str, list[Any]] = {"public": [], "private": []}

    # Public 검색 (단일 IP만, public_mode가 True일 때)
    if public_mode:
        ip_queries = []
        for query in queries:
            query_type, value = parse_query(query)
            if query_type == QueryType.IP and value:
                ip_queries.append(value)

        if ip_queries:
            with console.status("[bold yellow]Public IP 범위 검색 중..."):
                results["public"] = search_public_ip(ip_queries)

    # Private 검색 (캐시가 있으면)
    if cache and cache.is_valid():
        with console.status("[bold green]Private ENI 검색 중..."):
            results["private"] = search_by_query(queries, cache)

    return results


def _search_public_filter(provider: str, filter_type: str, filter_value: str) -> list:
    """
    Public IP 범위를 region/service로 필터링 검색

    Args:
        provider: 클라우드 제공자 (aws, gcp, azure, oracle)
        filter_type: 필터 타입 (region, service)
        filter_value: 필터 값

    Returns:
        매칭되는 IP 범위 목록
    """
    from plugins.vpc.ip_search.public import search_by_filter

    with console.status(f"[bold yellow]{provider.upper()} {filter_type} 검색 중..."):
        if filter_type == "region":
            return search_by_filter(provider=provider, region=filter_value)
        elif filter_type == "service":
            return search_by_filter(provider=provider, service=filter_value)
        else:
            return search_by_filter(provider=provider, region=filter_value, service=filter_value)


def _show_public_filter_menu():
    """Public IP 범위 필터 검색 메뉴"""
    from plugins.vpc.ip_search.public import get_available_filters

    console.print("\n[bold yellow]━━━ Public IP 범위 검색 ━━━[/bold yellow]")
    console.print("[dim]클라우드 제공자의 IP 범위를 region/service로 검색합니다.[/dim]\n")

    # 제공자 선택
    console.print("  (1) AWS")
    console.print("  (2) GCP")
    console.print("  (3) Azure")
    console.print("  (4) Oracle")
    console.print("  (0) 돌아가기")

    provider_choice = Prompt.ask("\n제공자 선택", choices=["0", "1", "2", "3", "4"], default="1")

    if provider_choice == "0":
        return None, None

    providers = {"1": "aws", "2": "gcp", "3": "azure", "4": "oracle"}
    provider = providers[provider_choice]

    # 필터 목록 표시
    console.print(f"\n[dim]{provider.upper()} 필터 목록 로딩 중...[/dim]")
    filters = get_available_filters(provider)

    console.print(f"\n[cyan]리전 ({len(filters['regions'])}개):[/cyan]")
    for i, region in enumerate(filters["regions"][:20], 1):
        console.print(f"  {region}", end="  ")
        if i % 5 == 0:
            console.print()
    if len(filters["regions"]) > 20:
        console.print(f"  ... 외 {len(filters['regions']) - 20}개")
    console.print()

    console.print(f"\n[cyan]서비스 ({len(filters['services'])}개):[/cyan]")
    for i, service in enumerate(filters["services"][:15], 1):
        console.print(f"  {service}", end="  ")
        if i % 4 == 0:
            console.print()
    if len(filters["services"]) > 15:
        console.print(f"  ... 외 {len(filters['services']) - 15}개")
    console.print()

    # 필터 입력
    console.print("\n[dim]검색할 리전 또는 서비스를 입력하세요 (부분 일치)[/dim]")
    filter_value = Prompt.ask("[bold yellow]필터[/bold yellow]").strip()

    if not filter_value:
        return None, None

    return provider, filter_value


def _handle_public_filter_query(query: str, save_csv: bool):
    """
    @ 접두사 쿼리 처리

    형식:
        @                              → 메뉴 모드
        @aws                           → AWS 필터 메뉴
        @aws ap-northeast-2            → AWS 서울 리전
        @aws ec2                       → AWS EC2 서비스
        @aws ap-northeast-2 ec2        → AWS 서울 리전 + EC2 (AND)
        @aws ap-northeast-2,us-east-1  → 서울 + 버지니아 리전 (OR)
        @aws ap-northeast-2 ec2,route53 → 서울 리전 + EC2/Route53
    """
    from plugins.vpc.ip_search.public import get_available_filters, search_by_filter

    query = query[1:].strip()  # @ 제거

    # @ 만 입력한 경우 메뉴 모드
    if not query:
        provider, filter_value = _show_public_filter_menu()
        if not provider or not filter_value:
            return
        filter_tokens = [filter_value]
    else:
        # @provider filter1 filter2 ... 파싱
        if ":" in query:
            parts = query.split(":", 1)
            provider = parts[0].strip().lower()
            filter_str = parts[1].strip()
        elif " " in query:
            parts = query.split(None, 1)
            provider = parts[0].strip().lower()
            filter_str = parts[1].strip() if len(parts) > 1 else ""
        else:
            provider = query.lower()
            filter_str = ""

        # 공백으로 분리된 필터 토큰들
        filter_tokens = filter_str.split() if filter_str else []

    # 유효한 provider 확인
    valid_providers = {"aws", "gcp", "azure", "oracle"}
    if provider not in valid_providers:
        console.print(f"[red]알 수 없는 제공자: {provider}[/red]")
        console.print(f"[dim]사용 가능: {', '.join(valid_providers)}[/dim]")
        return

    # filter_tokens가 없으면 필터 목록 표시
    if not filter_tokens:
        filters = get_available_filters(provider)
        console.print(f"\n[bold yellow]━━━ {provider.upper()} IP 범위 ━━━[/bold yellow]")

        console.print(f"\n[cyan]리전 ({len(filters['regions'])}개):[/cyan]")
        for region in filters["regions"][:30]:
            console.print(f"  {region}")
        if len(filters["regions"]) > 30:
            console.print(f"  ... 외 {len(filters['regions']) - 30}개")

        console.print(f"\n[cyan]서비스 ({len(filters['services'])}개):[/cyan]")
        for service in filters["services"][:20]:
            console.print(f"  {service}")
        if len(filters["services"]) > 20:
            console.print(f"  ... 외 {len(filters['services']) - 20}개")

        console.print("\n[dim]검색 예:[/dim]")
        console.print(f"  [dim]@{provider} ap-northeast-2          리전 검색[/dim]")
        console.print(f"  [dim]@{provider} ec2                     서비스 검색[/dim]")
        console.print(f"  [dim]@{provider} ap-northeast-2 ec2      리전+서비스 (AND)[/dim]")
        console.print(f"  [dim]@{provider} ap-northeast-2,us-east-1  다중 리전 (OR)[/dim]")
        return

    # 필터 토큰을 region/service로 분류
    filters = get_available_filters(provider)
    known_regions = {r.lower(): r for r in filters["regions"]}
    known_services = {s.lower(): s for s in filters["services"]}

    region_filters = []
    service_filters = []

    for token in filter_tokens:
        # 쉼표로 분리된 다중 값 처리
        values = [v.strip() for v in token.split(",") if v.strip()]
        for val in values:
            val_lower = val.lower()
            # 정확히 일치하거나 부분 일치로 분류
            matched_region = None
            matched_service = None

            # 정확한 일치 먼저 확인
            if val_lower in known_regions:
                matched_region = val
            elif val_lower in known_services:
                matched_service = val
            else:
                # 부분 일치 확인
                for kr in known_regions:
                    if val_lower in kr or kr in val_lower:
                        matched_region = val
                        break
                if not matched_region:
                    for ks in known_services:
                        if val_lower in ks or ks in val_lower:
                            matched_service = val
                            break

            if matched_region:
                region_filters.append(val)
            elif matched_service:
                service_filters.append(val)
            else:
                # 분류 실패 시 둘 다 시도
                region_filters.append(val)
                service_filters.append(val)

    # 검색 실행
    filter_desc = []
    if region_filters:
        filter_desc.append(f"리전={','.join(region_filters)}")
    if service_filters:
        filter_desc.append(f"서비스={','.join(service_filters)}")
    console.print(f"[dim]검색: {provider.upper()} → {' + '.join(filter_desc) if filter_desc else 'all'}[/dim]")

    all_results = []

    with console.status(f"[bold yellow]{provider.upper()} IP 범위 검색 중..."):
        # region OR 조건으로 수집
        region_results = []
        if region_filters:
            for rf in region_filters:
                region_results.extend(search_by_filter(provider=provider, region=rf))
        else:
            # 리전 필터가 없으면 전체
            region_results = search_by_filter(provider=provider)

        # service 필터 적용 (AND)
        if service_filters and region_results:
            for result in region_results:
                for sf in service_filters:
                    if sf.lower() in (result.service or "").lower():
                        all_results.append(result)
                        break
        elif not service_filters:
            all_results = region_results
        else:
            # region_results가 없고 service만 있는 경우
            for sf in service_filters:
                all_results.extend(search_by_filter(provider=provider, service=sf))

    # 중복 제거
    seen = set()
    unique_results = []
    for r in all_results:
        key = (r.ip_prefix, r.service, r.region)
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    if not unique_results:
        console.print("[yellow]해당 조건에 맞는 IP 범위가 없습니다.[/yellow]")
        return

    # 결과 표시
    console.print(f"\n[bold yellow]━━━ {provider.upper()} IP 범위 ({len(unique_results)}개) ━━━[/bold yellow]")
    _display_public_table(unique_results)
    console.print(f"\n[dim]{len(unique_results)}개 IP 범위[/dim]")

    # CSV 저장
    if save_csv:
        filepath = _save_public_csv(unique_results)
        if filepath:
            console.print(f"[green]CSV: {filepath}[/green]")


# =============================================================================
# 상세 조회 (API 기반 리소스 정보 조회)
# =============================================================================


def _enrich_with_detail(ctx, private_results: list, cache, session_name: str) -> list:
    """
    Private 검색 결과에 API 기반 상세 리소스 정보 추가

    Args:
        ctx: 실행 컨텍스트
        private_results: Private 검색 결과 목록
        cache: ENI 캐시
        session_name: 세션 이름

    Returns:
        enriched results (mapped_resource 필드 업데이트됨)
    """
    if not private_results or not cache:
        return private_results

    from plugins.vpc.ip_search.detail import get_detailed_resource_info

    # 컨텍스트에서 세션 가져오기
    session = getattr(ctx, "session", None)
    if not session:
        return private_results

    enriched = []
    for result in private_results:
        try:
            # 캐시에서 원본 ENI 데이터 가져오기
            eni_data_list = cache.get_by_ip(result.ip_address)
            if eni_data_list:
                eni_data = eni_data_list[0]
                eni_data["Region"] = result.region

                # API 호출로 상세 정보 가져오기
                detailed_info = get_detailed_resource_info(session, eni_data)
                if detailed_info:
                    # 새 결과 객체 생성 (원본 수정 방지)
                    from plugins.vpc.ip_search.private import PrivateIPResult

                    enriched_result = PrivateIPResult(
                        ip_address=result.ip_address,
                        account_id=result.account_id,
                        account_name=result.account_name,
                        region=result.region,
                        eni_id=result.eni_id,
                        vpc_id=result.vpc_id,
                        subnet_id=result.subnet_id,
                        availability_zone=result.availability_zone,
                        private_ip=result.private_ip,
                        public_ip=result.public_ip,
                        interface_type=result.interface_type,
                        status=result.status,
                        description=result.description,
                        security_groups=result.security_groups,
                        name=result.name,
                        is_managed=result.is_managed,
                        managed_by=result.managed_by,
                        mapped_resource=detailed_info,  # API에서 가져온 상세 정보
                    )
                    enriched.append(enriched_result)
                    continue
        except Exception:
            pass

        enriched.append(result)

    return enriched


# =============================================================================
# 결과 출력
# =============================================================================


def _display_results(results: dict, save_csv: bool = False) -> None:
    """통합 검색 결과 출력"""
    public_results = results.get("public", [])
    private_results = results.get("private", [])

    has_public = bool(public_results)
    has_private = bool(private_results)

    if not has_public and not has_private:
        console.print("\n[yellow]검색 결과가 없습니다.[/yellow]")
        return

    # Public 결과
    if has_public:
        console.print("\n[bold cyan]━━━ Public (클라우드 대역) ━━━[/bold cyan]")
        _display_public_table(public_results)

    # Private 결과
    if has_private:
        console.print("\n[bold cyan]━━━ Private (AWS ENI) ━━━[/bold cyan]")
        _display_private_table(private_results)

    # 요약
    console.print()
    if has_public:
        matched = [r for r in public_results if r.provider != "Unknown"]
        unknown = len(public_results) - len(matched)
        console.print(f"[dim]Public: {len(matched)}개 매칭" + (f", {unknown}개 Unknown" if unknown else "") + "[/dim]")

    if has_private:
        console.print(f"[dim]Private: {len(private_results)}개 ENI[/dim]")

    # CSV 저장
    if save_csv:
        if has_public:
            filepath = _save_public_csv(public_results)
            if filepath:
                console.print(f"[green]Public CSV: {filepath}[/green]")
        if has_private:
            filepath = _save_private_csv(private_results)
            if filepath:
                console.print(f"[green]Private CSV: {filepath}[/green]")


def _display_public_table(results):
    """Public 검색 결과 테이블"""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("IP 주소", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("서비스", style="blue")
    table.add_column("IP 범위", style="yellow")
    table.add_column("리전", style="white")

    for r in results:
        provider_style = {
            "AWS": "bold yellow",
            "GCP": "bold blue",
            "Azure": "bold cyan",
            "Oracle": "bold red",
            "Unknown": "dim",
        }.get(r.provider, "white")

        table.add_row(
            r.ip_address,
            f"[{provider_style}]{r.provider}[/{provider_style}]",
            r.service or "-",
            r.ip_prefix or "-",
            r.region or "-",
        )

    console.print(table)


def _display_private_table(results):
    """Private 검색 결과 테이블 (상세 모드)"""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("IP 주소", style="cyan")
    table.add_column("계정", style="green")
    table.add_column("리전", style="blue")
    table.add_column("리소스", style="magenta")
    table.add_column("ENI ID", style="yellow")
    table.add_column("VPC", style="white")
    table.add_column("Public IP", style="cyan")

    for r in results:
        table.add_row(
            r.ip_address,
            r.account_name,
            r.region,
            r.mapped_resource or r.interface_type or "-",
            r.eni_id,
            r.vpc_id,
            r.public_ip or "-",
        )

    console.print(table)


# =============================================================================
# CSV 저장
# =============================================================================


def _save_public_csv(results) -> str:
    """Public 결과 CSV 저장"""
    if not results:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"public_ip_{timestamp}.csv"
    filepath = os.path.join(_get_output_dir(), filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["IP 주소", "제공자", "서비스", "IP 범위", "리전", "추가정보"])

        for r in results:
            extra = ", ".join(f"{k}={v}" for k, v in r.extra.items()) if r.extra else ""
            writer.writerow([r.ip_address, r.provider, r.service, r.ip_prefix, r.region, extra])

    return filepath


def _save_private_csv(results) -> str:
    """Private 결과 CSV 저장"""
    if not results:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"private_ip_{timestamp}.csv"
    filepath = os.path.join(_get_output_dir(), filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "IP 주소",
                "계정 ID",
                "계정명",
                "리전",
                "ENI ID",
                "VPC ID",
                "Subnet ID",
                "Private IP",
                "Public IP",
                "인터페이스 타입",
                "상태",
                "설명",
                "Security Groups",
                "이름",
                "관리형",
                "관리자",
                "리소스",
            ]
        )

        for r in results:
            writer.writerow(
                [
                    r.ip_address,
                    r.account_id,
                    r.account_name,
                    r.region,
                    r.eni_id,
                    r.vpc_id,
                    r.subnet_id,
                    r.private_ip,
                    r.public_ip,
                    r.interface_type,
                    r.status,
                    r.description,
                    ", ".join(r.security_groups),
                    r.name,
                    "Yes" if r.is_managed else "No",
                    r.managed_by,
                    r.mapped_resource,
                ]
            )

    return filepath


# =============================================================================
# 메인 UI
# =============================================================================


def _show_help():
    """검색 도움말"""
    help_text = """
[bold cyan]━━━ 검색 쿼리 형식 ━━━[/bold cyan]

  [yellow]IP / CIDR[/yellow]
    10.0.1.50          단일 Private IP → Public 대역 + ENI 캐시 검색
    13.124.199.1       단일 Public IP  → AWS/GCP/Azure/Oracle 대역 확인
    10.0.0.0/24        CIDR 범위       → ENI 캐시에서 범위 내 IP 검색
    192.168.1.1, 10.0.1.50   쉼표로 여러 IP 동시 검색

  [yellow]AWS 리소스 ID[/yellow] (ENI 캐시 검색)
    eni-04d867ef       ENI ID → 해당 ENI 정보
    vpc-0a6d4f22       VPC ID → VPC 내 모든 ENI
    subnet-06eb447f    Subnet ID → 서브넷 내 모든 ENI
    i-0abc123def       Instance ID → EC2에 연결된 ENI
    sg-0abc123def      Security Group → 해당 SG 사용하는 ENI

  [yellow]텍스트 검색[/yellow] (ENI 캐시 검색)
    my-lambda          Description, Name 필드에서 검색
    RDS                리소스 타입명으로 검색
    prod               태그나 설명에 포함된 키워드

[bold cyan]━━━ 명령어 (토글) ━━━[/bold cyan]

  [yellow]p[/yellow]        Public 검색 ON/OFF (기본: ON) - 클라우드 대역 확인
  [magenta]d[/magenta]        Detail 모드 ON/OFF - API로 리소스 상세 정보 조회 (느림)
  [green]c[/green]        CSV 저장 ON/OFF

[bold cyan]━━━ Public IP 범위 검색 ━━━[/bold cyan]

  [yellow]@aws[/yellow]                        AWS 리전/서비스 목록
  [yellow]@aws ap-northeast-2[/yellow]         서울 리전
  [yellow]@aws ec2[/yellow]                    EC2 서비스
  [yellow]@aws ap-northeast-2 ec2[/yellow]     서울 + EC2 (AND)
  [yellow]@aws ap-northeast-2,us-east-1[/yellow]  서울 + 버지니아 (OR)
  [yellow]@aws ap-northeast-2,us-east-1 ec2,route53[/yellow]  다중 조합

[bold cyan]━━━ 기타 명령어 ━━━[/bold cyan]

  [green]cache[/green]    캐시 관리 (Private ENI + Public IP 범위)
  [green]h[/green]        이 도움말 표시
  [green]q[/green]        검색 종료
"""
    console.print(Panel(help_text, title="IP 검색 도움말", border_style="cyan"))


def _format_cache_status(cache) -> str:
    """캐시 상태를 포맷팅"""
    if not cache or not cache.is_valid():
        return "[yellow]없음[/yellow] - Private 검색 제한 ([green]cache[/green]로 생성)"

    stats = cache.get_stats()
    total = stats["total"]
    regions = stats["regions"]
    accounts = stats["accounts"]

    # 리전 목록 (최대 5개, 나머지는 +N개)
    region_list = sorted(regions.keys())
    if len(region_list) <= 5:
        region_str = ", ".join(region_list)
    else:
        region_str = ", ".join(region_list[:5]) + f" 외 {len(region_list) - 5}개"

    # 계정 목록 (최대 3개)
    account_names = list(accounts.values())
    if len(account_names) <= 3:
        account_str = ", ".join(account_names)
    else:
        account_str = ", ".join(account_names[:3]) + f" 외 {len(account_names) - 3}개"

    # 캐시 시간
    import os

    mtime = os.path.getmtime(cache.cache_file)
    cache_time = datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")

    return f"[green]{total}개[/green] ENI | 계정: {account_str} | 리전: {region_str} | 생성: {cache_time}"


def run(ctx):
    """
    IP 검색 도구 실행

    Args:
        ctx: 실행 컨텍스트 (ExecutionContext 객체)
    """
    global _current_session_name

    # 세션 이름 (프로파일/리전은 flow에서 이미 선택됨)
    session_name = getattr(ctx, "profile_name", None) or "default"
    _current_session_name = session_name

    # 캐시 로드 (있으면)
    cache = _get_cache(session_name)

    # 옵션 상태
    save_csv = False
    public_mode = True  # Public 검색 (클라우드 대역)
    detail_mode = False  # 상세 모드 (API 호출로 리소스 정보 조회)

    # 시작 메시지
    console.print(f"\n[bold cyan]━━━ IP 검색 ({session_name}) ━━━[/bold cyan]")

    # 캐시 상태에 따른 안내
    if not cache or not cache.is_valid():
        console.print("\n[yellow]Private 검색용 ENI 캐시가 없습니다.[/yellow]")
        console.print("  [dim]• Private 검색: 선택한 계정/리전의 ENI 정보 검색 (cache로 생성)[/dim]")
        console.print("  [dim]• Public 검색: 클라우드 IP 대역 검색 (인증 불필요, 바로 사용 가능)[/dim]")
        console.print("  [dim]  → @aws, @gcp, @azure, @oracle 명령으로 Public IP 범위 검색[/dim]")
    else:
        console.print(f"  [dim]ENI 캐시:[/dim] {_format_cache_status(cache)}")

    console.print(
        "\n  [dim]토글:[/dim] [yellow]p[/yellow]=Public  [magenta]d[/magenta]=Detail  [green]c[/green]=CSV  |  [dim]@aws:리전  cache  h=도움말  q=종료[/dim]"
    )

    # 검색 루프
    while True:
        # 옵션 상태 표시
        options = []
        if public_mode:
            options.append("[yellow]Public[/yellow]")
        if detail_mode:
            options.append("[magenta]Detail[/magenta]")
        if save_csv:
            options.append("[green]CSV[/green]")

        if options:
            console.print(f"\n[dim]모드: {' | '.join(options)}[/dim]")

        query_input = Prompt.ask("\n[bold cyan]검색[/bold cyan]").strip()

        # 명령어 처리
        if not query_input or query_input in ("0", "q"):
            console.print("\n[dim]검색을 종료합니다.[/dim]")
            break

        if query_input.lower() in ("c", "csv"):
            save_csv = not save_csv
            status = "[green]ON[/green]" if save_csv else "[dim]OFF[/dim]"
            console.print(f"[cyan]CSV 저장: {status}[/cyan]")
            continue

        if query_input.lower() in ("p", "public"):
            public_mode = not public_mode
            status = "[green]ON[/green]" if public_mode else "[dim]OFF[/dim]"
            console.print(f"[yellow]Public 검색: {status}[/yellow]")
            continue

        if query_input.lower() in ("d", "detail"):
            detail_mode = not detail_mode
            status = "[green]ON[/green]" if detail_mode else "[dim]OFF[/dim]"
            console.print(f"[magenta]상세 모드: {status}[/magenta]")
            if detail_mode:
                console.print("[dim]  API를 호출하여 리소스 상세 정보를 조회합니다 (느림)[/dim]")
            continue

        if query_input.lower() == "cache":
            _show_cache_menu(ctx, session_name)
            cache = _get_cache(session_name)
            continue

        if query_input.lower() in ("h", "help"):
            _show_help()
            continue

        # Public IP 범위 필터 검색 (@provider:filter 형식)
        if query_input.startswith("@"):
            _handle_public_filter_query(query_input, save_csv)
            continue

        # 쿼리 파싱
        queries = [q.strip() for q in query_input.split(",") if q.strip()]
        if not queries:
            continue

        console.print(f"[dim]검색: {', '.join(queries)}[/dim]")

        # 통합 검색
        results = _search_all(queries, cache, public_mode)

        # 상세 모드: API로 리소스 정보 enrichment
        if detail_mode and results.get("private"):
            with console.status("[bold magenta]리소스 상세 정보 조회 중..."):
                results["private"] = _enrich_with_detail(ctx, results["private"], cache, session_name)

        # 결과 출력 및 저장
        _display_results(results, save_csv=save_csv)

    console.print("\n[green]✓ 검색 완료[/green]")
