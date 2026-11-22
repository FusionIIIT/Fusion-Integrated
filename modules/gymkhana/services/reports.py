from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.report import ClubEventReport
from modules.gymkhana.selectors.scoping import is_club_head


@transaction.atomic
def submit_event_report(
    *,
    club_id: int,
    acting_user_id: int,
    title: str,
    description: str,
    report_file,
) -> ClubEventReport:
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError("Club not found.", code="club_not_found")

    if not is_club_head(acting_user_id, club_id):
        raise PermissionDeniedError(
            "Only the applicable club coordinator or co-coordinator may submit club event reports.",
            code="not_club_head",
        )

    if not report_file:
        raise BadRequestError(
            "A club event report must include its report/details file.",
            code="missing_report_file",
        )

    return ClubEventReport.objects.create(
        club=club,
        title=title,
        description=description,
        report_file=report_file,
        submitted_by_id=acting_user_id,
    )
