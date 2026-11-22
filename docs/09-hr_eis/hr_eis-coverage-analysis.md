# HR-EIS coverage analysis

Coverage was collected using the repository's prescribed branch coverage commands against PostgreSQL. Before adding the tests in this pass, `modules/hr` measured 62.57% statement coverage and `modules/hr/domain` measured 71.09%. The table records every initially uncovered executable line and branch arc from that baseline run. Source files were not changed during this coverage pass.

| File | Initially uncovered lines | Initially uncovered branch arcs (source -> destination) |
|---|---|---|
| `modules/hr/api/serializers.py` | 77-80, 83, 100-103, 106, 169-173, 178, 354-356 | 79->80, 79->83, 102->103, 102->106, 169->170, 169->178, 354->355, 354->356 |
| `modules/hr/api/views.py` | 52, 59-62, 74-75, 84-88, 91, 106, 109-111, 120-122, 125, 143-144, 153-156, 177-181, 190-192, 195, 204-206, 209, 218-220, 223, 234-236, 239, 260-263, 268, 280-281, 290-292, 295, 310-313, 322-324, 327, 336-338, 341, 350, 363-365, 368, 377, 390-392, 395, 404-405, 414-415, 424-427, 438-439, 448-450, 453, 466-468, 471, 479, 495-499, 502 | 109->110, 109->111, 178->179, 178->180, 261->262, 261->263, 311->312, 311->313 |
| `modules/hr/contracts.py` | 3, 5-6, 8, 11-21, 24, 26-30 | 27->28, 27->29 |
| `modules/hr/domain/state_machine.py` | 64, 72-78, 89, 91, 94, 100, 105, 116, 118, 120-122, 127 | 63->64, 72->73, 72->74, 74->75, 74->76, 76->77, 76->78, 88->89, 90->91, 93->94, 96->100, 104->105, 115->116, 117->118, 119->120, 120->121, 120->122, 123->127 |
| `modules/hr/models.py` | 210, 241, 245, 362, 365, 388, 392 | 244->245, 387->388 |
| `modules/hr/schedule.py` | 1, 3, 8 | — |
| `modules/hr/selectors/appraisals.py` | 7-9, 11-16 | 8->9, 8->11, 12->13, 12->14, 14->15, 14->16 |
| `modules/hr/selectors/audit.py` | 7 | — |
| `modules/hr/selectors/claims.py` | 18, 22, 29 | 17->18, 21->22 |
| `modules/hr/selectors/configuration.py` | 7, 11 | — |
| `modules/hr/selectors/employees.py` | 7-10, 14 | 8->9, 8->10 |
| `modules/hr/selectors/leaves.py` | 21, 25, 29 | — |
| `modules/hr/selectors/notifications.py` | 7 | — |
| `modules/hr/services/appraisals.py` | 21-22, 26, 30-31, 37-38, 42-43, 46-47, 50-51, 55, 62, 70, 78, 81-82, 87, 89, 94-96, 101, 106-111, 121, 128-129, 137, 145, 149, 161-162, 167, 206, 234-235 | 22->26, 22->30, 37->38, 37->42, 42->43, 42->46, 77->78, 86->87, 88->89, 90->94, 96->101, 96->106, 128->129, 128->137, 144->145, 148->149, 195->220, 205->206, 233->234 |
| `modules/hr/services/authz.py` | 6, 8 | 5->6, 7->8 |
| `modules/hr/services/claims.py` | 27, 33, 38, 65-70, 75-84, 86-88, 92-93, 97-98, 100, 109, 116, 122, 127-132, 137-141, 145-146, 150-155, 161, 172, 178, 180, 187-189, 197, 207, 223-224, 229, 278-283, 287-293, 302, 309, 315, 328-330, 334, 338-339, 342, 351, 362 | 26->27, 32->33, 37->38, 66->67, 66->68, 69->70, 69->75, 79->80, 79->86, 86->87, 86->92, 87->88, 87->97, 92->93, 92->97, 97->98, 97->100, 139->140, 139->172, 187->188, 187->197, 280->281, 280->282, 282->283, 282->287, 287->288, 287->289, 330->334, 330->338, 338->339, 338->342 |
| `modules/hr/services/configuration.py` | 21, 28, 33-34, 40, 47, 61, 75, 79, 90, 99, 111, 118-120, 123, 132, 144, 148, 151-153 | 20->21, 27->28, 39->40, 46->47, 52->61, 74->75, 78->79, 119->120, 119->123, 151->152, 151->153 |
| `modules/hr/services/employees.py` | 25, 27-30, 35-36, 42-44, 49-51, 54-55, 57, 64, 71, 83, 86, 88, 108-113, 120 | 28->29, 28->30, 36->42, 36->43, 44->49, 44->50, 50->51, 50->54, 54->55, 54->57, 77->83, 85->86, 87->88, 91->108, 102->108, 109->110, 109->111 |
| `modules/hr/services/leaves.py` | 36, 41, 56-57, 64-71, 79, 108, 113, 118, 128, 146, 196, 226, 230 | 35->36, 40->41, 47->64, 66->67, 66->68, 107->108, 112->113, 117->118, 127->128, 145->146, 195->196, 225->226, 229->230 |
| `modules/hr/services/notifications.py` | 23, 42, 44-47, 50-51, 54, 59, 63-66, 74-76, 83-84 | 22->23, 46->47, 46->50, 54->59, 54->63, 65->66, 65->84, 74->75, 74->76 |
| `modules/hr/tasks.py` | 22, 27-28, 30-31, 34-39, 44-47, 54-55, 58, 63-68, 73-74, 76, 82-83, 99-104, 114-116, 123, 133, 135 | 30->31, 30->83, 34->35, 34->37, 38->39, 38->46, 65->66, 65->76, 98->99, 100->101, 100->102, 102->103, 102->104, 114->98, 114->115, 132->133, 134->135 |

## Tests added in this pass

- `modules/hr/tests/test_state_machine_edges.py`: valid and invalid transitions for all claim, appraisal, and leave state machines.
- `modules/hr/tests/test_service_edge_paths.py`: claim validation/routing/processing/integration, employee lifecycle and archive protection, appraisal workflow/errors, route/window validation, leave balance/submission/approval failure paths, notification publication, permissions, and immutable records.
- `modules/hr/tests/test_api_workflows.py`: authenticated HTTP flows across employee, claim, appraisal, workflow configuration, notice, leave-balance, and leave endpoints, plus not-found and serializer errors.
- `modules/hr/tests/test_selectors_contracts.py`: access-scope combinations, public employment DTOs, selector ordering, and scheduled-task registration.
- `modules/hr/tests/test_serializer_boundaries.py`: invalid appointment windows, Drive URLs, appraisal windows, balances, and route/notice payloads.
- `modules/hr/tests/test_notification_tasks.py`: email success and failure transitions, worker race deferral, batch bounds, and claim/leave reminder timing and deduplication.

## Final coverage

`pytest modules/hr --cov=modules/hr --cov-branch --cov-report=term-missing --cov-fail-under=90` passed **165 tests** and measured **100%** across 1,400 statements and 278 branch arcs. Every module file reports zero missing statements and zero partial branches.

`pytest modules/hr --cov=modules/hr/domain --cov-branch --cov-report=term-missing --cov-fail-under=95` passed **165 tests** and measured **100%** across 84 statements and all 44 branch arcs in `state_machine.py`.
