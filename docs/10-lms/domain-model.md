# LMS Domain Model Specification

## 1. Domain Entities & Aggregates

The LMS (Course Management) module is structured around the `Course` aggregate root, managing course workspaces, materials, announcements, assignments, submissions, and grades.

```
+---------------------------------------------------------------+
|                      Course (Aggregate Root)                  |
|  - id: int                                                    |
|  - code: str (CS3010)                                         |
|  - title: str                                                 |
|  - syllabus: text                                             |
|  - schedule: text                                             |
|  - instructor_id: int                                         |
|  - ta_can_post_announcements: bool                            |
+---------------------------------------------------------------+
       |                   |                   |           |
       v                   v                   v           v
[CourseMembership] [CourseMaterial] [Announcement] [Assignment]
                                                           |
                                                           v
                                                      [Submission]
                                                           |
                                                           v
                                                        [Grade]
                                                           |
                                                           v
                                                    [GradeAuditLog]
```

### Invariants & Database Constraints
1. **Course Code Uniqueness:** Course codes must be unique across the academic year.
2. **Membership Exclusivity:** A user cannot have duplicate memberships for the same course (`UniqueConstraint(course, user_id, role)`).
3. **Material Release Sanity:** `release_date >= created_at`.
4. **Assignment Constraints:**
   - `max_marks > 0`
   - `deadline > release_date` (when release_date is set)
5. **Submission Atomicity:** One submission per student per assignment (`UniqueConstraint(assignment, student_id)`).
6. **Grade Constraints:**
   - `0 <= score <= assignment.max_marks`
   - Only Faculty can transition Grade to `RELEASED`.
   - Post-release modification requires a non-empty audit `reason`.
