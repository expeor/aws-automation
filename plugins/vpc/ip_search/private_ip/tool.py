"""
plugins/vpc/ip_search/private_ip/tool.py - Private IP Search Tool

Search AWS ENI cache for private IP addresses.
Supports multi-profile/multi-account cache management.
"""

import ipaddress
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from cli.i18n import get_lang

from .cache import (
    CacheInfo,
    ENICache,
    MultiCacheSearch,
    PrivateIPResult,
    build_cache,
    delete_all_caches,
    delete_cache,
    list_available_caches,
)
from .export import copy_to_clipboard, copy_to_clipboard_simple, export_csv, export_excel
from .i18n import t

console = Console()


# =============================================================================
# Cache Selection UI
# =============================================================================


def _display_cache_table(caches: list[CacheInfo], selected: set[int]) -> None:
    """Display available caches in a table."""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("", width=3)  # Selection checkbox
    table.add_column(t("cache_profile"), style="cyan")
    table.add_column(t("cache_account"), style="green")
    table.add_column(t("cache_eni_count"), style="yellow", justify="right")
    table.add_column(t("cache_regions"), style="blue")
    table.add_column(t("cache_created"), style="dim")
    table.add_column(t("cache_status"), style="white")

    for idx, cache in enumerate(caches):
        checkbox = "[green]v[/green]" if idx in selected else "[ ]"
        status = f"[green]{t('cache_valid')}[/green]" if cache.is_valid else f"[yellow]{t('cache_expired')}[/yellow]"
        regions_str = ", ".join(cache.regions[:3])
        if len(cache.regions) > 3:
            regions_str += f" +{len(cache.regions) - 3}"

        table.add_row(
            str(idx + 1),
            checkbox,
            cache.profile_name,
            cache.account_id,
            str(cache.eni_count),
            regions_str,
            cache.created_at.strftime("%Y-%m-%d %H:%M"),
            status,
        )

    console.print(table)


def _select_caches(caches: list[CacheInfo]) -> list[CacheInfo]:
    """Interactive cache selection UI."""
    if not caches:
        console.print(f"\n[yellow]{t('cache_none_available')}[/yellow]")
        return []

    selected: set[int] = set(range(len(caches)))  # Select all by default

    while True:
        console.print(f"\n[bold cyan]{t('cache_available')}[/bold cyan]")
        _display_cache_table(caches, selected)

        console.print(f"\n  [dim]번호 입력: 선택/해제 | a={t('cache_toggle_all')} | Enter={t('cache_confirm_selection')} | 0={t('menu_back')}[/dim]")
        choice = Prompt.ask(t("prompt_select"), default="").strip()

        if choice == "":
            # Confirm selection
            if not selected:
                console.print(f"[yellow]{t('cache_none_available')}[/yellow]")
                continue
            break
        elif choice == "0":
            return []
        elif choice.lower() == "a":
            # Toggle all
            if len(selected) == len(caches):
                selected.clear()
            else:
                selected = set(range(len(caches)))
        else:
            # Toggle specific cache
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(caches):
                    if idx in selected:
                        selected.discard(idx)
                    else:
                        selected.add(idx)
            except ValueError:
                pass

    return [caches[i] for i in sorted(selected)]


def _load_selected_caches(cache_infos: list[CacheInfo]) -> list[ENICache]:
    """Load ENICache instances for selected caches."""
    caches = []
    for info in cache_infos:
        cache = ENICache(profile_name=info.profile_name, account_id=info.account_id)
        if cache.count() > 0:
            caches.append(cache)
    return caches


# =============================================================================
# Cache Creation UI
# =============================================================================


def _create_cache(ctx) -> ENICache | None:
    """Create a new cache using existing auth flow."""
    from cli.flow.context import ExecutionContext
    from cli.flow.steps import ProfileStep, RegionStep
    from core.auth.session import get_session

    # Create a new context for auth flow
    auth_ctx = ExecutionContext()

    try:
        # Step 1: Profile selection (reuse existing flow)
        console.print()
        auth_ctx = ProfileStep().execute(auth_ctx)

        if not auth_ctx.profile_name:
            return None

        # Step 2: Region selection (reuse existing flow)
        auth_ctx = RegionStep().execute(auth_ctx)

        if not auth_ctx.regions:
            return None

        profile_name = auth_ctx.profile_name
        regions = auth_ctx.regions

        # Create session
        session = get_session(profile_name, regions[0])

        # Get account info
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]

        console.print(f"\n[cyan]{t('cache_creating_for', profile=profile_name, account=account_id)}[/cyan]")
        console.print(f"  [dim]Regions: {', '.join(regions)}[/dim]")

        # Build cache with progress
        with console.status(f"[bold yellow]{t('cache_creating')}[/bold yellow]"):
            cache = build_cache(
                profile_name=profile_name,
                account_id=account_id,
                account_name=account_id,
                session=session,
                regions=regions,
            )
            console.print(f"[green]{t('cache_created_success', count=cache.count())}[/green]")
            return cache

    except KeyboardInterrupt:
        console.print(f"\n[dim]{t('exit_message')}[/dim]")
        return None
    except Exception as e:
        console.print(f"[red]{t('cache_create_failed')}: {e}[/red]")
        return None


def _delete_caches_menu() -> None:
    """Delete cache menu."""
    caches = list_available_caches()
    if not caches:
        console.print(f"\n[yellow]{t('cache_none_available')}[/yellow]")
        return

    selected = _select_caches(caches)
    if not selected:
        return

    console.print(f"\n[yellow]{t('cache_delete_confirm')}[/yellow]")
    for cache in selected:
        console.print(f"  - {cache.profile_name} / {cache.account_id}")

    if Confirm.ask(t("prompt_yes_no"), default=False):
        count = 0
        for cache in selected:
            if delete_cache(cache.profile_name, cache.account_id):
                count += 1
        console.print(f"[green]{t('cache_deleted', count=count)}[/green]")


# =============================================================================
# Search Functions
# =============================================================================


def _parse_query(query: str) -> tuple[str, str]:
    """Parse query to determine type and value."""
    query = query.strip()

    if not query:
        return "empty", ""

    # VPC ID
    if query.startswith("vpc-"):
        return "vpc", query

    # ENI ID
    if query.startswith("eni-"):
        return "eni", query

    # Subnet ID
    if query.startswith("subnet-"):
        return "subnet", query

    # CIDR
    if "/" in query:
        try:
            ipaddress.ip_network(query, strict=False)
            return "cidr", query
        except ValueError:
            pass

    # IP
    try:
        ipaddress.ip_address(query)
        return "ip", query
    except ValueError:
        pass

    # Text search
    return "text", query


def _search(
    searcher: MultiCacheSearch,
    query: str,
) -> list[PrivateIPResult]:
    """Execute search based on query type."""
    query_type, value = _parse_query(query)

    if query_type == "empty":
        return []
    elif query_type == "ip":
        return searcher.search_ip(value)
    elif query_type == "cidr":
        return searcher.search_cidr(value)
    elif query_type == "vpc":
        return searcher.search_vpc(value)
    elif query_type == "text":
        return searcher.search_text(value)
    else:
        # For eni, subnet - fall back to text search
        return searcher.search_text(value)


def _enrich_with_details(
    results: list[PrivateIPResult],
    caches: list[ENICache],
    session,
) -> list[PrivateIPResult]:
    """Enrich results with detailed resource info via API calls."""
    from plugins.vpc.ip_search.detail import enrich_resources_parallel

    if not results or not session:
        return results

    # Group results by profile/account to match with caches
    cache_map = {(c.profile_name, c.account_id): c for c in caches}

    # Collect ENIs to enrich
    enis_to_enrich = []
    result_to_eni_map: dict[int, dict] = {}

    for idx, result in enumerate(results):
        cache = cache_map.get((result.profile_name, result.account_id))
        if cache:
            eni_list = cache.get_by_ip(result.ip_address)
            if eni_list:
                eni_data = eni_list[0]
                eni_data["Region"] = result.region
                enis_to_enrich.append(eni_data)
                result_to_eni_map[idx] = eni_data

    if not enis_to_enrich:
        return results

    # Enrich in parallel
    enriched_map = enrich_resources_parallel(enis_to_enrich, session)

    # Update results
    enriched_results = []
    for idx, result in enumerate(results):
        eni_data = result_to_eni_map.get(idx)
        if eni_data:
            eni_id = eni_data.get("NetworkInterfaceId", "")
            detailed_info = enriched_map.get(eni_id)
            if detailed_info:
                result = PrivateIPResult(
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
                    mapped_resource=detailed_info,
                    profile_name=result.profile_name,
                )
        enriched_results.append(result)

    return enriched_results


# =============================================================================
# Display Functions
# =============================================================================


def _display_results_table(results: list[PrivateIPResult]) -> None:
    """Display search results in a table."""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column(t("header_ip"), style="cyan")
    table.add_column(t("header_account"), style="green")
    table.add_column(t("header_region"), style="blue")
    table.add_column(t("header_resource"), style="magenta")
    table.add_column(t("header_eni_id"), style="yellow")
    table.add_column(t("header_vpc_id"), style="white")
    table.add_column(t("header_public_ip"), style="cyan")

    for r in results:
        table.add_row(
            r.ip_address,
            r.account_name or r.account_id,
            r.region,
            r.mapped_resource or r.interface_type or "-",
            r.eni_id,
            r.vpc_id,
            r.public_ip or "-",
        )

    console.print(table)


def _show_export_menu(results: list[PrivateIPResult], session_name: str) -> bool:
    """Show export options menu. Returns True to continue, False to exit."""
    lang = get_lang()

    console.print(f"\n[bold cyan]{t('export_title')}[/bold cyan]")
    console.print(f"  (1) {t('export_csv')}")
    console.print(f"  (2) {t('export_excel')}")
    console.print(f"  (3) {t('export_clipboard')}")
    console.print(f"  (4) {t('export_clipboard_simple')}")
    console.print(f"  (0) {t('export_continue')}")

    choice = Prompt.ask(t("prompt_select"), choices=["0", "1", "2", "3", "4"], default="0")

    if choice == "1":
        filepath = export_csv(results, session_name, lang)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
        else:
            console.print(f"[yellow]{t('export_failed')}[/yellow]")
    elif choice == "2":
        filepath = export_excel(results, session_name, lang)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
        else:
            console.print(f"[yellow]{t('export_failed')}[/yellow]")
    elif choice == "3":
        if copy_to_clipboard(results, lang):
            console.print(f"[green]{t('export_copied')}[/green]")
        else:
            console.print(f"[yellow]{t('export_failed')}[/yellow]")
    elif choice == "4":
        if copy_to_clipboard_simple(results, lang):
            console.print(f"[green]{t('export_copied')}[/green]")
        else:
            console.print(f"[yellow]{t('export_failed')}[/yellow]")

    return True


# =============================================================================
# Search Loop
# =============================================================================


def _run_search_loop(
    ctx,
    caches: list[ENICache],
    session_name: str,
) -> None:
    """Main search loop."""
    from core.auth.session import get_session

    searcher = MultiCacheSearch(caches)
    detail_mode = False

    # Get session for detail mode (lazy - only create when needed)
    profile_name = getattr(ctx, "profile_name", None) or "default"
    regions = getattr(ctx, "regions", None) or ["ap-northeast-2"]
    region = regions[0] if isinstance(regions, list) else regions
    session = None  # Will be created when detail mode is first enabled

    # Show selected caches summary
    total_enis = sum(c.count() for c in caches)
    console.print(f"\n[dim]{t('cache_selected')}: {len(caches)}개 캐시, {total_enis} ENI[/dim]")

    while True:
        # Prompt with hints
        console.print(f"\n[dim]{t('search_examples')}[/dim]")
        detail_hint = f"[magenta]{t('detail_mode_on')}[/magenta]" if detail_mode else f"[dim]{t('hint_toggle_detail')}[/dim]"
        console.print(f"[dim]{detail_hint} | {t('hint_back')}[/dim]")

        query = Prompt.ask(f"[bold cyan]{t('menu_search')}[/bold cyan]").strip()

        # Handle commands
        if not query or query == "0":
            break

        if query.lower() == "d":
            detail_mode = not detail_mode
            status = t("detail_mode_on") if detail_mode else t("detail_mode_off")
            console.print(f"[magenta]{status}[/magenta]")
            if detail_mode:
                console.print(f"[dim]  {t('detail_mode_desc')}[/dim]")
                # Create session when detail mode is first enabled
                if session is None:
                    try:
                        session = get_session(profile_name, region)
                    except Exception as e:
                        console.print(f"[yellow]{t('error')}: {e}[/yellow]")
                        detail_mode = False
            continue

        # Search
        with console.status(f"[bold yellow]{t('searching')}[/bold yellow]"):
            results = _search(searcher, query)

        if not results:
            console.print(f"\n[yellow]{t('result_no_match')}[/yellow]")
            continue

        # Enrich with details if enabled
        if detail_mode and session:
            with console.status(f"[bold magenta]{t('fetching_details')}[/bold magenta]"):
                results = _enrich_with_details(results, caches, session)

        # Display results
        console.print(f"\n[bold cyan]{t('result_title')} ({t('result_count', count=len(results))})[/bold cyan]")
        _display_results_table(results)

        # Export menu
        if results:
            _show_export_menu(results, session_name)


# =============================================================================
# Main Entry Point
# =============================================================================


def run(ctx) -> None:
    """
    Private IP Search Tool entry point.

    Args:
        ctx: Execution context
    """
    from cli.ui.console import print_box_end, print_box_line, print_box_start

    session_name = getattr(ctx, "profile_name", None) or "default"

    while True:
        # Check available caches
        available_caches = list_available_caches()
        cache_count = len(available_caches)

        # Main menu with box style
        print_box_start(t('title'))
        print_box_line(f"[dim]{t('subtitle')}[/dim]")
        print_box_line()
        print_box_line(f"  1) {t('menu_search')}")
        print_box_line(f"  2) {t('menu_cache_select')} [dim]({cache_count} available)[/dim]")
        print_box_line(f"  3) {t('menu_cache_create')}")
        print_box_line(f"  4) {t('menu_cache_delete')}")
        print_box_line(f"  0) {t('menu_back')}")
        print_box_end()

        choice = console.input(f"\n> ").strip()

        if choice == "0":
            console.print(f"\n[dim]{t('exit_message')}[/dim]")
            break

        elif choice == "1":
            # Search with all valid caches by default
            valid_caches = [c for c in available_caches if c.is_valid]
            if not valid_caches:
                console.print(f"\n[yellow]{t('cache_none_available')}[/yellow]")
                continue

            loaded_caches = _load_selected_caches(valid_caches)
            if loaded_caches:
                _run_search_loop(ctx, loaded_caches, session_name)

        elif choice == "2":
            # Select caches
            selected = _select_caches(available_caches)
            if selected:
                loaded_caches = _load_selected_caches(selected)
                if loaded_caches:
                    _run_search_loop(ctx, loaded_caches, session_name)

        elif choice == "3":
            # Create cache
            _create_cache(ctx)

        elif choice == "4":
            # Delete caches
            _delete_caches_menu()

    console.print(f"[green]{t('done')}[/green]")
