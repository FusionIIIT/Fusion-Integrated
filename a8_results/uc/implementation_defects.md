# UC implementation discrepancies

The following five frozen UC cases failed in the final isolated pytest run. Production code was not changed.

| Test ID | Observed behavior | Frozen expected result |
|---|---|---|
| `TC-UC-003` | The role assignment request returned HTTP 201 and created a replacement assignment. | Reject a conflicting active-role assignment and leave the existing assignment unchanged. |
| `TC-UC-046` | A Student's feedback-list request returned HTTP 200 (the endpoint scopes results to that Student). | Reject access to the Caretaker/Warden feedback review view. |
| `TC-UC-065` | Submitting the specified `Yes` response returned HTTP 409; no response was recorded. | Record the Student's explicit Yes response while the survey is open. |
| `TC-UC-066` | Submitting the specified `No` response returned HTTP 409; no response was recorded. | Record the Student's explicit No response while the survey is open. |
| `TC-UC-078` | Approving without a charge amount returned HTTP 409; the request remained Requested. | Record Approved status and trigger the applicable decision notification. |

These are test-observed mismatches against the frozen design. They are not corrected here. The exact traceback and response details are retained in `pytest.log` and `junit.xml`.
