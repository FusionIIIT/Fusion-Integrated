"""Post-resolution feedback and incident reporting services (UC-IWD-141, BR-IWD-017)."""

from modules.iwd.models import Complaint, ComplaintFeedback, DecisionAuditTrail


class UnresolvedFeedbackSubmissionError(Exception):
    """Raised when feedback is submitted on a complaint that has not yet been resolved."""


def submit_feedback(
    complaint_id: int,
    employee_user_id: int,
    rating: int,
    comments: str = "",
    post_repair_issue: bool = False,
    post_repair_remarks: str = "",
) -> ComplaintFeedback:
    """Submit post-resolution rating, feedback, and post-repair issues (BR-IWD-017)."""
    complaint = Complaint.objects.get(id=complaint_id)
    if not complaint.is_resolved:
        msg = "BR-IWD-017: Feedback is available only after physical verification."
        raise UnresolvedFeedbackSubmissionError(msg)

    feedback = ComplaintFeedback.objects.create(
        complaint=complaint,
        employee_user_id=employee_user_id,
        rating=rating,
        comments=comments,
        post_repair_issue=post_repair_issue,
        post_repair_remarks=post_repair_remarks,
    )

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=employee_user_id,
        actor_role="Institute Employee",
        action="submit_feedback",
        previous_state=complaint.status,
        new_state=complaint.status,
        remarks=f"Rating: {rating}/5. Post-repair issue: {post_repair_issue}",
    )
    return feedback
