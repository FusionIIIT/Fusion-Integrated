"""The configured venue list (BR-GYM-020), versioned by effective date and never edited."""
from django.db import models
from django.db.models.functions import Lower


class VenueList(models.Model):
    effective_from = models.DateTimeField()
    created_by_label = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_venue_list"
        constraints = [
            models.UniqueConstraint(fields=["effective_from"],
                                    name="gym_venuelist_effective_unique"),
        ]

    def __str__(self) -> str:
        return f"venues from {self.effective_from:%Y-%m-%d}"

class Venue(models.Model):
    venue_list = models.ForeignKey(VenueList, on_delete=models.PROTECT,
                                   related_name="venues")
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "gymkhana_venue"
        constraints = [
            models.UniqueConstraint("venue_list", Lower("name"),
                                    name="gym_venue_unique_in_list"),
        ]

    def __str__(self) -> str:
        return self.name
