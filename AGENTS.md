# AGENTS.md

## Overview

This document outlines the governance structure for the local Qwen 2.5 7B coding agent within the Fusion-Integrated repository root, specifically for the Employee Leave Management (ELM) module of the Fusion ERP system.

---

## Operational Architecture

### Antigravity (Gemini)

**Role:** Project Orchestrator  
**Functionality:**
- Inspects the codebase.
- Breaks down engineering tasks.
- Dispatches prompts to local Qwen 2.5 7B for coding and documentation generation.
- Runs builds and tests.
- Verifies diffs.
- Reports progress.
- Requests user approval.

**Restrictions:**  
- Antigravity must NEVER independently write or rewrite ELM application code.

### Local Qwen 2.5 7B

**Role:** Sole AI Coding Agent  
**Functionality:**
- Generates or modifies ELM application code, migrations, tests, and technical documentation.
- Operates under strict guidelines to ensure compliance with the Fusion ERP specifications.

---

## Mandatory Model Configuration

### Model
- **Name:** `qwen2.5:7b` (Q4_K_M, 4.68 GB GGUF)

### Runtime
- **Platform:** Windows Ollama
- **Endpoint:** `http://localhost:11434/v1`

### Digest Configuration
- **Mandatory Digest Prefix:** `845dbda0ea48`

### Safety Policies & Interaction Logging

#### Safe Tool Policies
- Restricted to the `Fusion-Integrated` repository.
- Human approval is mandatory before applying any file modifications, migrations, or destructive commands.

#### Full Persistence
- All interactions are logged in the `local_agent/logs/` directory. Logs include:
  - Prompts
  - Model responses
  - Timestamps
  - Elapsed time
  - Model digest

---

## Conclusion

This governance document ensures that the local Qwen 2.5 7B coding agent operates within strict parameters to maintain the integrity and security of the Fusion ERP Employee Leave Management (ELM) module. Any deviations from these guidelines must be approved by a human overseer.

---

