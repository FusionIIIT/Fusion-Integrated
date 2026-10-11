# Local ELM coding prompt

Use this repository's configured local model only for a small, explicit task.

Before editing:
1. Read `modules/elm/README.md`, this prompt, and the exact files named in the task.
2. Inspect `git status --short`; preserve every existing modification.
3. Confirm the active branch and keep edits inside `modules/elm/` unless the task names a specific integration file.

Rules:
- Implement only the requested change and only from the supplied ELM requirements.
- Follow Fusion's module boundaries, API permissions, migration rules and lint style.
- Do not copy reference identities, credentials, private configuration or code without checking it against the requirements.
- Do not invent a policy value. If the specs omit an exact rule, leave it configurable and state the gap.
- Do not edit `.env`, credentials, unrelated modules, or generated dependencies.
- Do not commit, push, change branches, download models or switch to a cloud model.
- Make a focused patch. Summarize changed files and explain any requirement that remains incomplete.
- Do not say a test or command passed unless you ran it and saw its result.

For each task, name the exact outcome, allowed files, acceptance checks
and whether running the named checks is authorized. Ask a short question if a missing
policy detail could change the implementation. Otherwise state a narrow assumption and
continue only within the named files.
