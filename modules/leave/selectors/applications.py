from django.db.models import Q

def get_active_overlapping_leaves(start_date, end_date, user_id, status__in):
    """
    Retrieve active leaves that overlap with the given date range for a specific user and status.

    :param start_date: The start date of the range.
    :param end_date: The end date of the range.
    :param user_id: The ID of the user to filter by.
    :param status__in: A list of statuses to filter by.
    :return: QuerySet containing overlapping leaves.
    """
    overlap_condition = Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    query_set = Leave.objects.filter(
        overlap_condition,
        user_id=user_id,
        status__in=status__in
    )
    return query_set