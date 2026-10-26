# Employee Leave Management (initial implementation slice)

This module is integrated into Fusion's Django app and API URL structure. It
uses Fusion authentication and the external employee identity (`user_id`), not
a local user table.

## Endpoints
- `GET /api/v1/elm/balances`
- `GET|POST /api/v1/elm/requests`
- `GET /api/v1/elm/requests/<id>`
- `POST /api/v1/elm/requests/<id>/actions`

## Important scope note
This is a starting slice, not a complete implementation of the supplied ELM
baseline. It records requests, balances, lifecycle actions, and substitute
responses. Before claiming specification compliance, implement and test the
full category-specific entitlement calculations, holiday/RH calendar checks,
overlap and continuous-day rules, substitute eligibility/overlap validation,
configured authority routing, cancellation and extension requests, year-end VL
conversion, notifications, permissions, and full frontend pages.

## Local integration
From the repository root:
1. Add `modules.elm` to `LOCAL_APPS` in `config/settings/base.py`.
2. Add `path("api/v1/elm/", include("modules.elm.api.urls")),` in `config/urls.py`.
3. Run `python manage.py makemigrations elm` and review the migration.
4. Run the backend tests and the project's checks before committing.
5. Configure the `elm` module grant and listed permission codes in Fusion IAM.
