# 10-lms/ARCHITECTURE_PLAN.md — LMS Course Management Architecture Plan

## 1. Architectural Overview & Fusion Integration

- **Modular Monolith Pattern**: Adhering to Fusion ERP platform standards, the architecture follows a modular monolith pattern.
- **Layering**: The system is structured in layers: API -> Services -> Selectors -> Models -> Domain.
- **Enforcement by .importlinter**: The domain layer must be pure Python with zero Django/DRF dependencies. This ensures clean separation of concerns and maintainability.
- **Cross-module Boundaries**: Communication between modules is strictly via `contracts.py` to enforce clear interfaces.

## 2. Planned Domain Entities & Models

### Modules/lms/models/

- **Course**
  - Fields: `code`, `title`, `description`, `syllabus`, `schedule`, `academic_year`, `semester`, `is_active`

- **CourseMembership**
  - Fields: `course_id`, `user_id`, `role` (student, instructor, ta, observer), `is_active`

- **ModuleSection**
  - Fields: `course`, `title`, `order`, `is_published`

- **CourseMaterial**
  - Fields: `section`, `title`, `kind` (file, link, note), `content`, `file_path`, `release_date`, `is_published`

- **Announcement**
  - Fields: `course`, `title`, `content`, `author_user_id`, `author_role`, `created_at`

- **Assignment**
  - Fields: `course`, `title`, `instructions`, `submission_type` (file, text, link), `points_possible`, `due_date`, `release_date`, `status` (draft, published)

- **Submission**
  - Fields: `assignment`, `student_user_id`, `submission_type`, `content`, `file_path`, `submitted_at`, `status` (submitted, late)

- **Grade**
  - Fields: `submission`, `points_awarded`, `feedback`, `assessor_user_id`, `assessor_role`, `status` (draft, released), `released_at`

- **GradeAuditLog**
  - Fields: `grade`, `assessor_user_id`, `previous_points`, `new_points`, `reason`, `changed_at`

- **ScheduledRelease**
  - Fields: `material_id` (nullable FK to CourseMaterial), `assignment_id` (nullable FK to Assignment), `scheduled_date`, `processed_at`, `status`, `error_message` (CHECK constraint: exactly one non-null target)

## 3. Role-Based Access Control & Permission Architecture

### Actors
- Student
- Faculty
- Teaching Assistant (TA)
- Observer

### Scoped Selectors
- Ensures that the principal cannot read or write outside of their assigned courses, maintaining data integrity and security.

## 4. Service & State Machine Lifecycle

### Assignment Lifecycle
- **States**: Draft -> Published (Immediate or Scheduled)

### Submission Lifecycle
- **States**: Pending -> Submitted / Late

### Grade Lifecycle
- **States**: Draft -> Released (Faculty release only)

## 5. Background Processing & Scheduled Release

### Celery Beat Task
- **Task Name**: UC-LMS-015
- Scans for materials and assignments with scheduled release dates.

### CLI Management Command
- Provides a deterministic, synchronous method to execute the release of content.

## 6. Frontend Architecture (client/src/modules/lms/)

### Technology Stack
- React 18
- TypeScript
- Mantine UI components

### Registration in Client
- `client/src/app/registry.ts` with `basePath: /courses`

### Dedicated Views
- **Course Home**
- **Materials Organizer**
- **Assignment View/Submit**
- **Grading Console**

## 7. Detailed Architecture Specifications
- **Domain Modeling & Schema**: See [DOMAIN_MODEL.md](file:///home/abhi/Documents/Fusion/Fusion-Integrated/docs/10-lms/DOMAIN_MODEL.md) for entity schemas, Mermaid ER diagram, indexes, constraints, and CFR/AFR traceability.
- **Workflow & Lifecycle Design**: See [WORKFLOW_DESIGN.md](file:///home/abhi/Documents/Fusion/Fusion-Integrated/docs/10-lms/WORKFLOW_DESIGN.md) for state-transition tables, Basis Workflows (BW-LMS-01..05), Composite Workflows (CW-LMS-01..02), and policy handling.
- **Subsystem & Integration Design**: See [INTEGRATION_DESIGN.md](file:///home/abhi/Documents/Fusion/Fusion-Integrated/docs/10-lms/INTEGRATION_DESIGN.md) for Academic adapter, IAM lookups, file storage hashing, Celery Beat scheduling, and client routing.
- **Unresolved Policy Issues**: See [OPEN_ISSUES.md](file:///home/abhi/Documents/Fusion/Fusion-Integrated/docs/10-lms/OPEN_ISSUES.md) where all six policy issues (ISS-LMS-001 through ISS-LMS-006) remain strictly in status `[NEEDS CLARIFICATION]` with zero invented defaults.
