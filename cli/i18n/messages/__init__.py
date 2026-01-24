"""
cli/i18n/messages/__init__.py - Message Registry

Aggregates all message dictionaries from sub-modules.
Messages are organized by namespace (common, ec2, rds, etc.)

Structure:
    MESSAGES = {
        "common.select_profile": {"ko": "...", "en": "..."},
        "common.auth_failed": {"ko": "...", "en": "..."},
        "ec2.unused_eip_title": {"ko": "...", "en": "..."},
        ...
    }
"""

from __future__ import annotations

from typing import TypedDict


class MessageDict(TypedDict):
    """Message dictionary type."""

    ko: str
    en: str


# Master message registry
MESSAGES: dict[str, MessageDict] = {}


def register_messages(namespace: str, messages: dict[str, MessageDict]) -> None:
    """Register messages for a namespace.

    Args:
        namespace: Namespace prefix (e.g., "common", "ec2")
        messages: Dictionary of message key -> translations
    """
    for key, value in messages.items():
        MESSAGES[f"{namespace}.{key}"] = value


# Import and register all message modules
# These imports must come after register_messages is defined
from cli.i18n.messages.area import AREA_MESSAGES  # noqa: E402
from cli.i18n.messages.cli_commands import CLI_MESSAGES  # noqa: E402
from cli.i18n.messages.common import COMMON_MESSAGES  # noqa: E402
from cli.i18n.messages.excel import EXCEL_MESSAGES  # noqa: E402
from cli.i18n.messages.flow import FLOW_MESSAGES  # noqa: E402
from cli.i18n.messages.menu import MENU_MESSAGES  # noqa: E402
from cli.i18n.messages.runner import RUNNER_MESSAGES  # noqa: E402

register_messages("common", COMMON_MESSAGES)
register_messages("area", AREA_MESSAGES)
register_messages("menu", MENU_MESSAGES)
register_messages("excel", EXCEL_MESSAGES)
register_messages("runner", RUNNER_MESSAGES)
register_messages("cli", CLI_MESSAGES)
register_messages("flow", FLOW_MESSAGES)

__all__ = ["MESSAGES", "register_messages", "MessageDict"]
