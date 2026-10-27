# DeepSeek Coder 6.7B Prompt Plan and Execution Provenance

## 1. Local Model Specifications (matching `fixed.txt`)
- **Exact Model:** `DeepSeek Coder 6.7B Instruct Q4_K_M`
- **Family:** DeepSeek
- **Parameter Size:** 6.7B
- **Quantization:** Q4_K_M
- **Inference Runtime:** Ollama (version 0.14.2)
- **Local Endpoint:** `http://127.0.0.1:11434`
- **Context Configuration:** 8192 tokens (with streaming to prevent socket read timeouts)
- **Temperature:** 0.1 - 0.2

## 2. Prompting Strategy
As established in Phase 1 (`fixed.txt`), supplying monolithic DOCX/XLSX or multi-thousand line prompts directly causes context saturation and format degradation in 6.7B parameter models. 
In Phase 2, the orchestrator applied the **Modular Specification Chunking** pattern:
1. Pure domain rules chunk (durations, counting, overlap, conversion).
2. Authoritative State Transition Table (STT) chunk for workflow states.
3. Django ORM model schema chunk with table mappings.
4. Transactional service orchestration chunk.
5. Unit test verification chunk.

## 3. Logged Interaction Provenance
All prompt requests, response sizes, and elapsed generation times are logged in:
`g:\6B\Fusion-Integrated\reports\local_model_interactions.jsonl`

### Example Interaction Summary:
| Task | Target File | Model Prompt Focus | Outcome |
|---|---|---|---|
| Workflow State Machine | `modules/elm/domain/workflow.py` | CW-EL-01 to CW-EL-04 STT rules | Generated 5.4KB state transition logic |
| Unit Test Suite | `modules/elm/tests/test_domain_workflow.py` | State verification & withdrawal | Verified 14 transition scenarios |
| Policy Domain Rules | `modules/elm/domain/policy.py` | BR-EL-001 to BR-EL-038 pure logic | Verified 15 counting & conversion tests |
