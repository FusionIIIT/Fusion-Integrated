# Round 1 gate reruns

The separate verification checkout at `/private/tmp/swe-lab9-review-gates` was clean and pinned to `8a550b4d3a2f67102bb3bebf44f30d93cf667aea`. These commands were run on that checkout alongside the independent static review. They do not constitute an official reviewer scorecard.

| Command | Result |
| --- | --- |
| `make check` | Passed. The full backend suite reached 100% with no failures. |
| `make check-client` | Passed. Seven files and 40 tests passed, and the client built. |
| `make e2e` | 11 passed in 5.5 seconds. |
| `pytest modules/department --cov=modules/department --cov-branch --cov-report=term-missing --cov-fail-under=90` | 21 passed. Coverage 92.60%. |
| `pytest modules/department --cov=modules/department/domain --cov-branch --cov-report=term-missing --cov-fail-under=95` | 21 passed. Coverage 100.00%. |
| `manage.py check --deploy --fail-level WARNING` with local production-shaped settings | Passed. No issues, two silenced by the repository settings. |

The local IAM full academic sync reported missing public fixture tables. The identity rows needed for the browser suite were available and all browser tests passed. The clean checkout, user branch, and remote branch were left unchanged.
