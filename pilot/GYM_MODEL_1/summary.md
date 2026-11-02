# Trial 1 — Local AI Coding Model Summary (Gymkhana Module)

## 1. Environment & Model Configuration
- **Machine**: Apple MacBook Air (M3, 16 GB Unified Memory)
- **OS**: macOS (Darwin)
- **Model**: `qwen2.5-coder:7b` (7.6B parameters)
- **Quantization**: `Q4_K_M` (4.7 GB)
- **Inference Runtime**: Ollama
- **Coding Agent**: Continue VS Code Extension (`32K` context window)

## 2. Step-by-Step Implementation Log
| Step | Description | Outcome |
|---|---|---|
| Step 1 | Module foundation (`apps.py`, `registry.py`) | Created module metadata, 9 navigation items, and 11 permissions |
| Step 2 | Initial Django ORM models (`models.py`) | Generated `Club`, `ClubLeadership`, `ClubMembership`, `VenueBooking`, `VotingPoll`, `PollOption`, `PollVote`, `ClubBudgetRequest`, `ClubEventReport` |
| Step 3 | Domain policy (`domain/policy.py`) | Defined pure-Python business rules (`BR-GYM-001` through `BR-GYM-021`) |
| Step 4 | Application services (`services/applications.py`) | Implemented transactional workflows for club creation/confirmation, venue bookings, membership approval, and polling |
| Step 5 | REST API (`api/serializers.py`, `views.py`, `urls.py`) | Created DRF views and serializers guarded by `HasModuleGrant` and `HasPermission` |
| Step 6 | Module & route registration (`settings/base.py`, `urls.py`) | Registered module in `DOMAIN_MODULES` and mounted `/api/v1/gymkhana/` in root URLs |
| Step 7 | Database migration (`migrations/0001_initial.py`) | Initial schema migration for all 9 Gymkhana tables |
| Step 8 | Frontend wiring & pages (`client/`) | Registered gymkhana routes and created React dashboard, management, and voting pages |
| Step 10 | Mechanical integration pass | Validated ADR-0013 zero cross-module FK rule, verified integer ID conventions, and updated permissions.json |
| Step 11 | Documentation & trial summary | Documented prompts, interaction history, and baseline readiness |

## 3. Practical Observations & Friction Notes
- Prompting with raw docx files caused issues because Continue tried to read the underlying XML zip stream. Converting the specs into markdown slices under specs/ made ingestion much faster and accurate.
- Agent mode in Continue struggled with multi-file edits and emitted raw JSON tool calls. Chat mode with specific file tags (@file) gave much better, directly usable code blocks.
- Qwen occasionally defaulted to standard Django patterns like models.ForeignKey(User). Explicitly reminding the model to use integer IDs for user references in each prompt was necessary to adhere to Fusion's ADR-0013 rule.
- Method parameter binding in DRF views: Qwen wrote some post handlers expecting pk in request.data instead of the URL kwargs. Fixed those mechanically during the integration pass.
