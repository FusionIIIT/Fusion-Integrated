# Phase 1 — Reconstructed AI Implementation Prompts

This is a reconstructed prompt sequence based on the recorded Assignment 6 context and final Employee Leave Management implementation. It is not a verified verbatim interaction transcript.

**Model label:** qwen2.5-coder:7b

**Final PR:** https://github.com/FusionIIIT/Fusion-Integrated/pull/88

**Final diff:** 66 changed files; 5,280 added lines; 2 deleted lines.

## Prompt 1 — Initial ELM implementation

```text
Work on the supplied Fusion-Integrated base code in this isolated
checkout. Read the available Assignment 6 instructions, Fusion
architecture documentation, module development guides and reference
modules before starting.

Inspect the existing Django backend, Placement module, IAM
permissions, database models, API structure and frontend integration.

The complete official ELM specification package is not available
in this workspace. Do not invent missing institutional rules.
Record unavailable requirements and assumptions as limitations.

Attempt an initial Employee Leave Management module using Fusion's
existing infrastructure. Keep the implementation consistent with
the project's conventions and avoid unrelated rewrites.

Implement leave types, policy validation, leave applications,
approval and cancellation workflows, employee balances, database
models, migrations, API routes and permission enforcement.

Use a state machine for leave requests and an append-only ledger
for balance changes. Prevent unauthorized approvals, overlapping
requests and duplicate accounting transactions.

Connect the module to Fusion's existing authentication, module
registry, frontend navigation and React/TypeScript client.

Provide usable leave application, history, balance, approval
and administrative pages using existing shared components.

Add regression tests for application workflows, permissions,
balance accounting, state transitions and access control.

Run available Django checks, migration checks, permission checks,
Python lint, frontend typechecking and build verification.

Synchronize generated permission manifests and OpenAPI schemas.
Document the implementation, actual verification results and
remaining limitations. Do not claim full ELM specification
coverage when the official specifications are unavailable.
```

**Implementation commit:** `7a7373efa2834c9f0fd3f7246c7959aea024ec7e`

## Prompt 2 — Fix generated OpenAPI schema consistency

```text
Review the generated OpenAPI schema for the ELM module.

The application status choices are derived from an unordered
frozenset, which can cause the generated enum order to change
between runs.

Make the status choices deterministic without changing the
workflow behavior.

Update the relevant serializer and regenerate the OpenAPI
schema. Verify that repeated schema generation produces the
same output across different Python hash seeds.

Run the relevant lint and ELM regression checks, and avoid
unrelated implementation changes.
```

**Follow-up commit:** `1389791a2d62fccfdaafc0e0615049f2138d9aa7`

## Recorded Implementation Output

- Integrated ELM backend, database models and migrations.
- Leave application, approval and cancellation workflows.
- Ledger-backed balances and policy administration.
- IAM permissions and employee-data isolation.
- REST API endpoints and React/TypeScript frontend.
- Celery scheduling and management commands.
- Backend and frontend regression tests.
- Permission manifest and OpenAPI integration.
- Deterministic status enum generation.

## Implementation Evidence

**Pull Request:** https://github.com/FusionIIIT/Fusion-Integrated/pull/88

**Recorded changes:** 66 files, 5,280 additions, 2 deletions.

The PR reports using both qwen2.5-coder:7b and gpt-oss:20b. It does not establish which model produced each change.
