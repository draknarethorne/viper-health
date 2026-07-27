# Contributing

Thanks for contributing to `viper-health`.

## Workflow

1. Create a branch from `main`.
2. Install the project-managed development tools.
3. Install the Git hooks.
4. Keep changes focused and scoped.
5. Add or update tests when behavior changes.
6. Run the local quality and test commands.
7. Ensure CI is green.
8. Open a pull request with a clear summary.

## Development setup

Use Python 3.12 or newer from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e "python[dev]"
.venv\Scripts\pre-commit.exe install --install-hooks
```

PowerShell contributors also need PSScriptAnalyzer 1.25.0:

```powershell
Install-Module PSScriptAnalyzer -RequiredVersion 1.25.0 -Scope CurrentUser
```

## Quality contract

Tool versions and Ruff policy live in `python/pyproject.toml`; hook orchestration
lives in `.pre-commit-config.yaml`. Keep CI and local commands aligned.

Run the same fast gates as CI:

```powershell
.venv\Scripts\pre-commit.exe run --all-files --show-diff-on-failure
```

Run individual language checks while iterating:

```powershell
.venv\Scripts\ruff.exe check python/src python/tests
.\scripts\Invoke-QualityChecks.ps1
.venv\Scripts\python.exe -m pytest -q python/tests
```

Commit-time hooks check file hygiene, YAML, Python defects, and PowerShell.
Pre-push runs the complete test suite. Hooks are a convenience, not the source
of truth: GitHub Actions installs clean dependencies and repeats the gates.

Ruff formatting is configured but not initially enforced repository-wide; it
should be introduced later as a dedicated formatting-only change rather than
mixed into behavior work.

## Commit guidance

- Use descriptive commit messages
- Prefer small, reviewable commits

## Safety requirements (important)

Because this project may include maintenance tooling:

- default behavior must remain read-only
- no hard-delete by default
- immutable/sensitive paths must remain protected
- mutating behavior must include dry-run, manifests, and guardrails
