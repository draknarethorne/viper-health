# Viper Health - Copilot Instructions

## Project Overview

**viper-health** is a Windows-focused SSD/filesystem health toolkit built with Python and PowerShell.

Primary goals:
- Detect filesystem pressure signals before performance degrades
- Track trends over time (tiny-file growth, churn acceleration, metadata stress)
- Preserve safety via strict cleanup guardrails (read-only default, immutable paths, dry-run/manifest requirements)

Authoritative spec:
- `viper-ssd-health.md`

---

## Technical Stack

### Python
- Package root: `python/`
- Source: `python/src/viper_health/`
- Tests: `python/tests/`
- Runtime baseline: Python 3.12+

### PowerShell
- Module root: `powershell/PSViperHealth/`
- Collectors/Analyzers/Scoring/Reports structure mirrors Python architecture

### Infrastructure
- GitHub Actions CI: `.github/workflows/ci.yml`
- Release tags: `.github/workflows/release.yml`

---

## Implemented Detectors & CLIs (observe-only)

All detector families in the spec (Section 4) plus drive-health checks are
implemented in Python and test-backed. The toolkit is **read-only**; maintenance
mode (spec Sections 3, 8) is intentionally deferred.

| CLI (`python -m viper_health.cli.<x>`) | Purpose |
| --- | --- |
| `scan` | Unified tiny-file + directory-density scan with health score |
| `suite` | Preset-based multi-target scans (`config/scan-presets.yaml`) |
| `scan_tiny_files` / `scan_directory_density` | Individual detectors |
| `scan_metadata` | Composite metadata pressure (4.3) |
| `scan_targets` | Cloud/browser/update/telemetry churn (4.4-4.7) |
| `scan_snapshot` | Capture/diff snapshots for churn velocity (Sec 11) |
| `scan_mft` | MFT size + fragmentation (admin) |
| `check_trim` | TRIM status (admin) |
| `check_space` | Free-space thresholds |
| `check_smart` | Drive health / SMART / temperature |
| `check_io` | Top disk-I/O processes |
| `benchmark_io` | Sequential/random I/O benchmarks |
| `compare_baseline` | Trend analysis vs saved baseline |

---

## Project Structure

```text
viper-health/
├── viper-ssd-health.md
├── python/
│   ├── src/viper_health/
│   │   ├── collectors/
│   │   ├── analyzers/
│   │   ├── scoring/
│   │   ├── reports/
│   │   ├── cli/
│   │   └── utils/
│   └── tests/
├── powershell/PSViperHealth/
├── config/
├── data/
├── scripts/
└── .github/
    ├── workflows/
    └── agents/
```

---

## Core Engineering Rules

1. **Safety first**
   - Default mode must remain read-only.
   - Never implement silent mutation behavior.
   - Mutating paths must be constrained by allowlists and immutable-root protections.

2. **Deterministic outputs**
   - Prefer structured outputs (JSON objects / typed data classes) over ad-hoc strings.
   - Keep report schema stable and test-protected.

3. **Test-backed changes**
   - New detectors/analyzers must include unit tests.
   - Regressions should be captured in tests before broad refactors.

4. **Separation of concerns**
   - Collectors gather facts.
   - Analyzers classify risk.
   - Scoring aggregates severity.
   - CLI/report layers format output.

---

## Safety Constraints (Non-Negotiable)

- Do not auto-clean immutable/sensitive paths.
- Do not hard-delete by default; quarantine-first design is preferred.
- Require dry-run and manifest generation before mutating operations.
- Include action caps/kill-switch behavior in maintenance logic.
- Preserve explicit protection for VS Code built-in extension paths.

---

## Preferred Workflow for Changes

1. Read relevant files first.
2. Create/update todo list for multi-step work.
3. Implement minimal, targeted changes.
4. Run tests (`pytest`) after each meaningful change.
5. Summarize changes with file-level clarity.

---

## Validation Commands

Use the configured virtual environment interpreter.

- Test suite: run pytest against `python/tests/`
- Editable install: install package from `python/`

---

## Communication Style

- Keep responses concise, structured, and actionable.
- Prefer explicit risk notes when discussing cleanup/mutation behavior.
- For major architecture choices, provide rationale + trade-offs.

---

## Agent Usage

For deep project work, use:
- `.github/agents/ViperHealth-Beast-Mode.agent.md`

Specialized companions:
- `.github/agents/ViperHealth-Implementation.agent.md`
- `.github/agents/ViperHealth-Testing.agent.md`
- `.github/agents/ViperHealth-Analysis.agent.md`
- `.github/agents/ViperHealth-Documentation.agent.md`

Selection index:
- `.github/agents/AGENT-SELECTION-GUIDE.md`
- `.github/AGENTS.md`
