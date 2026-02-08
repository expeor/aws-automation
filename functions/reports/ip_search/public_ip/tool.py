"""functions/reports/ip_search/public_ip/tool.py - Public IP Search Tool.

클라우드 프로바이더(AWS, GCP, Azure, Oracle, Cloudflare, Fastly)의 IP 대역에서
특정 IP 주소 또는 CIDR 범위의 소유자 정보를 검색합니다.
AWS 인증이 불필요하며, 공개된 IP 대역 데이터를 로컬 캐시로 관리합니다.
인라인 필터(-p, -r, -s)와 대화형 필터를 지원합니다.
"""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.shared.aws.ip_ranges import (
    ALL_PROVIDERS,
    PublicIPResult,
    clear_public_cache,
    get_available_filters,
    get_public_cache_status,
    refresh_public_cache,
    search_by_filter,
    search_public_cidr,
    search_public_ip,
)
from core.shared.io.output.builder import OutputPath

from .i18n import t

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

console = Console()


# =============================================================================
# Export Utilities
# =============================================================================


def _get_output_dir(session_name: str) -> str:
    """Get output directory path."""
    return OutputPath(session_name).sub("vpc", "public_ip_search").with_date("daily").build()


def _export_csv(results: list[PublicIPResult], session_name: str) -> str:
    """Export results to CSV file."""
    import csv

    if not results:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"public_ip_{timestamp}.csv"
    filepath = os.path.join(_get_output_dir(session_name), filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                t("header_ip"),
                t("header_provider"),
                t("header_service"),
                t("header_ip_range"),
                t("header_region"),
            ]
        )
        for r in results:
            writer.writerow([r.ip_address, r.provider, r.service, r.ip_prefix, r.region])

    return filepath


def _export_excel(results: list[PublicIPResult], session_name: str) -> str:
    """Export results to Excel file."""
    try:
        from core.shared.io.excel import ColumnDef, Workbook
    except ImportError:
        console.print("[red]shared.io.excel not available[/red]")
        return ""

    if not results:
        return ""

    columns = [
        ColumnDef(header=t("header_ip"), width=18),
        ColumnDef(header=t("header_provider"), width=12),
        ColumnDef(header=t("header_service"), width=20),
        ColumnDef(header=t("header_ip_range"), width=22),
        ColumnDef(header=t("header_region"), width=18),
    ]

    wb = Workbook()
    sheet = wb.new_sheet("Public IP Search", columns)

    for r in results:
        sheet.add_row([r.ip_address, r.provider, r.service, r.ip_prefix, r.region])

    return str(wb.save_as(_get_output_dir(session_name), "public_ip"))


def _copy_to_clipboard(results: list[PublicIPResult]) -> bool:
    """Copy results to clipboard as TSV."""
    try:
        import pyperclip
    except ImportError:
        console.print("[red]pyperclip not installed. Use: pip install pyperclip[/red]")
        return False

    if not results:
        return False

    lines = [
        f"{t('header_ip')}\t{t('header_provider')}\t{t('header_service')}\t{t('header_ip_range')}\t{t('header_region')}"
    ]
    for r in results:
        lines.append(f"{r.ip_address}\t{r.provider}\t{r.service}\t{r.ip_prefix}\t{r.region}")

    pyperclip.copy("\n".join(lines))
    return True


# =============================================================================
# Input Validation
# =============================================================================


def _validate_ip_input(ip_str: str) -> tuple[list[str], list[str], list[str]]:
    """Validate IP input and return valid IPs, CIDRs, and errors.

    Supports multiple delimiters: comma, space, newline.
    Supports both single IP addresses and CIDR notation.

    Args:
        ip_str: Raw input string

    Returns:
        Tuple of (valid_ips, valid_cidrs, error_messages)
    """
    valid_ips: list[str] = []
    valid_cidrs: list[str] = []
    errors: list[str] = []

    # Normalize delimiters: replace space and newline with comma
    normalized = ip_str.replace(" ", ",").replace("\n", ",")

    for ip in normalized.split(","):
        ip = ip.strip()
        if not ip:
            continue

        # Check if it's CIDR notation
        if "/" in ip:
            try:
                ipaddress.ip_network(ip, strict=False)
                valid_cidrs.append(ip)
            except ValueError:
                errors.append(t("validation_invalid_ip", ip=ip))
        else:
            try:
                ipaddress.ip_address(ip)
                valid_ips.append(ip)
            except ValueError:
                errors.append(t("validation_invalid_ip", ip=ip))

    return valid_ips, valid_cidrs, errors


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except ValueError:
        return False


# =============================================================================
# Help Display
# =============================================================================


def _show_help() -> None:
    """Display help information."""
    help_lines = [
        f"[bold]{t('help_input_format')}[/bold]",
        f"  {t('help_single_ip')}",
        f"  {t('help_cidr')}",
        f"  {t('help_multi_ip')}",
        "",
        f"[bold]{t('help_filter_options')}[/bold]",
        f"  {t('help_filter_provider')}",
        f"  {t('help_filter_region')}",
        f"  {t('help_filter_service')}",
        "",
        f"[bold]{t('help_interactive_filter')}[/bold]",
        f"  {t('help_filter_set')}",
        f"  {t('help_filter_clear')}",
        "",
        f"[bold cyan]{t('help_examples')}[/bold cyan]",
        f"  {t('help_example_basic')}",
        f"  {t('help_example_multi')}",
        f"  {t('help_example_cidr')}",
        f"  {t('help_example_provider')}",
        f"  {t('help_example_multi_provider')}",
        f"  {t('help_example_region')}",
        f"  {t('help_example_service')}",
        f"  {t('help_example_combined')}",
        "",
        f"[bold cyan]{t('help_interactive_example')}[/bold cyan]",
        f"  {t('help_interactive_step1')}",
        f"  {t('help_interactive_step2')}",
        "",
        f"[bold]{t('help_shortcuts')}[/bold]",
        f"  {t('help_shortcut_help')}",
        f"  {t('help_shortcut_export')}",
        f"  {t('help_shortcut_back')}",
        "",
        f"[dim]{t('help_providers')}[/dim]",
    ]
    console.print(Panel("\n".join(help_lines), title=t("help_title"), border_style="cyan"))


# =============================================================================
# Display Functions
# =============================================================================


def _display_results_table(results: list[PublicIPResult]) -> None:
    """Display search results in a table."""
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column(t("header_ip"), style="cyan")
    table.add_column(t("header_provider"), style="green")
    table.add_column(t("header_service"), style="blue")
    table.add_column(t("header_ip_range"), style="yellow")
    table.add_column(t("header_region"), style="white")

    for r in results:
        provider_style = {
            "AWS": "bold yellow",
            "GCP": "bold blue",
            "Azure": "bold cyan",
            "Oracle": "bold red",
            "Cloudflare": "bold bright_yellow",
            "Fastly": "bold magenta",
            "Unknown": "dim",
        }.get(r.provider, "white")

        table.add_row(
            r.ip_address or "-",
            f"[{provider_style}]{r.provider}[/{provider_style}]",
            r.service or "-",
            r.ip_prefix or "-",
            r.region or "-",
        )

    console.print(table)


def _show_export_menu(results: list[PublicIPResult], session_name: str) -> None:
    """Show export options as inline hint (non-blocking)."""
    console.print("\n[dim]e=export (1:csv, 2:excel, 3:clipboard) | Enter=계속[/dim]")

    choice = console.input("> ").strip().lower()

    # Handle 'e' to show full export menu
    if choice == "e":
        console.print(f"  (1) {t('export_csv')}")
        console.print(f"  (2) {t('export_excel')}")
        console.print(f"  (3) {t('export_clipboard')}")
        choice = console.input(f"  {t('prompt_select')}: ").strip().lower()

    if choice == "1" or choice == "csv":
        filepath = _export_csv(results, session_name)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
    elif choice == "2" or choice == "excel":
        filepath = _export_excel(results, session_name)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
    elif choice == "3" or choice in ("clip", "clipboard", "copy"):
        if _copy_to_clipboard(results):
            console.print(f"[green]{t('export_copied')}[/green]")


def _show_cache_status() -> None:
    """Display cache status for all providers."""
    status = get_public_cache_status()

    console.print(f"\n[bold cyan]{t('cache_status_title')}[/bold cyan]")

    for provider, info in status["providers"].items():
        if info.get("cached"):
            valid_str = (
                f"[green]{t('cache_valid')}[/green]" if info.get("valid") else f"[yellow]{t('cache_expired')}[/yellow]"
            )
            console.print(f"  {provider}: {valid_str} - {info.get('count', 0)} prefixes ({info.get('time', '')})")
        else:
            console.print(f"  {provider}: [dim]{t('cache_none')}[/dim]")


def _parse_provider_selection(selection: str) -> list[str]:
    """Parse provider selection string (e.g., '1,3,5' or '1 3 5').

    Args:
        selection: User input string

    Returns:
        List of provider names
    """
    # Normalize: replace comma and space with comma
    normalized = selection.replace(" ", ",")
    indices = [s.strip() for s in normalized.split(",") if s.strip()]

    providers = []
    for idx in indices:
        if idx.isdigit():
            i = int(idx)
            if 1 <= i <= len(ALL_PROVIDERS):
                providers.append(ALL_PROVIDERS[i - 1])
    return providers


def _show_cache_menu() -> None:
    """Show cache management menu."""
    status = get_public_cache_status()

    console.print(f"\n[bold cyan]{t('cache_status_title')}[/bold cyan]")

    # Display each provider with number
    for i, provider in enumerate(ALL_PROVIDERS, 1):
        info = status["providers"].get(provider.upper(), {})
        if info.get("cached"):
            is_valid = info.get("valid", False)
            status_icon = "[green]●[/green]" if is_valid else "[yellow]●[/yellow]"
            count = info.get("count", 0)
            cache_time = info.get("time", "")
            console.print(f"  [{i}] {status_icon} {provider.upper()}: {count} ({cache_time})")
        else:
            console.print(f"  [{i}] [dim]○[/dim] {provider.upper()}: [dim]{t('cache_none')}[/dim]")

    console.print()
    console.print(f"  (a) {t('cache_refresh_all')}")
    console.print(f"  (1-6) {t('cache_refresh_select')}")
    console.print(f"  (c) {t('cache_delete')}")
    console.print(f"  (0) {t('menu_back')}")

    choice = console.input(f"\n{t('prompt_select')}: ").strip().lower()

    if choice == "0":
        return
    elif choice == "a":
        # Refresh all providers
        with console.status(f"[bold yellow]{t('cache_refreshing')}[/bold yellow]"):
            result = refresh_public_cache()

        if result["success"]:
            counts = ", ".join(f"{p}: {result['counts'].get(p, 0)}" for p in result["success"])
            console.print(f"[green]{t('cache_refresh_done')}[/green]")
            console.print(f"  [dim]{counts}[/dim]")
        if result["failed"]:
            console.print(f"[yellow]{t('cache_refresh_failed')}: {', '.join(result['failed'])}[/yellow]")

    elif choice == "c":
        # Cache delete submenu
        console.print(f"\n  (a) {t('cache_delete_all')}")
        console.print(f"  (1-6) {t('cache_delete_select')}")
        console.print(f"  (0) {t('menu_back')}")

        del_choice = console.input(f"\n{t('prompt_select')}: ").strip().lower()

        if del_choice == "0":
            return
        elif del_choice == "a":
            count = clear_public_cache()
            console.print(f"[green]{t('cache_deleted', providers='ALL')} ({count})[/green]")
        else:
            providers = _parse_provider_selection(del_choice)
            if providers:
                count = clear_public_cache(providers)
                provider_names = ", ".join(p.upper() for p in providers)
                console.print(f"[green]{t('cache_deleted', providers=provider_names)} ({count})[/green]")

    else:
        # Selective refresh (e.g., "1" or "1,3,5")
        providers = _parse_provider_selection(choice)
        if providers:
            provider_names = ", ".join(p.upper() for p in providers)
            with console.status(
                f"[bold yellow]{t('cache_refreshing_providers', providers=provider_names)}[/bold yellow]"
            ):
                result = refresh_public_cache(providers)

            if result["success"]:
                counts = ", ".join(f"{p}: {result['counts'].get(p, 0)}" for p in result["success"])
                console.print(f"[green]{t('cache_refresh_done')}[/green]")
                console.print(f"  [dim]{counts}[/dim]")
            if result["failed"]:
                console.print(f"[yellow]{t('cache_refresh_failed')}: {', '.join(result['failed'])}[/yellow]")


# =============================================================================
# Auto Cache Management
# =============================================================================


def _ensure_cache_ready() -> bool:
    """Check cache status and auto-refresh if needed. Returns True if cache is ready."""
    status = get_public_cache_status()

    # Check if any cache exists and is valid
    has_valid_cache = any(info.get("cached") and info.get("valid") for info in status["providers"].values())

    if has_valid_cache:
        return True

    # Check if cache exists but expired
    has_expired_cache = any(info.get("cached") and not info.get("valid") for info in status["providers"].values())

    if has_expired_cache:
        console.print(f"\n[yellow]{t('cache_expired_auto')}[/yellow]")
    else:
        console.print(f"\n[yellow]{t('cache_none_auto')}[/yellow]")

    # Ask user to refresh
    if Confirm.ask(t("cache_refresh_confirm"), default=True):
        with console.status(f"[bold yellow]{t('cache_refreshing')}[/bold yellow]"):
            result = refresh_public_cache()

        if result["success"]:
            counts = ", ".join(f"{p}: {result['counts'].get(p, 0)}" for p in result["success"])
            console.print(f"[green]{t('cache_refresh_done')}[/green]")
            console.print(f"  [dim]{counts}[/dim]")
            return True
        else:
            console.print(f"[red]{t('cache_refresh_all_failed')}[/red]")
            return False
    else:
        return False


# =============================================================================
# Filter Parsing
# =============================================================================


def _parse_inline_filters(ip_input: str) -> tuple[str, dict[str, str | list[str] | None]]:
    """Parse inline filters from IP input.

    Supports:
        -p <provider>   CSP filter (can be comma-separated)
        -r <region>     Region filter
        -s <service>    Service filter

    Args:
        ip_input: Raw input string (e.g., "52.94.76.1 -p aws -r ap-northeast-2")

    Returns:
        Tuple of (ip_part, filters_dict)
        filters_dict: {"providers": [...], "region": str, "service": str}
    """
    import shlex

    filters: dict[str, str | list[str] | None] = {
        "providers": None,
        "region": None,
        "service": None,
    }

    # Try to parse using shlex for proper quoting support
    try:
        parts = shlex.split(ip_input)
    except ValueError:
        # Fall back to simple split if shlex fails
        parts = ip_input.split()

    if not parts:
        return "", filters

    ip_parts = []
    i = 0
    while i < len(parts):
        part = parts[i]

        if part == "-p" and i + 1 < len(parts):
            # Provider filter
            provider_str = parts[i + 1]
            providers = [p.strip().lower() for p in provider_str.split(",")]
            filters["providers"] = [p for p in providers if p in ALL_PROVIDERS]
            i += 2
        elif part == "-r" and i + 1 < len(parts):
            # Region filter
            filters["region"] = parts[i + 1]
            i += 2
        elif part == "-s" and i + 1 < len(parts):
            # Service filter
            filters["service"] = parts[i + 1]
            i += 2
        elif part.startswith("-"):
            # Unknown flag, skip
            i += 1
        else:
            # IP address part
            ip_parts.append(part)
            i += 1

    return " ".join(ip_parts), filters


def _get_filter_display(filters: dict[str, str | list[str] | None]) -> str:
    """Get display string for current filters."""
    parts: list[str] = []

    providers = filters.get("providers")
    if providers and isinstance(providers, list):
        parts.append(", ".join(p.upper() for p in providers))
    else:
        parts.append("ALL")

    region = filters.get("region")
    if region and isinstance(region, str):
        parts.append(region)

    service = filters.get("service")
    if service and isinstance(service, str):
        parts.append(service)

    return " / ".join(parts)


def _interactive_filter_setup() -> dict[str, str | list[str] | None]:
    """Interactive filter setup dialog.

    Returns:
        filters_dict: {"providers": [...], "region": str, "service": str}
    """
    filters: dict[str, str | list[str] | None] = {
        "providers": None,
        "region": None,
        "service": None,
    }

    console.print(f"\n[bold cyan]{t('help_interactive_filter')}[/bold cyan]")

    # CSP filter
    csp_input = Prompt.ask(f"  {t('filter_prompt_csp')}", default="").strip()
    if csp_input:
        providers = [p.strip().lower() for p in csp_input.split(",")]
        valid_providers = [p for p in providers if p in ALL_PROVIDERS]
        if valid_providers:
            filters["providers"] = valid_providers

    # Region filter
    region_input = Prompt.ask(f"  {t('filter_prompt_region')}", default="").strip()
    if region_input:
        filters["region"] = region_input

    # Service filter
    service_input = Prompt.ask(f"  {t('filter_prompt_service')}", default="").strip()
    if service_input:
        filters["service"] = service_input

    return filters


# =============================================================================
# Search Functions
# =============================================================================


def _search_by_ip(session_name: str) -> None:
    """Search IP addresses in cloud provider ranges."""
    # Auto-check and refresh cache if needed
    if not _ensure_cache_ready():
        return

    # Persistent filter state
    current_filters: dict[str, str | list[str] | None] = {
        "providers": None,
        "region": None,
        "service": None,
    }

    while True:
        # Show current filter if active
        has_filters = any(current_filters.values())
        if has_filters:
            filter_display = _get_filter_display(current_filters)
            console.print(f"\n[bold magenta]{t('filter_current', filters=filter_display)}[/bold magenta]")

        console.print(f"\n[dim]{t('prompt_enter_ip')} | ?=help | f=filter | fc=clear | 0=back[/dim]")
        ip_input = Prompt.ask(f"[bold cyan]{t('header_ip')}[/bold cyan]").strip()

        if not ip_input:
            return

        # Handle commands
        if ip_input == "?":
            _show_help()
            continue
        elif ip_input.lower() == "f":
            # Interactive filter setup
            current_filters = _interactive_filter_setup()
            if any(current_filters.values()):
                console.print(f"[green]{t('filter_set_success')}[/green]")
            continue
        elif ip_input.lower() == "fc":
            # Clear filters
            current_filters = {"providers": None, "region": None, "service": None}
            console.print(f"[green]{t('filter_cleared')}[/green]")
            continue
        elif ip_input == "0":
            return

        # Parse inline filters from input
        ip_part, inline_filters = _parse_inline_filters(ip_input)

        # Merge filters: inline filters override current filters
        effective_filters = current_filters.copy()
        if inline_filters.get("providers"):
            effective_filters["providers"] = inline_filters["providers"]
        if inline_filters.get("region"):
            effective_filters["region"] = inline_filters["region"]
        if inline_filters.get("service"):
            effective_filters["service"] = inline_filters["service"]

        # Validate input (supports both IPs and CIDRs)
        valid_ips, valid_cidrs, errors = _validate_ip_input(ip_part)

        # Show validation errors
        if errors:
            console.print(f"\n[yellow]{t('validation_errors_found', count=len(errors))}[/yellow]")
            for error in errors[:5]:  # Show max 5 errors
                console.print(f"  [dim]{error}[/dim]")
            if len(errors) > 5:
                console.print(f"  [dim]... +{len(errors) - 5}[/dim]")

        # No valid IPs or CIDRs
        if not valid_ips and not valid_cidrs:
            console.print(f"\n[red]{t('validation_no_valid_ips')}[/red]")
            continue

        # If there were some errors but also valid inputs, inform user
        total_valid = len(valid_ips) + len(valid_cidrs)
        if errors and total_valid > 0:
            console.print(f"[cyan]{t('validation_valid_ips', count=total_valid)}[/cyan]")

        # Prepare search parameters
        providers_list = effective_filters.get("providers")
        region_filter = effective_filters.get("region")
        service_filter = effective_filters.get("service")

        results: list[PublicIPResult] = []

        with console.status(f"[bold yellow]{t('searching')}[/bold yellow]"):
            # Search for individual IPs
            if valid_ips:
                ip_results = search_public_ip(
                    valid_ips,
                    providers=providers_list if isinstance(providers_list, list) else None,
                    region_filter=region_filter if isinstance(region_filter, str) else None,
                    service_filter=service_filter if isinstance(service_filter, str) else None,
                )
                results.extend(ip_results)

            # Search for CIDR ranges
            if valid_cidrs:
                cidr_results = search_public_cidr(
                    valid_cidrs,
                    providers=providers_list if isinstance(providers_list, list) else None,
                    region_filter=region_filter if isinstance(region_filter, str) else None,
                    service_filter=service_filter if isinstance(service_filter, str) else None,
                )
                results.extend(cidr_results)

        if not results:
            # Show detailed error message
            console.print(f"\n[yellow]{t('result_no_match_detail')}[/yellow]")
            # Show hints based on input
            sample = valid_ips[0] if valid_ips else (valid_cidrs[0] if valid_cidrs else "")
            if sample and "/" not in sample and _is_private_ip(sample):
                console.print(f"  [dim]{t('result_no_match_hint_private')}[/dim]")
            else:
                console.print(f"  [dim]{t('result_no_match_hint_public', ip=sample)}[/dim]")
            console.print(f"  [dim]{t('result_no_match_hint_check')}[/dim]")
            continue

        # Filter out Unknown if there are known matches for the same IP
        known_results = [r for r in results if r.provider != "Unknown"]
        known_ips = {r.ip_address for r in known_results}
        truly_unknown = [r for r in results if r.provider == "Unknown" and r.ip_address not in known_ips]

        display_results = known_results + truly_unknown

        console.print(f"\n[bold cyan]{t('result_title')} ({t('result_count', count=len(display_results))})[/bold cyan]")
        _display_results_table(display_results)

        if display_results:
            _show_export_menu(display_results, session_name)


def _search_by_filter(session_name: str) -> None:
    """Search IP ranges by region/service filter."""
    # Provider selection
    console.print(f"\n[bold cyan]{t('prompt_select_provider')}[/bold cyan]")
    console.print("  (1) AWS")
    console.print("  (2) GCP")
    console.print("  (3) Azure")
    console.print("  (4) Oracle")
    console.print("  (5) Cloudflare")
    console.print("  (6) Fastly")
    console.print(f"  (0) {t('menu_back')}")

    provider_choice = Prompt.ask(t("prompt_select"), choices=["0", "1", "2", "3", "4", "5", "6"], default="1")

    if provider_choice == "0":
        return

    providers = {"1": "aws", "2": "gcp", "3": "azure", "4": "oracle", "5": "cloudflare", "6": "fastly"}
    provider = providers[provider_choice]

    # Show available filters
    with console.status(f"[bold yellow]{t('loading')}[/bold yellow]"):
        filters = get_available_filters(provider)

    console.print(f"\n[cyan]{t('filter_regions', count=len(filters['regions']))}:[/cyan]")
    for i, region in enumerate(filters["regions"][:15], 1):
        console.print(f"  {region}", end="  ")
        if i % 5 == 0:
            console.print()
    if len(filters["regions"]) > 15:
        console.print(f"\n  [dim]{t('filter_more', count=len(filters['regions']) - 15)}[/dim]")
    console.print()

    console.print(f"\n[cyan]{t('filter_services', count=len(filters['services']))}:[/cyan]")
    for i, service in enumerate(filters["services"][:12], 1):
        console.print(f"  {service}", end="  ")
        if i % 4 == 0:
            console.print()
    if len(filters["services"]) > 12:
        console.print(f"\n  [dim]{t('filter_more', count=len(filters['services']) - 12)}[/dim]")
    console.print()

    # Get filter input - separate region and service
    console.print(f"\n[dim]{t('prompt_enter_filter')}[/dim]")
    region_filter = Prompt.ask(f"  {t('filter_prompt_region')}", default="").strip()
    service_filter = Prompt.ask(f"  {t('filter_prompt_service')}", default="").strip()

    if not region_filter and not service_filter:
        console.print(f"\n[yellow]{t('validation_no_valid_ips').replace('IP', '필터')}[/yellow]")
        return

    # Search with both filters
    with console.status(f"[bold yellow]{t('searching')}[/bold yellow]"):
        results = search_by_filter(
            provider=provider,
            region=region_filter if region_filter else None,
            service=service_filter if service_filter else None,
        )

    filter_desc = []
    if region_filter:
        filter_desc.append(f"region={region_filter}")
    if service_filter:
        filter_desc.append(f"service={service_filter}")
    filter_str = ", ".join(filter_desc)

    if not results:
        console.print(f"\n[yellow]{t('result_no_match_detail')}[/yellow]")
        console.print(f"  [dim]• {provider.upper()}: {filter_str} 필터와 일치하는 IP 범위 없음[/dim]")
        return

    console.print(f"\n[bold cyan]{t('result_title')} ({t('result_count', count=len(results))})[/bold cyan]")
    _display_results_table(results[:100])  # Limit display to 100

    if len(results) > 100:
        console.print(f"[dim]... {t('filter_more', count=len(results) - 100)}[/dim]")

    if results:
        _show_export_menu(results, session_name)


# =============================================================================
# Main Entry Point
# =============================================================================


def run(ctx: ExecutionContext) -> None:
    """
    Public IP Search Tool entry point.

    Args:
        ctx: Execution context
    """
    from core.cli.ui.console import print_box_end, print_box_line, print_box_start

    session_name = getattr(ctx, "profile_name", None) or "default"

    while True:
        # Main menu with box style
        print_box_start(t("title"))
        print_box_line(f"[dim]{t('subtitle')}[/dim]")
        print_box_line()
        print_box_line(f"  1) {t('menu_search_ip')}")
        print_box_line(f"  2) {t('menu_filter_search')}")
        print_box_line(f"  3) {t('menu_cache_manage')}")
        print_box_line(f"  ?) {t('menu_help_short')}")
        print_box_line(f"  0) {t('menu_back')}")
        print_box_end()

        choice = console.input("\n> ").strip()

        if choice == "0":
            console.print(f"\n[dim]{t('exit_message')}[/dim]")
            break
        elif choice == "?":
            _show_help()
        elif choice == "1":
            _search_by_ip(session_name)
        elif choice == "2":
            _search_by_filter(session_name)
        elif choice == "3":
            _show_cache_menu()

    console.print(f"[green]{t('done')}[/green]")
