# Employee Leave Management (ELM) — Assignment 6 Pilot

## Overview

This directory contains the Employee Leave Management (ELM) pilot for Fusion ERP, developed as part of Assignment 6 using a local coding model.

ELM is registered as a separate Fusion domain module. The current branch contains the initial module structure, leave-policy code, Django data models and migration, account-ledger code, workflow-related code, and a frontend overview page.

**Status:** Experimental pilot. This is not a claim of a complete, production-ready ELM implementation.

## Module Structure

- `modules/elm/` — Django backend module.
- `modules/elm/domain/` — Leave-policy and workflow-related domain code.
- `modules/elm/services/` — Account and workflow service code.
- `modules/elm/models.py` — ELM-owned database models.
- `modules/elm/migrations/` — Initial database migration.
- `modules/elm/tests/` — ELM test files.
- `client/src/modules/elm/` — Frontend module and overview page.

ELM is registered independently from Placement. The module remains marked as planned, with navigation entries not yet enabled.

## Model and Development Environment

- **Model tag:** `qwen2.5-coder:7b`
- **Inference runtime:** Ollama, running locally
- **Coding agent:** Aider
- **Model parameter count and quantization:** Record the exact values shown by `ollama show qwen2.5-coder:7b`.
- **Operating system and hardware:** Record the actual environment in the Assignment 6 evidence log.

## Verification Record

The recorded mechanical checks that passed include Ruff, Django system checks, migration consistency, import-layer checks, and `git diff --check`.

The permission-manifest check passes with the current registry. The seven ELM permissions are listed as known unenforced gaps because the module is still a planned pilot and does not yet have API endpoints. Passing the manifest check does not mean those actions are implemented or runtime-authorized. The substitute-response permission is granted to faculty and staff.

Earlier focused tests passed at the time they were run. They should not be interpreted as proof that the final working tree is functionally correct.

## Scope and Limitations

This is a model-assisted pilot, not a complete ELM release. Functional completeness, security correctness, and full business-requirement conformance are not claimed in this submission.

## Code Provenance

Qwen2.5-Coder 7B through Ollama and Aider was used in the development process. Some implementation files in the current working tree were also drafted directly with ChatGPT assistance and are not exclusively outputs of the local Qwen/Aider run. This must be reconciled with the Assignment 6 restriction on changes before the branch is described as a Qwen-only submission.
