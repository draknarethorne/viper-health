# Release Checklist

Viper Health releases are evidence-driven milestones. A tag must identify a
tested commit and must not publish machine-specific reports as an installable
artifact.

## Version policy

- Use semantic versions such as `v0.5.0` or `v0.5.0-beta.1`.
- Keep the tag, `python/pyproject.toml`, and
  `powershell/PSViperHealth/PSViperHealth.psd1` versions identical after
  removing the tag's leading `v` and any prerelease suffix.
- Use prerelease tags while behavior or report contracts are still being
  validated.

## Before tagging

- Confirm `main` is clean and synchronized with `origin/main`.
- Review changes since the previous tag and prepare release notes.
- Run all pre-commit gates and the complete Python test suite.
- Confirm default operation remains read-only.
- Confirm unavailable evidence remains unknown rather than green.
- Review documentation for unsupported or obsolete claims.
- Confirm no generated reports, host identifiers, logs, or secrets are present
  in the release bundle.

## Release artifact

The tag workflow creates a curated source bundle containing code,
configuration, documentation, and project metadata. It deliberately excludes
the repository's `data/` evidence tree. The workflow publishes the ZIP and a
SHA-256 checksum beside the generated GitHub release notes.

The bundle is not a standalone executable and does not include Python. Follow
the development/install instructions in `README.md`.

## After publishing

- Download the ZIP and verify it against `SHA256SUMS.txt` on both Windows and a
  Unix-compatible checksum tool.
- Confirm the archive contains no `data/`, `.venv/`, cache, or secret files.
- Confirm the release notes identify important safety or schema changes.
- If validation fails, remove the release artifact and correct the workflow;
  do not silently replace a versioned artifact with different bytes.
