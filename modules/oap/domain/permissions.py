"""OAP Permission constants.

Pure Python module defining permission codes for role-based access control (OA-BR-01, CFR-OAP-001).
Format: oap.<domain>.<action>
"""

# Student permissions
P_STUDENT_LEAVE_APPLY = "oap.leave.apply"
P_STUDENT_LEAVE_VIEW = "oap.leave.view"
P_STUDENT_BONAFIDE_REQUEST = "oap.bonafide.request"
P_STUDENT_BONAFIDE_VIEW = "oap.bonafide.view"
P_STUDENT_BONAFIDE_DOWNLOAD = "oap.bonafide.download"
P_STUDENT_NODUES_INITIATE = "oap.nodues.initiate"
P_STUDENT_NODUES_VIEW = "oap.nodues.view"
P_STUDENT_NODUES_DOWNLOAD = "oap.nodues.download"
P_STUDENT_ASSISTANTSHIP_SUBMIT = "oap.assistantship.submit"
P_STUDENT_ASSISTANTSHIP_VIEW = "oap.assistantship.view"
P_STUDENT_SEMINAR_REQUEST = "oap.seminar.request"
P_STUDENT_SEMINAR_VIEW = "oap.seminar.view"

# Faculty permissions
P_FACULTY_SEMINAR_VIEW = "oap.seminar.view"

# Supervisor permissions
P_SUPERVISOR_VERIFY_THESIS = "oap.assistantship.verify_thesis"
P_SUPERVISOR_VERIFY_TA = "oap.assistantship.verify_ta"

# Head of Department permissions
P_HOD_LEAVE_DECIDE = "oap.leave.decide"
P_HOD_LEAVE_VIEW_DEPT = "oap.leave.view_dept"
P_HOD_ASSISTANTSHIP_DECIDE = "oap.assistantship.decide"

# Academic Administrator permissions
P_ACAD_ADMIN_BONAFIDE_DECIDE = "oap.bonafide.decide"
P_ACAD_ADMIN_NODUES_FINALIZE = "oap.nodues.finalize"
P_ACAD_ADMIN_ASSISTANTSHIP_DISBURSE = "oap.assistantship.disburse"

# Department Administrator permissions
P_DEPT_ADMIN_ASSIGNMENT_MANAGE = "oap.assignment.manage"
P_DEPT_ADMIN_SEMINAR_SCHEDULE = "oap.seminar.schedule"
P_DEPT_ADMIN_ASSISTANTSHIP_REVIEW = "oap.assistantship.dept_review"

# 7 Mandatory No-Dues Clearance Authorities
P_NODUES_VERIFY = "oap.nodues.verify"

# Notifications
P_NOTIFICATION_VIEW = "oap.notification.view"
