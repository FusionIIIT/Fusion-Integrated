# Local LLM iteration prompts for Assignment 6B

Use the selected local model already configured for your Phase-1 trial. Keep the original Phase-1 version unchanged.

## Iteration 1 — Repository and specification understanding (no edits)
Inspect the existing Fusion repository, the ELM module and the complete supplied ELM specifications. Summarize the current architecture, module registration, API/URL conventions, IAM permissions, models/migrations, frontend route/navigation convention and the ELM requirement-to-file map. Do not modify files yet. Do not invent missing requirements.

## Iteration 2 — Focused domain/service corrections
Read the ELM workflow and business-rule specifications plus the affected leave service files. Explain each proposed change in terms of a specific requirement and existing defect. Implement only the focused change. Preserve unrelated code and existing Fusion abstractions. Never add an independent user/RBAC table; user references must follow Fusion/IAM conventions.

## Iteration 3 — Regression tests
For every change, add a targeted test for the previously incorrect case and a normal case. Include failure/authorization cases where relevant. Run the focused tests and report exact commands and actual outcomes. If a test cannot run, state why; do not claim it passed.

## Iteration 4 — Integration and migrations
Check whether models and migrations agree. Run migration checks and frontend type/build commands in the repository environment. Fix only failures grounded in the ELM specification or caused by this ELM change. Ensure the module is registered in backend settings, permissions manifest, API URLs, frontend registry and router.

## Iteration 5 — Evidence and final review
Run relevant ELM tests, full project checks and frontend build; list exact commands, passed/failed/skipped results, and logs. Map fixes to requirement IDs from supplied specifications. List remaining gaps honestly. Do not claim deployment-ready if critical behavior has not been verified.

## Guardrails
- Never overwrite the preserved Phase-1 copy.
- Do not copy another pair's implementation.
- Use the supplied specification package as the source of truth.
- Keep changes within ELM and required Fusion integration surfaces.
- Inspect diffs before committing; do not merge the PR.
