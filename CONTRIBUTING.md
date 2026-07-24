# Contributing

Thanks for contributing to `viper-health`.

## Workflow

1. Create a branch from `main`
2. Keep changes focused and scoped
3. Add/update tests when behavior changes
4. Ensure CI is green
5. Open a pull request with a clear summary

## Commit guidance

- Use descriptive commit messages
- Prefer small, reviewable commits

## Safety requirements (important)

Because this project may include maintenance tooling:

- default behavior must remain read-only
- no hard-delete by default
- immutable/sensitive paths must remain protected
- mutating behavior must include dry-run, manifests, and guardrails
