# viper-health

SSD and filesystem health diagnostics toolkit (Python + PowerShell).

## Purpose

`viper-health` focuses on long-term filesystem/SSD health by detecting metadata pressure, tiny-file hotspots, churn patterns, and risky growth trends while enforcing safe maintenance boundaries.

## Layout

- `docs/` - specs, architecture notes, and runbooks
- `python/` - Python package and tests
- `powershell/` - PowerShell module
- `config/` - thresholds, allowlists, and profiles
- `data/` - baselines, snapshots, and generated reports
- `scripts/` - convenience entry scripts

See `viper-ssd-health.md` for the authoritative specification.

## Setup

### Python

1. Create/activate a Python 3.12+ environment
2. Install package in editable mode:
   - `pip install -e python`
3. Install test dependencies:
   - `pip install pytest`

### PowerShell

- Module source is under `powershell/PSViperHealth/`.
- Import during development with:
  - `Import-Module .\powershell\PSViperHealth\PSViperHealth.psd1 -Force`

## Development standards

- Default behavior for maintenance tooling must remain read-only unless explicitly overridden.
- Protected/immutable paths must never be auto-cleaned.
- Mutating actions must support dry-run and auditable manifests.

## CI

GitHub Actions runs Python tests on pushes and pull requests to `main`.
