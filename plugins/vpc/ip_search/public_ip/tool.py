"""
plugins/vpc/ip_search/public_ip/tool.py - Public IP Search Tool

Search cloud provider IP ranges (AWS, GCP, Azure, Oracle).
No AWS authentication required.
"""

import os
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from plugins.vpc.ip_search.common.ip_ranges import (
    PublicIPResult,
    get_available_filters,
    get_public_cache_status,
    refresh_public_cache,
    search_by_filter,
    search_public_ip,
)
from core.tools.output.builder import OutputPath

from .i18n import t

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
        writer.writerow([
            t("header_ip"),
            t("header_provider"),
            t("header_service"),
            t("header_ip_range"),
            t("header_region"),
        ])
        for r in results:
            writer.writerow([r.ip_address, r.provider, r.service, r.ip_prefix, r.region])

    return filepath


def _export_excel(results: list[PublicIPResult], session_name: str) -> str:
    """Export results to Excel file."""
    try:
        from core.tools.io.excel import ColumnDef, Workbook
    except ImportError:
        console.print("[red]core.tools.io.excel not available[/red]")
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

    lines = [f"{t('header_ip')}\t{t('header_provider')}\t{t('header_service')}\t{t('header_ip_range')}\t{t('header_region')}"]
    for r in results:
        lines.append(f"{r.ip_address}\t{r.provider}\t{r.service}\t{r.ip_prefix}\t{r.region}")

    pyperclip.copy("\n".join(lines))
    return True


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


def _show_export_menu(results: list[PublicIPResult], session_name: str) -> bool:
    """Show export options menu. Returns True to continue, False to exit."""
    console.print(f"\n[bold cyan]{t('export_title')}[/bold cyan]")
    console.print(f"  (1) {t('export_csv')}")
    console.print(f"  (2) {t('export_excel')}")
    console.print(f"  (3) {t('export_clipboard')}")
    console.print(f"  (0) {t('export_continue')}")

    choice = Prompt.ask(t("prompt_select"), choices=["0", "1", "2", "3"], default="0")

    if choice == "1":
        filepath = _export_csv(results, session_name)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
    elif choice == "2":
        filepath = _export_excel(results, session_name)
        if filepath:
            console.print(f"[green]{t('export_saved', path=filepath)}[/green]")
    elif choice == "3":
        if _copy_to_clipboard(results):
            console.print(f"[green]{t('export_copied')}[/green]")

    return True  # Continue searching


def _show_cache_status() -> None:
    """Display cache status for all providers."""
    status = get_public_cache_status()

    console.print(f"\n[bold cyan]{t('cache_status_title')}[/bold cyan]")

    for provider, info in status["providers"].items():
        if info.get("cached"):
            valid_str = f"[green]{t('cache_valid')}[/green]" if info.get("valid") else f"[yellow]{t('cache_expired')}[/yellow]"
            console.print(f"  {provider}: {valid_str} - {info.get('count', 0)} prefixes ({info.get('time', '')})")
        else:
            console.print(f"  {provider}: [dim]{t('cache_none')}[/dim]")


def _show_cache_menu() -> None:
    """Show cache management menu."""
    _show_cache_status()

    console.print(f"\n  (1) {t('cache_refresh')}")
    console.print(f"  (0) {t('menu_back')}")

    choice = Prompt.ask(t("prompt_select"), choices=["0", "1"], default="0")

    if choice == "1":
        with console.status(f"[bold yellow]{t('cache_refreshing')}[/bold yellow]"):
            result = refresh_public_cache()

        if result["success"]:
            counts = ", ".join(f"{p}: {result['counts'].get(p, 0)}" for p in result["success"])
            console.print(f"[green]{t('cache_refresh_done')}[/green]")
            console.print(f"  [dim]{counts}[/dim]")
        if result["failed"]:
            console.print(f"[yellow]{t('cache_refresh_failed')}: {', '.join(result['failed'])}[/yellow]")


# =============================================================================
# Search Functions
# =============================================================================


def _search_by_ip(session_name: str) -> None:
    """Search IP addresses in cloud provider ranges."""
    console.print(f"\n[dim]{t('prompt_enter_ip')}[/dim]")
    ip_input = Prompt.ask(f"[bold cyan]{t('header_ip')}[/bold cyan]").strip()

    if not ip_input:
        return

    ip_list = [ip.strip() for ip in ip_input.split(",") if ip.strip()]
    if not ip_list:
        return

    with console.status(f"[bold yellow]{t('searching')}[/bold yellow]"):
        results = search_public_ip(ip_list)

    if not results:
        console.print(f"\n[yellow]{t('result_no_match')}[/yellow]")
        return

    # Filter out Unknown if there are known matches for the same IP
    known_results = [r for r in results if r.provider != "Unknown"]
    unknown_ips = {r.ip_address for r in results if r.provider == "Unknown"}
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
    console.print(f"  (0) {t('menu_back')}")

    provider_choice = Prompt.ask(t("prompt_select"), choices=["0", "1", "2", "3", "4"], default="1")

    if provider_choice == "0":
        return

    providers = {"1": "aws", "2": "gcp", "3": "azure", "4": "oracle"}
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

    # Get filter input
    console.print(f"\n[dim]{t('prompt_enter_filter')}[/dim]")
    filter_value = Prompt.ask("[bold yellow]Filter[/bold yellow]").strip()

    if not filter_value:
        return

    # Search
    with console.status(f"[bold yellow]{t('searching')}[/bold yellow]"):
        # Try as region first, then as service
        results = search_by_filter(provider=provider, region=filter_value)
        if not results:
            results = search_by_filter(provider=provider, service=filter_value)

    if not results:
        console.print(f"\n[yellow]{t('result_no_match')}[/yellow]")
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


def run(ctx) -> None:
    """
    Public IP Search Tool entry point.

    Args:
        ctx: Execution context
    """
    from cli.ui.console import print_box_end, print_box_line, print_box_start

    session_name = getattr(ctx, "profile_name", None) or "default"

    while True:
        # Main menu with box style
        print_box_start(t('title'))
        print_box_line(f"[dim]{t('subtitle')}[/dim]")
        print_box_line()
        print_box_line(f"  1) {t('menu_search_ip')}")
        print_box_line(f"  2) {t('menu_filter_search')}")
        print_box_line(f"  3) {t('menu_cache_manage')}")
        print_box_line(f"  0) {t('menu_back')}")
        print_box_end()

        choice = console.input(f"\n> ").strip()

        if choice == "0":
            console.print(f"\n[dim]{t('exit_message')}[/dim]")
            break
        elif choice == "1":
            _search_by_ip(session_name)
        elif choice == "2":
            _search_by_filter(session_name)
        elif choice == "3":
            _show_cache_menu()

    console.print(f"[green]{t('done')}[/green]")
