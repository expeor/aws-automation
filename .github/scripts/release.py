#!/usr/bin/env python3
"""Release automation script for Conventional Commits.

This script analyzes commits since the last tag, determines version bump type,
and updates version.txt and CHANGELOG.md accordingly.

Usage:
    python release.py analyze   # Analyze commits and output version info
    python release.py update    # Update version.txt and CHANGELOG.md
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

# Repository URL for PR/compare links
REPO_URL = "https://github.com/expeor/aws-automation"

# Conventional Commit patterns
COMMIT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|refactor|perf|docs|test|chore|ci|style|build|revert)"
    r"(?P<breaking>!)?(?:\((?P<scope>[^)]+)\))?:\s*(?P<description>.+)$"
)

# Version bump mapping
VERSION_BUMP: dict[str, Literal["major", "minor", "patch", "none"]] = {
    "feat": "minor",
    "fix": "patch",
    "refactor": "patch",
    "perf": "patch",
    "docs": "none",
    "test": "none",
    "chore": "none",
    "ci": "none",
    "style": "none",
    "build": "none",
    "revert": "patch",
}

# Changelog section headers
CHANGELOG_SECTIONS = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "docs": "Documentation",
    "revert": "Reverted",
}


@dataclass
class Commit:
    """Represents a parsed conventional commit."""

    hash: str
    type: str
    scope: str | None
    description: str
    breaking: bool
    pr_number: int | None = None

    @property
    def full_message(self) -> str:
        """Return full commit message with scope if present."""
        scope_part = f"({self.scope})" if self.scope else ""
        return f"{self.type}{scope_part}: {self.description}"


@dataclass
class ReleaseInfo:
    """Release analysis result."""

    current_version: str
    new_version: str
    version_type: Literal["major", "minor", "patch", "none"]
    should_release: bool
    commits: list[Commit] = field(default_factory=list)
    changelog_content: str = ""


def run_git(args: list[str]) -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    return (result.stdout or "").strip()


def get_last_tag() -> str | None:
    """Get the most recent version tag."""
    tags = run_git(["tag", "-l", "v*", "--sort=-version:refname"])
    if tags:
        return tags.split("\n")[0]
    return None


def get_commits_since_tag(tag: str | None) -> list[tuple[str, str]]:
    """Get commits since the specified tag.

    Returns list of (hash, message) tuples.
    """
    if tag:
        range_spec = f"{tag}..HEAD"
    else:
        range_spec = "HEAD"

    log_output = run_git(["log", range_spec, "--oneline", "--no-merges"])
    if not log_output:
        return []

    commits = []
    for line in log_output.split("\n"):
        if line:
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append((parts[0], parts[1]))
    return commits


def extract_pr_number(message: str) -> int | None:
    """Extract PR number from commit message.

    Looks for patterns like "(#123)" at end of message or "#123" anywhere.
    """
    # Check for squash merge pattern: "message (#123)"
    pr_match = re.search(r"\(#(\d+)\)$", message)
    if pr_match:
        return int(pr_match.group(1))

    # Check for PR reference anywhere in message
    pr_match = re.search(r"#(\d+)", message)
    if pr_match:
        return int(pr_match.group(1))

    return None


def parse_commit(commit_hash: str, message: str) -> Commit | None:
    """Parse a commit message into a Commit object."""
    # Extract PR number before parsing (from full message)
    pr_number = extract_pr_number(message)

    # Remove PR number suffix for pattern matching
    clean_message = re.sub(r"\s*\(#\d+\)$", "", message)

    match = COMMIT_PATTERN.match(clean_message)
    if not match:
        return None

    return Commit(
        hash=commit_hash,
        type=match.group("type"),
        scope=match.group("scope"),
        description=match.group("description"),
        breaking=bool(match.group("breaking")),
        pr_number=pr_number,
    )


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch) tuple."""
    parts = version_str.strip().split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(
    current: str, bump_type: Literal["major", "minor", "patch"]
) -> str:
    """Calculate new version based on bump type."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def determine_version_type(
    commits: list[Commit],
) -> Literal["major", "minor", "patch", "none"]:
    """Determine version bump type based on commits."""
    has_breaking = any(c.breaking for c in commits)
    if has_breaking:
        return "major"

    # Find highest priority bump
    bump_priority = {"major": 3, "minor": 2, "patch": 1, "none": 0}
    max_bump: Literal["major", "minor", "patch", "none"] = "none"

    for commit in commits:
        commit_bump = VERSION_BUMP.get(commit.type, "none")
        if bump_priority[commit_bump] > bump_priority[max_bump]:
            max_bump = commit_bump

    return max_bump


def generate_changelog_section(
    commits: list[Commit], version: str, prev_version: str | None
) -> str:
    """Generate CHANGELOG section for this release."""
    sections: dict[str, list[str]] = {}

    for commit in commits:
        section = CHANGELOG_SECTIONS.get(commit.type)
        if not section:
            continue

        if section not in sections:
            sections[section] = []

        # Format commit entry with optional PR link
        entry = f"- {commit.full_message}"
        if commit.pr_number:
            entry += f" ([#{commit.pr_number}]({REPO_URL}/pull/{commit.pr_number}))"

        sections[section].append(entry)

    # Build changelog content
    today = date.today().isoformat()
    lines = [f"## [{version}] - {today}", ""]

    # Order: Added, Changed, Fixed, Documentation, Reverted
    section_order = ["Added", "Changed", "Fixed", "Documentation", "Reverted"]
    for section_name in section_order:
        if section_name in sections:
            lines.append(f"### {section_name}")
            lines.extend(sections[section_name])
            lines.append("")

    return "\n".join(lines)


def generate_compare_link(version: str, prev_version: str | None) -> str:
    """Generate version compare link for CHANGELOG footer."""
    if prev_version:
        return f"[{version}]: {REPO_URL}/compare/{prev_version}...v{version}"
    return f"[{version}]: {REPO_URL}/releases/tag/v{version}"


def analyze() -> ReleaseInfo:
    """Analyze commits and determine release info."""
    # Get current version
    version_file = Path("version.txt")
    current_version = version_file.read_text().strip()

    # Get last tag
    last_tag = get_last_tag()

    # Get commits since last tag
    raw_commits = get_commits_since_tag(last_tag)

    # Parse commits
    commits = []
    for commit_hash, message in raw_commits:
        parsed = parse_commit(commit_hash, message)
        if parsed:
            commits.append(parsed)

    # Determine version type
    version_type = determine_version_type(commits)

    # Calculate new version
    if version_type == "none":
        new_version = current_version
        should_release = False
    else:
        new_version = bump_version(current_version, version_type)
        should_release = True

    # Generate changelog
    changelog_content = ""
    if should_release:
        changelog_content = generate_changelog_section(
            commits, new_version, last_tag
        )

    return ReleaseInfo(
        current_version=current_version,
        new_version=new_version,
        version_type=version_type,
        should_release=should_release,
        commits=commits,
        changelog_content=changelog_content,
    )


def update_version_file(new_version: str) -> None:
    """Update version.txt with new version."""
    Path("version.txt").write_text(f"{new_version}\n")
    print(f"Updated version.txt to {new_version}")


def update_changelog(changelog_section: str, new_version: str, prev_tag: str | None) -> None:
    """Update CHANGELOG.md with new release section."""
    changelog_path = Path("CHANGELOG.md")
    content = changelog_path.read_text()

    # Find insertion point (after header, before first version section)
    lines = content.split("\n")
    insert_idx = 0

    for i, line in enumerate(lines):
        # Find first version section (## [x.y.z])
        if re.match(r"^## \[\d+\.\d+\.\d+\]", line):
            insert_idx = i
            break

    # Insert new section
    new_lines = lines[:insert_idx]
    new_lines.extend(changelog_section.split("\n"))
    new_lines.extend(lines[insert_idx:])

    # Update compare links at the bottom
    compare_link = generate_compare_link(new_version, prev_tag)

    # Find existing compare links section and add new one
    final_lines = []
    added_link = False
    for line in new_lines:
        if re.match(r"^\[\d+\.\d+\.\d+\]:", line) and not added_link:
            final_lines.append(compare_link)
            added_link = True
        final_lines.append(line)

    # If no existing links, add at the end
    if not added_link:
        final_lines.append("")
        final_lines.append(compare_link)

    changelog_path.write_text("\n".join(final_lines))
    print(f"Updated CHANGELOG.md with version {new_version}")


def output_github_actions(info: ReleaseInfo) -> None:
    """Output results for GitHub Actions."""
    github_output = os.environ.get("GITHUB_OUTPUT")

    outputs = {
        "current_version": info.current_version,
        "new_version": info.new_version,
        "version_type": info.version_type,
        "should_release": str(info.should_release).lower(),
    }

    if github_output:
        with open(github_output, "a") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")

    # Also print for debugging
    for key, value in outputs.items():
        print(f"{key}={value}")


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: release.py [analyze|update]")
        return 1

    command = sys.argv[1]

    if command == "analyze":
        info = analyze()
        output_github_actions(info)

        if info.should_release:
            print(f"\nRelease needed: {info.current_version} -> {info.new_version}")
            print(f"Commits analyzed: {len(info.commits)}")
        else:
            print("\nNo release needed (no version-affecting commits)")

        return 0

    elif command == "update":
        info = analyze()

        if not info.should_release:
            print("No release needed")
            return 0

        # Get previous tag for compare link
        prev_tag = get_last_tag()

        # Update files
        update_version_file(info.new_version)
        update_changelog(info.changelog_content, info.new_version, prev_tag)

        return 0

    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
