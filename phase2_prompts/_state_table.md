# ELM state-transition table (transcribed from Workflow Specifications v1.6 STTs of CW-EL-01, CW-EL-02, CW-EL-03; BR-EL-016..020, 022, 023, 025)

State values (strings, identical to LeaveApplication.STATUS_CHOICES):
 awaiting_substitute, applicant_action_required, awaiting_unit_head, awaiting_establishment, awaiting_final_sanction,
 awaiting_director_self_sanction, approved, rejected, withdrawn,
 cancellation_pending_unit_head, cancellation_pending_establishment, cancellation_pending_final, cancelled.
(An extension request is a separate LeaveApplication row with kind="extension" that uses the same pending states.)

Actor kinds: employee (the applicant), substitute, unit_head, establishment, authority (final Sanctioning Authority: Dean/Registrar/Director...),
director (the Director acting as Sanctioning Authority on their own leave), system.

Category classes: UNIT_HEAD_FINAL = {CL, RH}; HIGHER_SANCTION = {SCL, EL, COL, VL}.
Scope of a transition: "any", "unit_head_final" (only CL/RH), or "higher" (only SCL/EL/COL/VL).

Permissions (strings): "leave_management.application.create", "leave_management.application.respond",
 "leave_management.application.review", "leave_management.application.delete".

| from | to | actor kinds | permission | scope | guard name |
|---|---|---|---|---|---|
| awaiting_substitute | awaiting_unit_head | substitute | respond | any | substitute_accepts_non_director |
| awaiting_substitute | awaiting_director_self_sanction | substitute | respond | any | substitute_accepts_director_applicant |
| awaiting_substitute | applicant_action_required | substitute | respond | any | substitute_declines |
| applicant_action_required | awaiting_substitute | employee | create | any | eligible_replacement_nominated |
| awaiting_unit_head | approved | unit_head | review | unit_head_final | - |
| awaiting_unit_head | rejected | unit_head | review | unit_head_final | has_reason |
| awaiting_unit_head | awaiting_establishment | unit_head | review | higher | recommendation_recorded, establishment_configured |
| awaiting_unit_head | awaiting_final_sanction | unit_head | review | higher | recommendation_recorded, no_establishment_step |
| awaiting_establishment | awaiting_final_sanction | establishment | review | higher | routing_context_valid |
| awaiting_final_sanction | approved | authority | review | higher | - |
| awaiting_final_sanction | rejected | authority | review | higher | has_reason |
| awaiting_director_self_sanction | approved | director | review | any | - |
| awaiting_director_self_sanction | rejected | director | review | any | has_reason |
| approved | cancellation_pending_unit_head | employee | create | any | before_start_date |
| cancellation_pending_unit_head | cancelled | unit_head | review | unit_head_final | - |
| cancellation_pending_unit_head | approved | unit_head | review | unit_head_final | has_reason  (cancellation rejected, original unchanged) |
| cancellation_pending_unit_head | cancellation_pending_establishment | unit_head | review | higher | recommendation_recorded, establishment_configured |
| cancellation_pending_unit_head | cancellation_pending_final | unit_head | review | higher | recommendation_recorded, no_establishment_step |
| cancellation_pending_establishment | cancellation_pending_final | establishment | review | higher | routing_context_valid |
| cancellation_pending_final | cancelled | authority | review | higher | - |
| cancellation_pending_final | approved | authority | review | higher | has_reason  (cancellation rejected, original unchanged) |
| withdraw: each of awaiting_substitute, applicant_action_required, awaiting_unit_head, awaiting_establishment, awaiting_final_sanction, awaiting_director_self_sanction | withdrawn | employee | delete | any | - |

Not allowed (must be illegal): any move out of rejected, withdrawn or cancelled; withdrawing from approved or from any cancellation_pending_* state;
approved -> rejected; awaiting_unit_head -> approved for higher-sanction categories; skipping the substitute gate.
Initial state on submission (a separate function, not a table row):
 substitute required -> awaiting_substitute; else applicant is Director -> awaiting_director_self_sanction; else awaiting_unit_head.
