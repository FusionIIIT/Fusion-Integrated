# Verified observations for documentation

{
  "model": "qwen3.5:9b",
  "details": {
    "parent_model": "",
    "format": "safetensors",
    "family": "qwen3_5",
    "families": null,
    "parameter_size": "9.7B",
    "quantization_level": "nvfp4",
    "runner": "mlx"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "generation_requests": 11,
  "code_request_wall_seconds": 2504.01,
  "output_limit_requests": [
    "001",
    "003"
  ],
  "requests": [
    {
      "prompt": "001",
      "label": "Backend foundation",
      "wall_seconds": 604.65,
      "prompt_eval_count": 19787,
      "eval_count": 8192,
      "done_reason": "length"
    },
    {
      "prompt": "002",
      "label": "Complete missing public contracts",
      "wall_seconds": 64.58,
      "prompt_eval_count": 4231,
      "eval_count": 1173,
      "done_reason": "stop"
    },
    {
      "prompt": "003",
      "label": "Backend services and selectors",
      "wall_seconds": 826.37,
      "prompt_eval_count": 20865,
      "eval_count": 6500,
      "done_reason": "length"
    },
    {
      "prompt": "004",
      "label": "Complete missing selectors",
      "wall_seconds": 16.53,
      "prompt_eval_count": 623,
      "eval_count": 302,
      "done_reason": "stop"
    },
    {
      "prompt": "005",
      "label": "Backend API and scheduled work",
      "wall_seconds": 381.51,
      "prompt_eval_count": 13607,
      "eval_count": 4426,
      "done_reason": "stop"
    },
    {
      "prompt": "006",
      "label": "Frontend types, queries and route table",
      "wall_seconds": 178.53,
      "prompt_eval_count": 10290,
      "eval_count": 1443,
      "done_reason": "stop"
    },
    {
      "prompt": "007",
      "label": "Frontend MyLeavePage",
      "wall_seconds": 112.72,
      "prompt_eval_count": 2080,
      "eval_count": 1246,
      "done_reason": "stop"
    },
    {
      "prompt": "008",
      "label": "Frontend LeaveTasksPage",
      "wall_seconds": 88.45,
      "prompt_eval_count": 2078,
      "eval_count": 1240,
      "done_reason": "stop"
    },
    {
      "prompt": "009",
      "label": "Frontend LeaveAdminPage",
      "wall_seconds": 152.31,
      "prompt_eval_count": 2088,
      "eval_count": 1562,
      "done_reason": "stop"
    },
    {
      "prompt": "010",
      "label": "Frontend imported model type interfaces",
      "wall_seconds": 23.02,
      "prompt_eval_count": 1278,
      "eval_count": 220,
      "done_reason": "stop"
    },
    {
      "prompt": "011",
      "label": "Frontend missing imported JSON editor helper",
      "wall_seconds": 55.34,
      "prompt_eval_count": 2290,
      "eval_count": 691,
      "done_reason": "stop"
    },
    {
      "prompt": "012",
      "label": "Documentation trial README, record and comparison",
      "wall_seconds": 178.59,
      "prompt_eval_count": 5227,
      "eval_count": 1479,
      "done_reason": "stop"
    }
  ],
  "checks": [
    {
      "label": "foundation-python-compilation",
      "returncode": 0,
      "wall_seconds": 0.05
    },
    {
      "label": "foundation-django-registration",
      "returncode": 1,
      "wall_seconds": 0.65
    },
    {
      "label": "foundation-registration-corrected",
      "returncode": 0,
      "wall_seconds": 0.57
    },
    {
      "label": "generate-elm-schema",
      "returncode": 0,
      "wall_seconds": 0.48
    },
    {
      "label": "isolated-foundation-schema-install",
      "returncode": 0,
      "wall_seconds": 0.21
    },
    {
      "label": "foundation-contract-compilation",
      "returncode": 0,
      "wall_seconds": 0.04
    },
    {
      "label": "plural-contract-interface-check",
      "returncode": 1,
      "wall_seconds": 0.03
    },
    {
      "label": "plural-contract-interface-corrected",
      "returncode": 0,
      "wall_seconds": 0.03
    },
    {
      "label": "service-syntax-check",
      "returncode": 0,
      "wall_seconds": 0.04
    },
    {
      "label": "service-selector-import-check",
      "returncode": 1,
      "wall_seconds": 0.54
    },
    {
      "label": "service-selector-import-corrected",
      "returncode": 0,
      "wall_seconds": 0.4
    },
    {
      "label": "backend-api-registration",
      "returncode": 1,
      "wall_seconds": 0.55
    },
    {
      "label": "backend-api-registration-corrected",
      "returncode": 0,
      "wall_seconds": 0.44
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0,
      "wall_seconds": 0.03
    },
    {
      "label": "schema-model-drift",
      "returncode": 0,
      "wall_seconds": 0.56
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0,
      "wall_seconds": 0.82
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1,
      "wall_seconds": 1.36
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0,
      "wall_seconds": 0.21
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0,
      "wall_seconds": 0.42
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0,
      "wall_seconds": 0.23
    },
    {
      "label": "backend-task-imports",
      "returncode": 0,
      "wall_seconds": 1.04
    },
    {
      "label": "api-schema-generation",
      "returncode": 0,
      "wall_seconds": 0.79
    },
    {
      "label": "permission-manifest-registration",
      "returncode": 1,
      "wall_seconds": 0.58
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2,
      "wall_seconds": 2.88
    },
    {
      "label": "frontend-after-interface-corrections",
      "returncode": 2,
      "wall_seconds": 1.95
    },
    {
      "label": "frontend-complete-typecheck",
      "returncode": 2,
      "wall_seconds": 1.59
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0,
      "wall_seconds": 1.52
    },
    {
      "label": "backend-final-registration",
      "returncode": 0,
      "wall_seconds": 0.62
    },
    {
      "label": "frontend-production-build",
      "returncode": 0,
      "wall_seconds": 4.4
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0,
      "wall_seconds": 0.03
    }
  ],
  "hardware_record": "Recorded in trial-metadata.json; exported identifiers redacted. Target reproduction PC is not measured trial hardware.",
  "functional_correctness": "Not evaluated; model logic preserved.",
  "full_baseline_migration": "Failed in pre-existing Placement0009 on disposable SQLite",
  "permission_manifest_registration": "Failed; no permission behavior repairs performed",
  "comparison_limits": "Same official base/specification exercise; prompt ordering, settings, runtime and quantization differ. Exploratory comparison only."
}

# First-model summary

{
  "model": "qwen2.5-coder:3b",
  "details": {
    "parameter_size": "3.1B",
    "quantization_level": "Q4_K_M",
    "format": "gguf",
    "runner": "ggml"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "generation_requests": 34,
  "code_request_wall_seconds": 1734.58,
  "output_limit_requests": [
    1,
    3,
    5,
    7,
    9
  ],
  "final_build_status": "Compilation, frontend production build, Django system checks, isolated ELM schema and import boundaries passed after mechanical integration corrections; full temporary SQLite migration failed in pre-existing Placement0009; workflow correctness unverified",
  "checks": [
    {
      "label": "Foundation Python compilation",
      "returncode": 0
    },
    {
      "label": "Foundation Python compilation after batch recovery",
      "returncode": 0
    },
    {
      "label": "Django foundation import and registration",
      "returncode": 1
    },
    {
      "label": "Django registration after mixin inheritance correction",
      "returncode": 1
    },
    {
      "label": "Generate schema migration from Qwen models",
      "returncode": 1
    },
    {
      "label": "Django model registration after related-name correction",
      "returncode": 0
    },
    {
      "label": "Generate schema migration from registered Qwen models",
      "returncode": 0
    },
    {
      "label": "backend-import-registration",
      "returncode": 1
    },
    {
      "label": "backend-api-imports",
      "returncode": 1
    },
    {
      "label": "backend-api-imports-corrected",
      "returncode": 0
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0
    },
    {
      "label": "isolated-elm-schema-install",
      "returncode": 0
    },
    {
      "label": "schema-model-drift",
      "returncode": 0
    },
    {
      "label": "full-baseline-schema-install",
      "returncode": 1
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2
    },
    {
      "label": "frontend-after-interface-retries",
      "returncode": 2
    },
    {
      "label": "frontend-current-typecheck",
      "returncode": 2
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0
    },
    {
      "label": "frontend-production-build",
      "returncode": 0
    },
    {
      "label": "final-harness-compilation",
      "returncode": 0
    }
  ],
  "comparison_limits": "Same official base and specification exercise. Prompt ordering, configurations, quantization and runtimes differ; this is exploratory, not a controlled performance benchmark."
}


# Method and limits

# Qwen 3.5 9B ELM trial

Independent clean worktree from official latest main 02b01fea4a67b257ea7000009f06a1561699550e, identical to the first trial base. No first-model ELM application output was copied. Shared trial harness, specification extracts and initial task plans were reused.

The installed model supports thinking; requests explicitly set think=false to generate code without a separate thinking phase. Actual per-call settings and outputs will be recorded. Build/integration checks only; workflow bugs are to remain. This is an exploratory comparison, not a controlled performance benchmark.

During prompt001, ollama ps reported qwen3.5:9b using 7.7 GB, 100% GPU, context4096 and runnermlx despite requested num_ctx32768. Requested settings do not by themselves establish the runtime context actually used. This discrepancy is preserved rather than assuming identical effective settings across models.

Comparison limits: stage instructions and specification inputs are reused, but this trial uses the final evolved harness (references before CURRENT TASK), while early first-trial prompts used the older ordering. Model/runtime/quantization and thinking capability differ. This is the same implementation exercise, not byte-identical prompting or a controlled model-efficiency benchmark.

For API generation, removed repeated specification text from input because this stage wraps existing generated service/model interfaces, without changing their logic. Full specifications were provided to foundation/service stages. API request uses shorter interface-only context and requested context16384; exact payload will be logged.

Frontend interface generation uses requested context16384 and temperature0.2, with exact options saved in each request. First-model build/timing summary copied for later comparison only; its ELM application source was not used as second-model input.

Backend Django checks, syntax compilation, isolated schema/module seeding, import boundaries, migration drift, task imports and API schema generation passed. API schema emitted one operation-ID collision warning. Full temporary SQLite migration failed in baseline Placement0009. The repository permission-manifest registration command failed validation; its full output is retained in checks.log. No permission enforcement or application behavior was changed to pass that gate, in accordance with the mechanical-correction-only scope. This is partial integration success, not a claim that every repository gate passes.

Final frontend strict TypeScript and production build passed after documented mechanical interface corrections. Remaining build warnings were retained without optimization. Navigation route registration passed. Application generation used eleven recorded requests, totaling2504.01 seconds of aggregate request wall time (about41.7 minutes), excluding documentation requests and supervision/build time. Original checkout remains separate from codex/elm-qwen35-9b.


# Mechanical corrections

# Mechanical integration corrections

Prompt001 truncated contracts.py; six complete preceding JSON file values were recovered unchanged. See 001.recovery.json for hashes. Registered modules.leave_elm in DOMAIN_MODULES and added empty package initializers. No model/domain/registry logic changed.

Django fields.E009: adapted LeaveApplication.category max_length2 to3 to fit existing declared choices. Choice values, other fields and logic unchanged. See mechanical-001.patch.

Plural-contract interface check rejected two extra scalar helpers generated by prompt002. Renamed get_holidays and get_vacation_periods to module-private _get_holidays/_get_vacation_periods; retained their signatures and bodies exactly. The requested plural getters are unchanged. No workflow logic repaired.

Prompt003 hit its output limit in selectors/leave.py. Recovered complete service and initializer strings unchanged; incomplete selector not applied.

Selector import corrected from .models (nonexistent selectors.models) to modules.leave_elm.models. No selector bodies changed. See mechanical-003.patch.

Import check found domain package exports referencing files the model did not generate. Removed only the nonexistent imports and matching __all__ names; retained exports from existing policy.py unchanged. No domain calculations or services changed. See mechanical-004.patch.

Registered ELM root API URLs, frontend static route import, Celery schedule/routes and import-boundary configuration. See integration-registration.patch.

API import/registration check failed because ViewSet.as_view lacked HTTP-to-action dictionaries. Adapted existing URL declarations to their existing action names, imported serializers and their LeavePolicy model, and converted the generated list schedule to Fusion/Celery mapping configuration with actual registered task names. Preserved paths, schedule intervals, action bodies and task logic. See mechanical-005.patch.

Normalized registered ELM API URL suffixes to Fusion/client paths without a trailing slash. Preserved endpoint/action mapping and all view bodies. See mechanical-006.patch. The preceding frontend prompt retains the exact earlier route excerpt it received.

Adapted frontend shared-http import placement, imported the already declared LeaveRequest type, removed unused imports and prefixed an unused parameter for existing strict compiler settings. Exported hook names, argument positions, request bodies and request operations unchanged. See mechanical-007.patch.

Added @mantine/form7.13.4 to package.json/package-lock.json to satisfy the model-generated employee-page import, matching the repository Mantine version. Replaced only the worktree dependency symlink with independent npm-installed dependencies; original checkout files remain untouched. No application behavior changed.

First TypeScript check recorded import/library-interface errors. Corrected Textarea/errorMessage imports, unused imports, Axios response-envelope access, explicit callback typings and non-null date-index typing. Changed unsupported button active prop to data-active. Preserved the model's unsupported form schema object using spread (no validation rules were implemented), and adapted the existing substitute-mutation argument transport to React Query5's single variables object with the same supplied values/request body. The unused apply-hook argument now accepts Partial<LeaveRequest>. No action buttons were connected or business logic repaired. See mechanical-008.patch.

Admin-page compiler adaptations: removed unused imports/binding while retaining the balance-hook call; adjusted shared PageHeader children to its actual action prop; corrected Axios notification envelope access; placed the missing model-generated JSON editor helper within the ELM module and adapted the import. No admin handler or request logic repaired. See mechanical-009.patch.

JSON helper compiler corrections: imported TextInput, adapted react-icons/rx export names using aliases, removed unused imports, added type-only non-null index assertions and a no-op reference retaining the unused addField function. No new field button, index guard, validation or workflow repair was introduced. See mechanical-010.patch.

Qwen-generated documentation received factual corrections for actual paths/layout, branch name, response/job meaning, diff purpose, separate frontend/backend/database results and measured timings. Removed an unsupported first-trial classification/gate comparison; original model prose remains in prompt012.response.txt. See documentation-factual-corrections.patch. Application logic unchanged.
