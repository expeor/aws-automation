#!/usr/bin/env python3
"""
Project Index Generator

프로젝트 구조를 스캔하여 .claude/project-index.md 파일을 생성합니다.
Claude Code의 토큰 사용량을 줄이고 프로젝트 탐색을 빠르게 합니다.

Usage:
    python scripts/generate_index.py [--section analyzers|core|git|all]
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Project root detection
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ANALYZERS_DIR = PROJECT_ROOT / "functions" / "analyzers"
REPORTS_DIR = PROJECT_ROOT / "functions" / "reports"
CORE_DIR = PROJECT_ROOT / "core"
OUTPUT_FILE = PROJECT_ROOT / ".claude" / "project-index.md"


def scan_analyzers_and_reports() -> tuple[list[dict], list[dict]]:
    """Scan analyzers and reports directories for CATEGORY/TOOLS metadata."""
    analyzers = []
    reports = []

    # Scan analyzers/
    for init_file in sorted(ANALYZERS_DIR.glob("*/__init__.py")):
        result = _parse_init_file(init_file)
        if result:
            analyzers.append(result)

    # Scan reports/
    for init_file in sorted(REPORTS_DIR.glob("*/__init__.py")):
        result = _parse_init_file(init_file)
        if result:
            reports.append(result)

    return analyzers, reports


def _parse_init_file(init_file: Path) -> dict | None:
    """Parse a single __init__.py file for CATEGORY/TOOLS metadata."""
    service_name = init_file.parent.name
    try:
        content = init_file.read_text(encoding="utf-8")
        # Parse AST to extract CATEGORY and TOOLS
        tree = ast.parse(content)

        category = None
        tools = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "CATEGORY" and isinstance(node.value, ast.Dict):
                            category = ast.literal_eval(ast.unparse(node.value))
                        elif target.id == "TOOLS" and isinstance(node.value, ast.List):
                            tools = ast.literal_eval(ast.unparse(node.value))

        if category:
            # Collect areas from tools
            areas = list({t.get("area", "other") for t in tools if isinstance(t, dict)})
            return {
                "name": service_name,
                "display_name": category.get("display_name", service_name.upper()),
                "description": category.get("description", ""),
                "description_en": category.get("description_en", ""),
                "tool_count": len(tools),
                "areas": sorted(areas),
                "tools": tools,
            }
    except Exception as e:
        print(f"Warning: Failed to parse {init_file}: {e}", file=sys.stderr)

    return None


def get_directory_stats() -> dict:
    """Get file counts for main directories."""
    stats = {}

    for dir_name in ["core", "functions/analyzers", "functions/reports", "tests"]:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            py_files = list(dir_path.rglob("*.py"))
            stats[dir_name] = len(py_files)

    return stats


def get_git_status() -> dict:
    """Get git status for recent changes."""
    modified: list[str] = []
    new: list[str] = []
    branch = "unknown"

    try:
        # Current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()

        # Git status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if status_result.returncode == 0:
            for line in status_result.stdout.strip().split("\n"):
                if not line:
                    continue
                status_code = line[:2]
                file_path = line[3:].strip()

                if status_code.startswith("?"):
                    new.append(file_path)
                elif status_code.strip():
                    modified.append(file_path)

    except FileNotFoundError:
        pass  # git not available

    return {"modified": modified, "new": new, "branch": branch}


def get_core_modules() -> list[dict]:
    """Scan core directory structure."""
    modules = []

    core_subdirs = [
        ("auth", "Authentication providers (SSO Session, SSO Profile, Static)"),
        ("parallel", "Parallel execution, rate limiting"),
        ("tools", "Tool management, file I/O, history"),
        ("region", "Region data and availability"),
        ("cli", "Click CLI, interactive menu, i18n"),
        ("shared", "Shared utilities (AWS metrics/pricing/inventory, I/O excel/html/csv)"),
    ]

    for subdir, description in core_subdirs:
        subdir_path = CORE_DIR / subdir
        if subdir_path.exists():
            py_files = list(subdir_path.rglob("*.py"))
            modules.append(
                {
                    "name": subdir,
                    "description": description,
                    "file_count": len(py_files),
                }
            )

    return modules


def render_index_md(
    analyzers: list[dict],
    reports: list[dict],
    core_modules: list[dict],
    git_status: dict,
    dir_stats: dict,
) -> str:
    """Render the project index markdown."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Calculate totals
    all_items = analyzers + reports
    total_files = sum(dir_stats.values())

    # Count areas
    area_counter: Counter[str] = Counter()
    for p in all_items:
        for area in p["areas"]:
            area_counter[area] += 1

    lines = [
        "# Project Index",
        "",
        "> Auto-generated by `scripts/generate_index.py`",
        f"> Last updated: {now}",
        "> Run `/sync-index` to refresh.",
        "",
        "## Quick Stats",
        "",
        f"- **Total Files**: {total_files} Python files",
        f"- **Analyzers**: {len(analyzers)} services, {sum(p['tool_count'] for p in analyzers)} tools",
        f"- **Reports**: {len(reports)} categories, {sum(p['tool_count'] for p in reports)} tools",
        f"- **Core Modules**: {len(core_modules)}",
        f"- **Branch**: `{git_status['branch']}`",
        "",
        "### Area Distribution",
        "",
    ]

    for area, count in area_counter.most_common():
        lines.append(f"- `{area}`: {count} items")

    lines.extend(
        [
            "",
            "## Directory Map",
            "",
            "| Directory | Files | Description |",
            "|-----------|-------|-------------|",
            f"| `core/` | {dir_stats.get('core', 0)} | CLI infra: auth, parallel, tools, CLI, shared utils |",
            f"| `functions/analyzers/` | {dir_stats.get('functions/analyzers', 0)} | AWS service analysis tools |",
            f"| `functions/reports/` | {dir_stats.get('functions/reports', 0)} | Comprehensive reports |",
            f"| `tests/` | {dir_stats.get('tests', 0)} | pytest tests |",
            "",
            "## Core Modules",
            "",
            "| Module | Files | Description |",
            "|--------|-------|-------------|",
        ]
    )

    for mod in core_modules:
        lines.append(f"| `core/{mod['name']}/` | {mod['file_count']} | {mod['description']} |")

    lines.extend(
        [
            "",
            "## Analyzers Registry",
            "",
            "| Service | Display | Tools | Areas |",
            "|---------|---------|-------|-------|",
        ]
    )

    for p in analyzers:
        areas_str = ", ".join(p["areas"][:3])  # Limit to 3 areas
        if len(p["areas"]) > 3:
            areas_str += "..."
        lines.append(f"| `{p['name']}` | {p['display_name']} | {p['tool_count']} | {areas_str} |")

    lines.extend(
        [
            "",
            "## Reports Registry",
            "",
            "| Name | Display | Tools | Areas |",
            "|------|---------|-------|-------|",
        ]
    )

    for p in reports:
        areas_str = ", ".join(p["areas"][:3])
        if len(p["areas"]) > 3:
            areas_str += "..."
        lines.append(f"| `{p['name']}` | {p['display_name']} | {p['tool_count']} | {areas_str} |")

    lines.extend(
        [
            "",
            "## Core API Summary",
            "",
            "### Parallel Execution (`core.parallel`)",
            "```python",
            "parallel_collect(ctx, callback, service) -> ParallelResult",
            "get_client(session, service, region) -> RateLimited Client",
            "safe_aws_call(service, operation) -> Decorator",
            "ErrorCollector() -> Error classification",
            "```",
            "",
            "### File I/O (`core.shared.io`)",
            "```python",
            "generate_reports(ctx, data, columns) -> Excel + HTML",
            "Workbook().add_sheet(name) -> Excel builder",
            "create_aws_report(title, service, ...) -> HTML report",
            "```",
            "",
            "### Authentication (`core.auth`)",
            "```python",
            "get_provider(profile_name) -> AuthProvider",
            "provider.get_session(region) -> boto3.Session",
            "```",
            "",
        ]
    )

    # Recent changes section
    if git_status["new"] or git_status["modified"]:
        lines.extend(
            [
                "## Recent Changes (uncommitted)",
                "",
            ]
        )

        if git_status["new"]:
            lines.append("### New Files")
            lines.append("")
            for f in git_status["new"][:10]:  # Limit to 10
                lines.append(f"- `{f}`")
            if len(git_status["new"]) > 10:
                lines.append(f"- ... and {len(git_status['new']) - 10} more")
            lines.append("")

        if git_status["modified"]:
            lines.append("### Modified Files")
            lines.append("")
            for f in git_status["modified"][:10]:  # Limit to 10
                lines.append(f"- `{f}`")
            if len(git_status["modified"]) > 10:
                lines.append(f"- ... and {len(git_status['modified']) - 10} more")
            lines.append("")

    # Analyzer details (collapsed)
    lines.extend(
        [
            "## Analyzer Details",
            "",
            "<details>",
            "<summary>Click to expand full tool list</summary>",
            "",
        ]
    )

    for p in analyzers:
        lines.append(f"### {p['display_name']} (`functions/analyzers/{p['name']}`)")
        lines.append("")
        lines.append(f"> {p['description']}")
        lines.append("")

        if p["tools"]:
            lines.append("| Tool | Module | Area |")
            lines.append("|------|--------|------|")
            for tool in p["tools"]:
                name = tool.get("name_en", tool.get("name", "Unknown"))
                module = tool.get("module", "-")
                area = tool.get("area", "-")
                lines.append(f"| {name} | `{module}` | {area} |")
            lines.append("")

    lines.extend(
        [
            "</details>",
            "",
        ]
    )

    # Report details (collapsed)
    lines.extend(
        [
            "## Report Details",
            "",
            "<details>",
            "<summary>Click to expand full tool list</summary>",
            "",
        ]
    )

    for p in reports:
        lines.append(f"### {p['display_name']} (`functions/reports/{p['name']}`)")
        lines.append("")
        lines.append(f"> {p['description']}")
        lines.append("")

        if p["tools"]:
            lines.append("| Tool | Module | Area |")
            lines.append("|------|--------|------|")
            for tool in p["tools"]:
                name = tool.get("name_en", tool.get("name", "Unknown"))
                module = tool.get("module", "-")
                area = tool.get("area", "-")
                lines.append(f"| {name} | `{module}` | {area} |")
            lines.append("")

    lines.extend(
        [
            "</details>",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """Generate project index."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate project index")
    parser.add_argument(
        "--section",
        choices=["analyzers", "core", "git", "all"],
        default="all",
        help="Section to regenerate (default: all)",
    )
    parser.parse_args()

    print(f"Scanning project at {PROJECT_ROOT}...")

    # Always scan everything for now (incremental update can be added later)
    analyzers, reports = scan_analyzers_and_reports()
    print(f"  Found {len(analyzers)} analyzers with {sum(p['tool_count'] for p in analyzers)} tools")
    print(f"  Found {len(reports)} reports with {sum(p['tool_count'] for p in reports)} tools")

    core_modules = get_core_modules()
    print(f"  Found {len(core_modules)} core modules")

    git_status = get_git_status()
    print(f"  Branch: {git_status['branch']}, {len(git_status['new'])} new, {len(git_status['modified'])} modified")

    dir_stats = get_directory_stats()
    print(f"  Total: {sum(dir_stats.values())} Python files")

    # Render and save
    content = render_index_md(analyzers, reports, core_modules, git_status, dir_stats)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(content, encoding="utf-8")

    print(f"\nGenerated: {OUTPUT_FILE}")
    print(f"Size: {len(content):,} bytes")


if __name__ == "__main__":
    main()
