---
purpose: >
  Record the hardware, local-model configuration, observed outcome and
  limitations of Assignment 6 Trial 1 using the supplied ELM specifications.
---

# Assignment 6 Qwen3 trial record

This trial produced a partial ELM scaffold inside the current Fusion base.
The frontend builds after mechanical integration corrections. The backend
configuration check fails on a generated model-field constraint. This is a
pilot result, not a complete or functionally verified ELM implementation.

## Hardware and configuration

| Item | Recorded value |
| --- | --- |
| Date | 11 October 2026, Asia/Kolkata |
| OS | Ubuntu 26.04.1 LTS |
| CPU | Intel Core i7-13620H |
| RAM | Approximately 30 GiB usable system RAM |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU |
| GPU memory | 8188 MiB reported by NVIDIA tooling |
| Model | `qwen3:8b`, 8.2B parameters, `Q4_K_M` |
| Model digest | `500a1f067a9f` prefix; full digest retained in local evidence |
| Runtime | Ollama 0.32.13, local endpoint only |
| Coding harness | OpenCode 1.18.34, external plugins disabled |
| Context configurations | 16,384 and 32,768 tokens; returned to 16,384 |
| Output limit | 4096 tokens per response |
| Sampling | Temperature 0.6, top-p 0.95, top-k 20 |
| Thinking setting | `/no_think` instruction |
| Clean starting commit | `02b01fea4a67b257ea7000009f06a1561699550e` |

The model aliases only change runtime parameters; they use the same installed
Qwen3 weights. This is one model trial with configuration variations, not two
different-model trials. No cloud model generated the ELM implementation.

## Procedure and observations

All six supplied ELM artifacts were preserved and extracted into readable
text. Spreadsheet cell coordinates and table columns were retained. The
workflow document's 22 images were preserved with supplementary OCR; OCR
does not reliably preserve arrows. The text was also split into roughly
6 KB chunks. Complete specification coverage was not demonstrated.

The first 16K attempt made file-search mistakes, compacted its context and
returned a requirements summary without writing application code. A fresh
32K retry wrote backend files but referenced infrastructure absent from this
Fusion base. It was paused to provide the actual Fusion interfaces.

Subsequent prompts continued that same retry session and reused its files.
They provided exact repository excerpts, separated code generation from
environment/build commands, and explicitly requested the missing frontend
files. The 32K configuration showed 29% CPU / 71% GPU execution; 16K showed
8% CPU / 92% GPU. These are observed Ollama residency reports, not benchmark
throughput measurements.

The first run began at 21:37 IST and the final generation response ended at
22:36 IST: about one hour including coordination intervals, with about
49 minutes across foreground model runs. Raw outputs, prompts, session
exports, timing logs, model details and correction records were retained
locally. The original working checkout and its lockfile changes were preserved.

| Trial item | Observation |
| --- | --- |
| Loaded successfully | Yes |
| Could access Fusion repository | Yes |
| Could access ELM specifications | Yes; used only part of the available context |
| Could inspect/edit multiple files | Yes |
| Reused Fusion infrastructure | Partly; required explicit references and mechanical adapters |
| Frontend generation | Partial: four list/dashboard pages, hooks and routing |
| Backend generation | Partial: four data models, serializers and CRUD viewsets |
| Database integration | Migration generated; not applied to an existing database |
| Build/run outcome | Partial: frontend build passes; backend check fails |
| Main difficulty | Context loss, inaccurate interfaces and invalid Edit operations |
| Most useful workaround | Small context chunks and focused continuations in the same session |
| Overall impression | Marginal with substantial coordination |

## Integration corrections and validation

Coordinator edits were restricted to file placement, imports, external identity
references, existing authorization interfaces, registration, URL/component
bindings and dependency interfaces. The original Placement entry, authentication
routes and platform routes were preserved. Migration and permission-manifest
artifacts were generated using existing project commands.

Generated leave workflow logic and displayed data fields were not repaired.
No systematic business-rule testing, security hardening, optimization or
functional completeness review was performed. Request forms, detail/edit
workflows and year-end/SLA processing remain incomplete or placeholders.

| Verification | Result |
| --- | --- |
| `npm run build` | Pass after mechanical integration corrections |
| Python syntax parsing | Pass for 10 ELM Python files |
| `ops/checks/no_cross_module_fk.py` | Pass |
| `manage.py permission_manifest --skip-checks` | Pass; generated the manifest and catalogue |
| `manage.py makemigrations elm --skip-checks` | Generated `0001_initial.py`; no migration applied |
| `manage.py check` | Fail: `elm.LeaveType.type` reports `fields.E009` |

The model uses `max_length=3` while one generated choice is 13 characters.
That generated constraint error was retained. Management-command verification
used temporary in-memory SQLite configuration, without modifying a user
database. Frontend dependencies were copied from the existing local install;
a fresh lockfile-based dependency install was not verified. Full `make check`,
end-to-end IAM login and functional UI/database behavior were not verified.

## Recommendation

Qwen3 8B can load and write coordinated files on this machine, but this setup
was unreliable for unattended repository implementation. Use it only with
small context sections and active coordination. Larger context increased CPU
offload without resolving integration mistakes. A second model-family trial
is separate work and has not been claimed in this record.
