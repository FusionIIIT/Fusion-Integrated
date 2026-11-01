# Complaint Management System (complaint_cms)

## Overview

The **Complaint Management System** is designed to streamline complaint handling processes within an institution. It provides various functionalities such as viewing own complaints, managing task queues, reviewing and resolving complaints, escalating issues, configuring settings, and managing records. The system integrates with existing Fusion Auth, configuration, and database systems.

## File Structure

- `registry.py`: Contains metadata about the module, including its name, label, base path, navigation section, icon, status, sort order, navigation items, permissions, role grants, and system permissions.
  
- `api/urls.py`: Defines URL patterns for API endpoints related to complaints, tasks, notifications, complaint actions, configuration management, and record management.

## Route Paths

### Frontend Routes

- `/complaints/mine`: View all complaints created by the logged-in user.
- `/complaints/queue`: View the task queue of complaints awaiting review.
- `/complaints/admin`: Manage configuration settings and record management.

### Backend Routes

- `/api/v1/complaints/`: Provides access to various API endpoints for managing complaints, tasks, notifications, and other data.

## Mechanical Integration Setup

To integrate this system:

1. **Run Migrations**: Execute `python manage.py migrate` to apply any necessary database migrations.
2. **Seed Modules**: Use `seed_modules` to populate the database with initial data if needed.
3. **Build Client**: Run `client npm run build` to compile the frontend assets.

## Phase 1 One-Shot Local LLM Trial

This is a one-shot local LLM trial where only build/structural checks are performed. Workflow correctness has not been verified at this stage.

## Evidence Directory

For logs and check outputs, refer to the evidence directory: ../../docs/08-delivery/cms-qwen-trial
