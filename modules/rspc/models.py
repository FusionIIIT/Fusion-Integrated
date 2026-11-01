from django.db import models
from core.db.mixins import TimeStampedModel

# -- ResearchProposal --------------------------------------------------------
class ResearchProposal(TimeStampedModel):
    STATUS = [
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("dept_recommended", "Dept. Recommended"),
        ("dept_not_recommended", "Dept. Not Recommended"),
        ("admin_verified", "Admin Verified"),
        ("not_eligible", "Not Eligible"),
        ("approved", "Approved"),
        ("dean_not_approved", "Dean Not Approved"),
        ("director_not_approved", "Director Not Approved"),
        ("forwarded_to_director", "Forwarded to Director"),
    ]

    title = models.CharField(max_length=255)
    objectives = models.TextField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    funding_agency = models.TextField(null=True, blank=True)
    resource_requirements = models.TextField(null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    pi_id = models.IntegerField()
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    class Meta:
        db_table = "rspc_research_proposal"
        indexes = [
            models.Index(fields=["status"], name="research_proposal_status_idx"),
        ]

    def __str__(self) -> str:
        return f"prop#{self.pk} {self.title} {self.status}"


# -- ProposalDecision --------------------------------------------------------
class ProposalDecision(models.Model):
    proposal = models.ForeignKey(ResearchProposal, on_delete=models.CASCADE,
                                related_name="decisions")
    stage = models.CharField(max_length=50)  # "HoD", "RSPC Admin", "Dean-RSPC", "Director"
    actor_id = models.IntegerField(null=True, blank=True)  # Fusion user id
    outcome = models.CharField(max_length=24)  # "recommended" or "not eligible"
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_proposal_decision"
        indexes = [models.Index(fields=["proposal", "stage", "decided_at"],
                                name="decision_proposal_idx")]

    def __str__(self) -> str:
        return f"prop#{self.proposal_id} {self.stage} {self.outcome}"