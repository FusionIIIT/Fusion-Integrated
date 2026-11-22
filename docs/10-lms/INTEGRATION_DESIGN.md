# Fusion ERP LMS Course Management: Integration Design Document

## 1. Executive Summary & Fusion Platform Architecture Context

### High-Level Modular Monolith Design
The Fusion ERP LMS Course Management system is designed as a modular monolith, ensuring clear separation of concerns and maintainability. The architecture is divided into distinct layers to promote loose coupling and ease of maintenance.

### Separation of Concerns
- **API Layer**: Handles HTTP requests and responses.
- **Services Layer**: Contains business logic and orchestrates interactions between different services.
- **Selectors Layer**: Provides data retrieval mechanisms for the services layer.
- **Models Layer**: Manages database models and their relationships.
- **Domain Layer**: Houses core domain logic, ensuring zero dependencies on external frameworks like Django or DRF.

### Inter-Module Contract Rules
Modules communicate exclusively through defined contracts in `contracts.py`, ensuring a clean separation of concerns and preventing circular dependencies. This approach enhances testability and maintainability.

### Domain Layer Purity
The domain layer is kept free from any framework-specific dependencies, promoting a pure business logic environment that can be easily tested and maintained independently of the rest of the system.

## 2. Course Registration & Academic System Integration

### Current Fusion-Integrated State
The `modules/academics` module is currently not implemented within the LMS. This integration will be handled through an autonomous local projection, leveraging existing models in `modules/lms/models`.

### Autonomous Local Projection
- **Course Model**: Represents a course with attributes such as title, description, and start/end dates.
- **CourseMembership Model**: Tracks user enrollment status for each course.

### Adapter Pattern
An adapter pattern is employed to define an interface (`AcademicAdapter`) in `modules/lms/domain/adapters.py` and its contract definition in `contracts.py`. This allows the LMS to interact with external academic systems without direct dependencies, ensuring flexibility and ease of integration.

### Ingestion and Synchronization Capabilities

The system supports both ingestion from external registration tables and direct administrative seeding. This ensures that data can be synchronized or manually added as needed, maintaining a robust and flexible data management strategy.

### LMS as a Read‑Only Projection

The LMS **does not** act as the registration authority for courses or enrollments. All course, section, and membership data are sourced from the external academic system via an **AcademicAdapter**. The adapter provides a **projection** of the external data into the LMS data model, synchronizing records as needed but never creating or modifying the source of truth.

#### AcademicAdapter Interface

- Defined in `modules/lms/domain/adapters.py`.
- Contract (`contracts.py`) includes methods such as:
  - `fetch_course(course_id) -> CourseDTO`
  - `fetch_course_membership(course_id) -> List[MembershipDTO]`
  - `sync_courses()` – bulk pull from the external system.
- Implementations may use batch API calls, CSV imports, or direct database views, depending on the institution’s infrastructure.

#### Scope Limitations

- **No registration, add‑drop, or wait‑list functionality** resides in the LMS.
- All write‑operations for courses, sections, and enrollments are performed **outside** the LMS (e.g., in the university SIS) and are reflected in the LMS only through the adapter sync process.
- The LMS only stores **local copies** for fast read access and API exposure; these copies are considered **derived data** and must be refreshed regularly.

#### Integration Points

- The adapter is invoked by background tasks (Celery beat) and on‑demand API endpoints.
- Consistency guarantees are handled by the external system; the LMS logs any sync failures for operational monitoring.
The system supports both ingestion from external registration tables and direct administrative seeding. This ensures that data can be synchronized or manually added as needed, maintaining a robust and flexible data management strategy.

## 3. Identity and Directory Integration (IAM)

### Authentication via Fusion Auth
- **IamClient**: Utilizes `fusion_auth.client.IamClient` for authentication.
- **IamSession**: Manages session state post-authentication.

### User ID Convention
- **User IDs** are represented as integer values, inheriting from `UserScopedModel`. No direct foreign key relationships to Django’s `auth.User` model are allowed.

### User Profile and Directory Lookups
- **Batched Calls**: Utilizes `modules.directory.contracts.get_users(user_ids) -> dict[int, UserDTO]` for efficient user profile lookups.
- **Zero N+1 Query Guarantee**: Ensures that all necessary data is fetched in a single database query to prevent performance bottlenecks.

## 4. File Storage & Attachment Management

### Attachment Requirements
Attachments for `CourseMaterial` and `Submission` models are managed through the LMS storage service.

### Storage Adapter
- **Storage Service**: Defined in `modules/lms/services/storage.py`.
- **Storage Key Generation**: Uses SHA-256 content hash with 2-level directory sharding (`ab/cd/abcdef...`) to ensure unique and efficient file storage.
- **Security Constraints**:
  - Path Traversal Prevention: Ensures that filenames cannot contain paths or special characters.
  - File Size Limits: Enforces maximum file size limits for uploaded files.
  - MIME Type Validation: Validates the MIME type of uploaded files.

### Content Streaming
- **FileResponse**: Provides content streaming capabilities, ensuring that large files can be served efficiently without loading entire contents into memory.
- **X-Accel-Redirect Guarded by Course Permission Checks**: Ensures that only authorized users can access stored files.

## 5. Background Tasks & Scheduled Release Engine

### Celery Beat Schedule Configuration
- **Schedule Configuration**: Defined in `modules/lms/schedule.py`.
- **Integration in config/celery.py**: Configures the task to run every 60 seconds (`lms.process_scheduled_releases`).

### Atomic Database Locking
- **Concurrency Safety**: Ensures that database operations are atomic and prevent duplicate publication by using `select_for_update(skip_locked=True)`.

### Deterministic CLI Command
- **Manual Execution**: Provides a deterministic command `python manage.py lms_process_scheduled_releases` for manual execution, testing, and CI evaluation without requiring a permanently running Celery worker.

## 6. Frontend Architecture & Client Integration

### Registration in Client Registry
- **Code**: `"lms"`
- **Base Path**: `"/courses"`

### Route Configuration
Defined in `client/src/modules/lms/routes.tsx`.

### UI Views Using Mantine UI
- **Course Workspace Home**: `/courses/:courseId`
- **Materials Organizer & Viewer**: `/courses/:courseId/materials`
- **Announcement Feed**: `/courses/:courseId/announcements`
- **Assignment Workspace & Submission Portal**: `/courses/:courseId/assignments/:assignmentId`
- **Faculty/TA Grading Console**: `/courses/:courseId/assignments/:assignmentId/grading`

### Client API Client
Reuses `client/src/core/api` conventions for consistent and reliable API interactions.

## 7. Audit Logging & Governance Integration

### GradeAuditLog
- **Mandatory Tracking**: Implements a mandatory immutable tracking mechanism for grade modifications made after grade release (BR-LMS-019).
- **Logging Details**:
  - Assessor Identity: Tracks the identity of the user making the change.
  - Timestamp: Records the exact time of the modification.
  - Old Score: Logs the previous score before the change.
  - New Score: Logs the new score after the change.
  - Change Reason: Provides a reason for the grade change.

## 8. Technical Decision Classifications & Open Issues

### Explicit Labeling
- **Confirmed by Existing Repository**: [Confirmed by existing repository]
- **Required by Official Specification**: [Required by official specification]
- **Recommended Design**: [Recommended design]
- **Needs Instructor Clarification**: [NEEDS CLARIFICATION]

### Unresolved Issues (ISS-LMS-001 through ISS-LMS-006)
All 6 unresolved issues are strictly preserved as [NEEDS CLARIFICATION].

This document provides a comprehensive overview of the technical architecture and design decisions for the Fusion ERP LMS Course Management system, ensuring clarity and consistency in implementation.