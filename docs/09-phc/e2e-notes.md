# PHC end-to-end notes

## Happy path

`client/e2e/phc.spec.ts` covers two PHC flows. The happy-path test stubs `GET /api/v1/me` with a session that grants `phc.schedule.view` and the `phc` module, and stubs `GET /api/v1/phc/schedule` with an empty schedule payload. It opens `/phc/schedule`, checks the "Doctor Schedule" heading and the explicit "No published schedule yet" empty state, and asserts that no console or page error was raised. No backend is needed.

The second test is a regression case for the record download. It stubs the patient session and the records/prescriptions lists, opens `/phc/records`, clicks "View", and asserts the drawer renders the visit notes and medicine. It then stubs a real `application/pdf` response with `Content-Disposition`, clicks "Download PDF" and asserts the saved filename. This guards the contract: the download endpoint returns PDF bytes, so the client buffers it as a blob rather than parsing it as JSON.

The session stub follows the client's auth contract: the app reads permissions and module grants from `/api/v1/me`, and the session cookie is paired with the CSRF token returned there.

Run it from `client/`:

```sh
npm run test:e2e
```

`client/playwright.config.ts` starts the Vite dev server on port 4173 and reuses an existing server outside CI. `npx playwright test --list` confirms the spec is discovered without starting a browser.

## Accessibility and keyboard check

The same test runs `AxeBuilder` with the `wcag2a` and `wcag2aa` tags and requires zero violations. It also presses Tab after focusing the page and asserts that the Notifications control receives focus, so keyboard navigation into the shell's controls is covered. The test uses a 1920x1080 viewport so the expanded sidebar is exercised.

The initial axe run exposed four WCAG AA contrast failures in shared shell components; the dimmed text colours and the red Logout control were darkened, and the axe assertion now passes.

## Load test: N/A

PHC has no predictable peak event. Schedule publication and advisory publishing are small staff actions, reimbursement claims are submitted individually without a submission deadline, and requisitions, inventory adjustments and ambulance logs follow ordinary working-day traffic. Unlike placement, there is no deadline-driven mass submission to size for, so a load test would not exercise a realistic risk. Server-side behaviour is covered by the module's Python suite instead.
