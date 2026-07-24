# Agent Selection Guide

## Available Agents

- `ViperHealth-Beast-Mode.agent.md` — Primary deep-work orchestrator for architecture, implementation, safety guardrails, and test-backed delivery.
- `ViperHealth-Implementation.agent.md` — Multi-file code implementation specialist for collectors/analyzers/CLI/reporting.
- `ViperHealth-Testing.agent.md` — QA and regression-validation specialist for tests, diagnostics, and output contract checks.
- `ViperHealth-Analysis.agent.md` — Read-heavy analysis specialist for root-cause, trend, and cross-module impact assessment.
- `ViperHealth-Documentation.agent.md` — Documentation specialist for README/spec/runbook/instruction updates.

## When to Use ViperHealth-Beast-Mode

Use it for:
- building new detectors/analyzers
- adding or refactoring maintenance guardrails
- implementing CLI/report orchestration
- adding and hardening test coverage
- multi-file technical updates requiring architectural consistency

Avoid using it for:
- tiny one-line edits
- purely cosmetic markdown changes
- unrelated non-project context tasks

## Task Routing

### Implementation-heavy tasks
Use `ViperHealth-Implementation` when work includes:
- new module creation
- multi-file refactors
- CLI/report orchestration updates

### Validation-heavy tasks
Use `ViperHealth-Testing` when work includes:
- adding regression tests
- investigating failing tests
- validating output contract stability

### Research and diagnostics tasks
Use `ViperHealth-Analysis` when work includes:
- understanding churn patterns
- root-cause investigation
- architecture impact analysis before coding

### Docs and handoff tasks
Use `ViperHealth-Documentation` when work includes:
- updating onboarding docs
- keeping specs and README aligned to implementation
- writing operational runbooks for safe maintenance workflows
