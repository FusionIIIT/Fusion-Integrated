# LMS (Course Management) State Machines

**Module Code**: `lms`

---

## 1. Course Material Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft : Faculty creates draft material
    Draft --> Published : Faculty publishes immediately
    Draft --> Scheduled : Faculty sets future release date
    Scheduled --> Published : Celery beat task or arrival of release_at
    Published --> [*]
```

---

## 2. Course Assignment Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft : Faculty drafts assignment
    Draft --> Published : Faculty publishes assignment
    Draft --> Scheduled : Faculty configures future release date
    Scheduled --> Published : Release time arrives
    Published --> [*]
```

---

## 3. Student Submission Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Submitted : Student submits assignment before cutoff
    Submitted --> Evaluated : Faculty or TA records score
    Evaluated --> Evaluated : Regrade or feedback update
```

---

## 4. Evaluation and Grade Release Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft : Grader evaluates submission (hidden from student)
    Draft --> Released : Faculty triggers grade release service
    Released --> Released : Faculty modifies released grade (creates GradeAuditLog)
```
