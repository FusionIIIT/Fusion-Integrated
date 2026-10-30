# Leave Management System (ELM)

## Overview

This repository contains an implementation of a leave management system using Django as the backend framework and React for the frontend. The system is designed to handle employee leave applications, task scheduling, and configuration settings.

## File Structure

- **modules/leave_elm**: Contains the main application logic.
  - `apps.py`: Configures the Django app.
  - `models.py`: Defines the database models used by the application.
  - `services`: Directory containing services for handling various functionalities like leaving, tasks, and configurations.
    - `actions.py`, `applications.py`, `events.py`, `queries.py`
  - `registry.py`: Manages navigation items, permissions, role grants, and system permissions.
  - `api`**: Directory containing views and serializers for API endpoints.
    - `urls.py`: URL routing configuration.
    - `views.py`, `serializers.py`
- **client/src/modules/leave_elm**: Contains the frontend components and routes.
  - `pages`: Directory with individual page components.
    - `MyLeavePage.tsx`, `LeaveTasksPage.tsx`, `LeaveAdminPage.tsx`
  - `api.ts`: Client-side API interactions using the supplied Axios client.
  - `types.ts`: TypeScript type definitions for frontend interfaces.

## Mechanical Integration Setup

1. **Django Backend**:
   - The backend uses the supplied Fusion settings and database configuration. SQLite was used only in temporary build checks. Models include `LeaveApplication`, `LeaveTask`, `LeavePolicy`, and `LeaveCalendar`.
   - Django migrations (`manage.py makemigrations`) are used to create tables based on these models.
   - The generated API is mounted at `/api/v1/leave/` through Django REST Framework.
   - Authentication uses the supplied Fusion Principal and access-control interfaces. Permission behavior has not been audited.

2. **React Frontend**:
   - The frontend is set up using Vite. It interacts with the backend via the supplied shared Axios client to handle CRUD operations and other functionalities.
   - Components like `MyLeavePage`, `LeaveTasksPage`, and `LeaveAdminPage` manage state and render data fetched from the backend.
   - Navigation is handled by React Router, ensuring smooth routing between different pages of the application.

3. **Integration Commands**:
   - To run the development server: `cd client && npm run dev`
   - To build the production version: `cd client && npm run build`

4. **Database Migration Verification**:
   - The isolated ELM migration installed successfully. The full temporary SQLite migration failed in existing Placement0009 because `document_profile_idx` was missing. Actual PostgreSQL migration and workflow behavior were not verified. See the evidence directory for exact commands and results.

5. **Module Registration**:
   - Run `python manage.py seed_modules` to register declared module and sidebar rows. The generated permission grants are retained; their correctness is unverified.

## Workflow Correctness Unverified

- No functional, BR, security, missing-requirement, maintainability, or optimization review has been performed on this implementation.
- Bugs may remain due to incomplete code, incorrect logic, or integration issues not verified during testing.
- The system does not claim to be fully operational; it is a work-in-progress with potential bugs and improvements needed.

For detailed logs and exact check commands, refer to the evidence directory at `../../docs/08-delivery/elm-qwen-trial`.

---

This README provides an overview of the project structure, integration setup, and workflow correctness unverified for the Leave Management System (ELM).

## Registered routes

Backend paths under `/api/v1/leave/`: `applications`, `balances`, `tasks`, `applications/<id>/action`, `configuration`, `records`. Frontend paths: `/leave/mine`, `/leave/queue`, `/leave/admin`. Endpoint behavior is unverified.
