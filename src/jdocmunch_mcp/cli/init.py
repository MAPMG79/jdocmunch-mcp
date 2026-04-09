"""jdocmunch-mcp init -- one-command hook installer for Claude Code."""

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Optional


_ENFORCEMENT_HOOKS = {
    "PreToolUse": [{
        "matcher": "Read",
        "hooks": [{"type": "command", "command": "jdocmunch-mcp hook-pretooluse"}],
    }],
    "PostToolUse": [{
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "jdocmunch-mcp hook-posttooluse"}],
    }],
    "PreCompact": [{
        "matcher": "",
        "hooks": [{"type": "command", "command": "jdocmunch-mcp hook-precompact"}],
    }],
}


def _settings_json_path() -> Path:
    """Return the Claude Code settings.json path."""
    if platform.system() == "Windows":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".claude" / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning {} if it doesn't exist."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict[str, Any], *, backup: bool = True) -> None:
    """Write JSON, optionally creating a .bak backup first."""
    if backup and path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _merge_hooks(
    data: dict[str, Any],
    hook_defs: dict[str, list],
    marker: str,
) -> list[str]:
    """Merge hook definitions into settings data, returning names of added events.

    ``marker`` is a substring used to detect whether our hook is already
    installed (e.g. ``"jdocmunch-mcp hook-p"``).

    Each rule is checked individually: if a rule's command already exists
    in the event's hook list, it is skipped.
    """
    hooks = data.setdefault("hooks", {})
    added: list[str] = []

    for event_name, event_hooks in hook_defs.items():
        existing_cmds: set[str] = set()
        if event_name in hooks:
            for rule in hooks[event_name]:
                for h in rule.get("hooks", []):
                    existing_cmds.add(h.get("command", ""))

        new_rules = []
        for rule in event_hooks:
            rule_cmds = [h.get("command", "") for h in rule.get("hooks", [])]
            if any(cmd in existing_cmds for cmd in rule_cmds if cmd):
                continue
            if any(marker in cmd for cmd in existing_cmds):
                if any(marker in cmd for cmd in rule_cmds):
                    continue
            new_rules.append(rule)

        if new_rules:
            if event_name in hooks:
                hooks[event_name].extend(new_rules)
            else:
                hooks[event_name] = new_rules
            added.append(event_name)

    return added


def install_hooks(*, dry_run: bool = False, backup: bool = True) -> str:
    """Merge PreToolUse/PostToolUse/PreCompact hooks into ~/.claude/settings.json.

    Returns a status message.
    """
    path = _settings_json_path()
    data = _read_json(path)
    added = _merge_hooks(data, _ENFORCEMENT_HOOKS, "jdocmunch-mcp hook-p")

    if not added:
        return f"  hooks already present in {path}"
    if dry_run:
        return f"  would add {', '.join(added)} hooks to {path}"

    _write_json(path, data, backup=backup)
    return f"  added {', '.join(added)} hooks to {path}"


def run_init(*, hooks: bool = False, dry_run: bool = False) -> None:
    """Run the init command."""
    from jdocmunch_mcp import __version__
    print(f"jdocmunch-mcp {__version__} init", file=sys.stderr)

    if hooks:
        msg = install_hooks(dry_run=dry_run)
        print(msg)
    else:
        print("Usage: jdocmunch-mcp init --hooks")
        print("  --hooks    Install enforcement hooks into ~/.claude/settings.json")
        print("  --dry-run  Show what would be done without making changes")
