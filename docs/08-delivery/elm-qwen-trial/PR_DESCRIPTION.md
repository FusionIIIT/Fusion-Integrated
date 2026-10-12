# PR to implement ELM

Adds the ELM backend, frontend, migration and module registration using local Qwen2.5-Coder 3B output. Prompts, responses and mechanical integration fixes are included.

Frontend build, backend checks and the isolated ELM migration pass. Full SQLite migration hits an existing Placement migration error; PostgreSQL remains unverified.

Workflow logic and remaining bugs are unchanged. Functional correctness was not tested.
