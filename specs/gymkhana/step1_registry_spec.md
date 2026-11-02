# Gymkhana Step 1: Actors, Permissions & Navigation Specification

## 1. Actors & Roles
- **Student** (`student`): General student. Applies for club memberships, votes in active polls.
- **Club Head** (`club_coordinator`, `club_co_coordinator`): Student leaders of a club. Manages club, approves memberships, books venues, creates polls, submits budgets and event reports.
- **Student Admin** (`student_admin`): Creates clubs and confirms open clubs.
- **Club Faculty Councillor** (`faculty`, `Club Faculty Councillor`): Reviews submitted event reports.

## 2. Use Cases & Required Permissions
- `UC-GYM-001` (Create Club) -> Permission: `gymkhana.club.admin`
- `UC-GYM-002` (Book Session) & `UC-GYM-003` (Book Event) -> Permission: `gymkhana.booking.manage`
- `UC-GYM-004` (Apply Membership) -> Permission: `gymkhana.membership.apply`
- `UC-GYM-005` (Approve Membership) -> Permission: `gymkhana.membership.approve`
- `UC-GYM-006` (Create Poll) -> Permission: `gymkhana.poll.create`
- `UC-GYM-007` (Vote in Poll) -> Permission: `gymkhana.poll.vote`
- `UC-GYM-008` (Change Leadership) & General management -> Permission: `gymkhana.club.manage`
- `UC-GYM-009` (Request Budget) -> Permission: `gymkhana.budget.submit`
- `UC-GYM-010` (Submit Report) -> Permission: `gymkhana.report.submit`
- `UC-GYM-011` (Confirm Club) -> Permission: `gymkhana.club.admin`
- `UC-GYM-012` (Review Report) -> Permission: `gymkhana.report.review`
- General viewing -> Permission: `gymkhana.club.view`

## 3. Navigation Links Needed
- Browse Clubs (`/gymkhana`, icon: `Users`, perm: `gymkhana.club.view`)
- My Memberships (`/gymkhana/memberships`, icon: `UserCheck`, perm: `gymkhana.membership.apply`)
- Voting Polls (`/gymkhana/polls`, icon: `Checks`, perm: `gymkhana.poll.vote`)
- Manage Club (`/gymkhana/manage`, icon: `Gear`, perm: `gymkhana.club.manage`)
- Venue Bookings (`/gymkhana/bookings`, icon: `CalendarBlank`, perm: `gymkhana.booking.manage`)
- Budget Requests (`/gymkhana/budget`, icon: `CurrencyDollar`, perm: `gymkhana.budget.submit`)
- Event Reports (`/gymkhana/reports`, icon: `ClipboardText`, perm: `gymkhana.report.submit`)
- Club Approvals (`/gymkhana/admin/clubs`, icon: `ShieldCheck`, perm: `gymkhana.club.admin`)
- Review Reports (`/gymkhana/faculty/reports`, icon: `FileSearch`, perm: `gymkhana.report.review`)
