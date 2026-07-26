"""Advisory analysis of startup, service, and background-process load.

Pure and testable. Turns a passive ``startup_items`` snapshot into advisory
recommendations: which auto-start programs to pause, which auto services are
candidates to set to Manual, and which known heavy apps are consuming memory.
Nothing here disables anything — recommendations include the safe manual step.
"""

from __future__ import annotations

import os
from typing import Any

# Known apps (by executable/process token) and how to reduce their footprint.
KNOWN_APPS: dict[str, dict[str, str]] = {
    "chrome": {"label": "Google Chrome", "advice": "Each tab/extension is a process; close unused tabs or enable Memory Saver."},
    "msedge": {"label": "Microsoft Edge", "advice": "Close unused tabs; disable startup boost if not needed."},
    "msedgewebview2": {"label": "WebView2 runtime (Copilot/Teams/widgets)", "advice": "Shared runtime; multiple instances are normal but tie to the host apps."},
    "discord": {"label": "Discord", "advice": "Pause at startup via Task Manager > Startup, or Discord Settings > Windows Settings > Open Discord = Off."},
    "onedrive": {"label": "OneDrive", "advice": "Sync churn is heavy on small files; pause sync when not needed or limit synced folders."},
    "googledrivefs": {"label": "Google Drive", "advice": "Use streaming (not mirror) mode and pause sync when idle to cut small-file churn."},
    "code": {"label": "VS Code", "advice": "Disable unused extensions per-workspace; file watchers and language servers add background load."},
    "devenv": {"label": "Visual Studio", "advice": "Very memory-heavy; close solutions you are not actively using."},
    "eqgame": {"label": "TAKP / EverQuest", "advice": "Game client; close fully when not playing (it can hold GPU/CPU)."},
    "takp": {"label": "TAKP launcher", "advice": "Close the launcher when not playing."},
    "copilot": {"label": "Copilot", "advice": "Runs as an app/WebView; close when not in use."},
    "slack": {"label": "Slack", "advice": "Pause at startup; runs in tray."},
    "teams": {"label": "Microsoft Teams", "advice": "Disable auto-start if not needed; it launches WebView2."},
}

# Third-party updater/helper services commonly safe to set to Manual. Matched
# by vendor-specific patterns to avoid flagging Windows core services (e.g. IP
# Helper, Update Orchestrator) that merely contain generic words.
_MANUAL_SERVICE_HINTS = (
    "adobe", "acrobat update", "google update", "googleupdater", "edgeupdate",
    "brave update", "mozilla maintenance", "intel(r) driver", "nvidia",
    "steam client", "epic online", "office click-to-run", "dropbox update",
)

# Core services we never suggest changing.
_PROTECTED_SERVICE_TOKENS = (
    "wuauserv", "windows update", "wsearch", "defender", "wscsvc", "bits",
    "dcomlaunch", "rpcss", "lsm", "profsvc", "eventlog", "windows security",
    "ip helper", "iphlpsvc", "orchestrator", "usosvc", "dosvc",
    "delivery optimization", "medic", "waasmedic", "cryptographic", "cryptsvc",
    "connected devices", "network", "firewall",
)


def _exe_token(command: str) -> str:
    """Extract a lowercase executable token from a startup command string."""
    text = str(command or "").strip().strip('"')
    # Take up to the first .exe if present.
    lowered = text.lower()
    index = lowered.find(".exe")
    if index != -1:
        text = text[: index + 4]
    base = os.path.basename(text.strip('"'))
    return base.lower().replace(".exe", "")


def _match_known(token: str) -> dict[str, str] | None:
    for key, meta in KNOWN_APPS.items():
        if key in token:
            return {"key": key, **meta}
    return None


def analyze_startup(data: dict[str, Any]) -> dict[str, Any]:
    """Classify startup/service/process load into advisory recommendations."""
    startup_commands = _as_list(data.get("StartupCommands"))
    services = _as_list(data.get("Services"))
    processes = _as_list(data.get("Processes"))

    startup_entries: list[dict[str, Any]] = []
    for entry in startup_commands:
        token = _exe_token(entry.get("Command", ""))
        known = _match_known(token)
        startup_entries.append(
            {
                "name": entry.get("Name"),
                "location": entry.get("Location"),
                "token": token,
                "known": bool(known),
                "label": known["label"] if known else entry.get("Name"),
                "recommendation": (
                    f"{known['advice']} Pause at startup via Task Manager > Startup if not needed."
                    if known
                    else "Review in Task Manager > Startup; disable if you don't need it at boot."
                ),
            }
        )

    manual_service_candidates: list[dict[str, Any]] = []
    for service in services:
        name = str(service.get("Name") or "")
        display = str(service.get("DisplayName") or "")
        blob = f"{name} {display}".lower()
        if any(token in blob for token in _PROTECTED_SERVICE_TOKENS):
            continue
        if any(hint in blob for hint in _MANUAL_SERVICE_HINTS):
            manual_service_candidates.append(
                {
                    "name": name,
                    "display_name": display,
                    "state": service.get("State"),
                    "recommendation": (
                        "Auto-start updater/helper — consider Services.msc > set to Manual. "
                        "Verify the app still updates when launched before changing."
                    ),
                }
            )

    heavy_processes: list[dict[str, Any]] = []
    for proc in processes:
        name = str(proc.get("Name") or "")
        token = name.lower()
        known = _match_known(token)
        working_set = proc.get("WorkingSetBytes") or 0
        try:
            memory_mb = round(int(working_set) / (1024**2), 1)
        except (TypeError, ValueError):
            memory_mb = 0.0
        if known and memory_mb >= 100:
            heavy_processes.append(
                {
                    "name": name,
                    "label": known["label"],
                    "instances": proc.get("Count"),
                    "memory_mb": memory_mb,
                    "recommendation": known["advice"],
                }
            )

    recommendations: list[str] = []
    if heavy_processes:
        top = ", ".join(f"{p['label']} ({p['memory_mb']:.0f} MB)" for p in heavy_processes[:5])
        recommendations.append(f"Highest-memory known apps right now: {top}. Close the ones you are not using.")
    known_startup = [e for e in startup_entries if e["known"]]
    if known_startup:
        names = ", ".join(sorted({e["label"] for e in known_startup}))
        recommendations.append(f"Known apps launching at startup: {names}. Pause any you don't need at boot in Task Manager > Startup.")
    if manual_service_candidates:
        recommendations.append(
            f"{len(manual_service_candidates)} auto-start updater/helper service(s) could be set to Manual (verify first)."
        )
    if not recommendations:
        recommendations.append("No heavy known apps or third-party auto-start load identified.")

    return {
        "startup_entries": startup_entries,
        "manual_service_candidates": manual_service_candidates,
        "heavy_processes": heavy_processes,
        "recommendations": recommendations,
    }


def _as_list(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []
