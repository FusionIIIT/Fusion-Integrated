# Local Qwen workflow for the ELM pilot

## Verified environment

The Windows host reported Ollama 0.40.2 and Codex CLI 0.162.1. Ollama lists
`qwen2.5-coder:1.5b` as a Qwen2 1.5B model quantized Q4_K_M (about 986 MB),
with a 32K model context. A direct `ollama run` prompt returned
`LOCAL_QWEN_OK`. This verifies local text inference only; it does not show
that Qwen wrote this module.

Codex CLI's local OSS route was tried with Ollama and reasoning effort
`none`. It reached the local model, but Codex reported missing model metadata
and the model returned an unexpected tool-call-shaped response instead of the
requested text. That is not a reliable coding-agent result. The earlier
thinking-mode error is therefore only avoidable by selecting an effort the
model/client accepts; it does not make this 1.5B model reliable inside Codex.

Aider is the documented alternative in this repository, but it was not
installed or executed during this pilot. The configuration below pins Aider to
the installed Ollama model and disables automatic commits. Aider recommends
the `ollama_chat/` model prefix and supports fixed Ollama `num_ctx` through
its model settings file. Start with 8K context and small file-scoped requests
on this 8 GB machine. Do not pull another model for this workflow.

## Start a local Aider session

Install Aider only if you choose to try it:

```bash
python -m pip install aider-install
aider-install
```

Keep Ollama running on Windows. In the WSL repository, confirm the local
endpoint responds before starting the agent:

```bash
curl http://127.0.0.1:11434/api/tags
aider --read modules/elm/README.md --read docs/elm-local-model-prompt.md
```

The repository configuration selects
`ollama_chat/qwen2.5-coder:1.5b`; it contains no cloud API key or cloud-model
fallback. If the WSL endpoint cannot reach the Windows Ollama service, resolve
that local networking path before invoking Aider. Do not change the model to a
cloud provider.

## Task size and review

Give one task at a time. Name the exact file(s), expected behavior and a short
acceptance list. Include only the relevant requirement excerpt. Ask for a small
patch, then inspect `git diff` and `git status` yourself. Run one focused
check after each task, followed by the repository checks that fit the change.
Review migrations and permissions manually. Keep each prompt and included file
context small; this model has limited coding-agent reliability.

Example task:

> Read `modules/elm/README.md` and `modules/elm/domain/policy.py`. In
> `modules/elm/domain/policy.py` only, add a pure helper that checks whether a
> half-day CL request overlaps an existing request. Use the ELM rule stated in
> this task. Do not edit any other file. Do not commit or run unrelated checks.
> Return the patch summary and any uncertainty.

## What this workflow proves

Direct Ollama inference was verified. Codex CLI reached Ollama but did not
follow the response format in a one-turn probe. Aider's compatibility remains
unverified until installed and exercised on a small throwaway task. No code in
this repository is attributed to Qwen-generated output.
