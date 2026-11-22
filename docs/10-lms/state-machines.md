# LMS State Machines Specification

This document formally specifies the declarative finite state machines operating within the LMS module.

---

## 1. Course Material Lifecycle (`CM-SM`)

```
      +--------------+
      |    DRAFT     |<-----------------+
      +--------------+                  |
        |          |                    |
SCHEDULE|          |PUBLISH             |CANCEL_SCHEDULE
        v          v                    |
+-------------+  +---------------+      |
|  SCHEDULED  |  |   PUBLISHED   |------+
+-------------+  +---------------+
        | AUTO_RELEASE   |
        +-------->-------+
                         | ARCHIVE
                         v
                 +---------------+
                 |   ARCHIVED    |
                 +---------------+
```

### Transition Table:
- `(DRAFT, SCHEDULE, Faculty) -> SCHEDULED` [Condition: `release_date > now`]
- `(DRAFT, PUBLISH, Faculty) -> PUBLISHED` [Condition: `release_date <= now` or `None`]
- `(SCHEDULED, AUTO_RELEASE, System) -> PUBLISHED` [Condition: `now >= release_date`]
- `(SCHEDULED, CANCEL_SCHEDULE, Faculty) -> DRAFT`
- `(PUBLISHED, ARCHIVE, Faculty) -> ARCHIVED`

---

## 2. Assignment Lifecycle (`AS-SM`)

```
      +--------------+
      |    DRAFT     |
      +--------------+
        |          |
SCHEDULE|          |PUBLISH
        v          v
+-------------+  +---------------+
|  SCHEDULED  |  |   PUBLISHED   |
+-------------+  +---------------+
        | AUTO_RELEASE   |
        +-------->-------+
                         | CLOSE (now >= deadline)
                         v
                 +---------------+
                 |    CLOSED     |
                 +---------------+
```

### Transition Table:
- `(DRAFT, SCHEDULE, Faculty) -> SCHEDULED` [Condition: `release_date > now`, `deadline > release_date`]
- `(DRAFT, PUBLISH, Faculty) -> PUBLISHED` [Condition: `deadline > now`]
- `(SCHEDULED, AUTO_RELEASE, System) -> PUBLISHED` [Condition: `now >= release_date`]
- `(PUBLISHED, CLOSE, System/Faculty) -> CLOSED` [Condition: `now >= deadline`]

---

## 3. Submission & Grading Lifecycle (`GR-SM`)

```
 [Student SUBMIT]
        |
        v
+---------------+
|   SUBMITTED   |
+---------------+
        |
        | GRADE_DRAFT (Faculty/TA)
        v
+---------------+
|    GRADED     | <------+ (UPDATE_DRAFT)
+---------------+        |
        |                |
        | RELEASE (Faculty only)
        v
+---------------+
|   RETURNED    | (AMEND_GRADE + Audit Log)
+---------------+
```

### Transition Table:
- `(None, SUBMIT, Student) -> SUBMITTED` [Condition: `assignment.status == PUBLISHED`, `now <= deadline`]
- `(SUBMITTED, GRADE_DRAFT, Faculty/TA) -> GRADED` [Condition: `0 <= score <= max_marks`]
- `(GRADED, UPDATE_DRAFT, Faculty/TA) -> GRADED` [Condition: `grade.status == DRAFT`]
- `(GRADED, RELEASE, Faculty) -> RETURNED` [Condition: Faculty designation required]
- `(RETURNED, AMEND_GRADE, Faculty) -> RETURNED` [Condition: mandatory audit reason recorded]
