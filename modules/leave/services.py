from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import (
    LeaveCategory, HalfDayType, SubstituteStatus, ApplicationStatus,
    ResumptionType, UserRole, LeavePolicy, HolidayCalendar, AcademicCalendarVacation,
    LeaveBalance, LeaveApplication, SubstituteRequest, LeaveActionHistory,
    ResumptionRequest, OfflineLeaveRecord, SLAConfig
)


class LeaveValidationError(Exception):
    pass


class ELMService:
    @staticmethod
    def calculate_requested_days(category, start_date, end_date, half_day_type=HalfDayType.NONE):
        """Calculate leave duration adhering to continuous vs non-continuous rules."""
        if start_date > end_date:
            raise LeaveValidationError("Start date cannot be after end date.")

        if half_day_type != HalfDayType.NONE:
            if start_date != end_date:
                raise LeaveValidationError("Half-day leave can only be requested for a single date.")
            if category != LeaveCategory.CL:
                raise LeaveValidationError("Half-day leave is only permissible for Casual Leave (CL).")
            return Decimal("0.5")

        policy = LeavePolicy.objects.filter(category=category).first()
        is_continuous = policy.is_continuous_counting if policy else (category in [LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL])

        if is_continuous:
            # Continuous counting including weekends and holidays
            delta_days = (end_date - start_date).days + 1
            return Decimal(str(delta_days))
        else:
            # Non-continuous counting (exclude holidays and weekends)
            curr = start_date
            count = 0
            holidays = set(HolidayCalendar.objects.filter(is_published=True).values_list("date", flat=True))

            while curr <= end_date:
                is_weekend = curr.weekday() in (5, 6) # Saturday, Sunday
                is_holiday = curr in holidays
                if not (is_weekend or is_holiday):
                    count += 1
                curr += timedelta(days=1)
            return Decimal(str(count))

    @staticmethod
    def validate_eligibility_and_balance(user_id, user_category, category, start_date, end_date, requested_days, half_day_type):
        """Validate category eligibility, balance availability, calendar conditions, and impermissible overlap."""
        # 1. Category-specific policy checks
        if category == LeaveCategory.RH:
            if start_date != end_date:
                raise LeaveValidationError("Restricted Holiday (RH) must be taken on a single specific RH date.")
            rh_exists = HolidayCalendar.objects.filter(
                date=start_date,
                holiday_type=HolidayCalendar.Type.RESTRICTED_HOLIDAY,
                is_published=True
            ).exists()
            if not rh_exists:
                raise LeaveValidationError(f"Date {start_date} is not configured as a published Restricted Holiday (RH).")

        if category == LeaveCategory.VL:
            if user_category != "FACULTY":
                raise LeaveValidationError("Vacation Leave (VL) is only accessible to Faculty members.")
            vacation_valid = AcademicCalendarVacation.objects.filter(
                start_date__lte=start_date,
                end_date__gte=end_date
            ).exists()
            if not vacation_valid:
                raise LeaveValidationError("Vacation Leave (VL) can only be availed during published Academic Calendar vacation periods.")

        if category == LeaveCategory.EL and user_category == "FACULTY":
            # Faculty cannot directly apply EL except converted from VL
            pass

        # 2. Check balance
        year = start_date.year
        balance_obj = LeaveBalance.objects.filter(user_id=user_id, category=category, year=year).first()
        available = balance_obj.balance if balance_obj else Decimal("0.0")

        if available < requested_days:
            raise LeaveValidationError(
                f"Insufficient balance for {category}. Available: {available} days, Requested: {requested_days} days."
            )

        # 3. Impermissible Overlap Check
        active_statuses = [
            ApplicationStatus.AWAITING_SUBSTITUTE,
            ApplicationStatus.AWAITING_UNIT_HEAD,
            ApplicationStatus.AWAITING_ESTABLISHMENT,
            ApplicationStatus.AWAITING_FINAL_SANCTION,
            ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
            ApplicationStatus.APPROVED,
            ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD,
            ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT,
            ApplicationStatus.CANCELLATION_PENDING_FINAL,
            ApplicationStatus.EXTENSION_PENDING_FINAL,
        ]
        
        overlapping_apps = LeaveApplication.objects.filter(
            applicant_id=user_id,
            status__in=active_statuses,
            start_date__lte=end_date,
            end_date__gte=start_date
        )

        for app in overlapping_apps:
            # Check half-day CL non-overlapping exception on same date
            if (app.start_date == start_date == end_date == app.end_date and 
                app.category == LeaveCategory.CL and category == LeaveCategory.CL and
                app.half_day_type != HalfDayType.NONE and half_day_type != HalfDayType.NONE and
                app.half_day_type != half_day_type):
                continue # First-half and second-half on same date do not overlap
            raise LeaveValidationError(f"Requested period overlaps with active application #{app.id} ({app.start_date} to {app.end_date}).")

    @staticmethod
    def validate_substitute(substitute_id, applicant_id, start_date, end_date):
        """Validate substitute eligibility and absence of overlapping leave."""
        if not substitute_id:
            return
        if substitute_id == applicant_id:
            raise LeaveValidationError("Applicant cannot be nominated as their own substitute.")

        sub_active_statuses = [
            ApplicationStatus.AWAITING_SUBSTITUTE,
            ApplicationStatus.AWAITING_UNIT_HEAD,
            ApplicationStatus.AWAITING_ESTABLISHMENT,
            ApplicationStatus.AWAITING_FINAL_SANCTION,
            ApplicationStatus.APPROVED
        ]
        sub_overlap = LeaveApplication.objects.filter(
            applicant_id=substitute_id,
            status__in=sub_active_statuses,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exists()

        if sub_overlap:
            raise LeaveValidationError("Nominated substitute has active pending or approved leave during this responsibility period.")

    @classmethod
    @transaction.atomic
    def apply_for_leave(cls, applicant_id, applicant_name, applicant_category, applicant_role, department,
                       category, start_date, end_date, purpose, half_day_type=HalfDayType.NONE,
                       is_station_leave=False, station_address="", out_of_station_start=None, out_of_station_end=None,
                       emergency_contact="", substitute_id=None, substitute_name=None):
        """UC-001: Submit a new leave application."""
        requested_days = cls.calculate_requested_days(category, start_date, end_date, half_day_type)
        cls.validate_eligibility_and_balance(applicant_id, applicant_category, category, start_date, end_date, requested_days, half_day_type)

        substitute_status = SubstituteStatus.NOT_REQUIRED
        if substitute_id:
            cls.validate_substitute(substitute_id, applicant_id, start_date, end_date)
            substitute_status = SubstituteStatus.AWAITING_RESPONSE

        # Determine initial status & routing
        if substitute_status == SubstituteStatus.AWAITING_RESPONSE:
            initial_status = ApplicationStatus.AWAITING_SUBSTITUTE
        elif applicant_role == UserRole.DIRECTOR:
            initial_status = ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION
        else:
            initial_status = ApplicationStatus.AWAITING_UNIT_HEAD

        app = LeaveApplication.objects.create(
            applicant_id=applicant_id,
            applicant_name=applicant_name,
            applicant_category=applicant_category,
            applicant_role=applicant_role,
            department=department,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day_type=half_day_type,
            requested_days=requested_days,
            purpose=purpose,
            is_station_leave=is_station_leave,
            station_address=station_address,
            out_of_station_start=out_of_station_start,
            out_of_station_end=out_of_station_end,
            emergency_contact=emergency_contact,
            substitute_id=substitute_id,
            substitute_name=substitute_name,
            substitute_status=substitute_status,
            status=initial_status,
            current_authority_role="SUBSTITUTE" if substitute_status == SubstituteStatus.AWAITING_RESPONSE else ("DIRECTOR" if applicant_role == UserRole.DIRECTOR else "UNIT_HEAD")
        )

        if substitute_id:
            SubstituteRequest.objects.create(
                application=app,
                substitute_id=substitute_id,
                substitute_name=substitute_name or substitute_id,
                status="PENDING"
            )

        # Update pending balance
        cls._adjust_balance(applicant_id, category, start_date.year, pending_delta=requested_days)

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=applicant_id,
            actor_name=applicant_name,
            actor_role=applicant_role,
            action="APPLY_LEAVE",
            from_state=ApplicationStatus.DRAFT,
            to_state=initial_status,
            remarks=f"Application submitted for {requested_days} days of {category}."
        )

        return app

    @classmethod
    @transaction.atomic
    def respond_to_substitute_request(cls, substitute_id, application_id, action, remarks=""):
        """UC-002: Accept or Decline substitute responsibility."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)
        sub_req = app.substitute_requests.filter(substitute_id=substitute_id, status="PENDING").last()

        if not sub_req or app.substitute_status != SubstituteStatus.AWAITING_RESPONSE:
            raise LeaveValidationError("No pending substitute request found for this application.")

        if action.upper() == "ACCEPT":
            sub_req.status = "ACCEPTED"
            sub_req.remarks = remarks
            sub_req.responded_at = timezone.now()
            sub_req.save()

            app.substitute_status = SubstituteStatus.ACCEPTED
            if app.applicant_role == UserRole.DIRECTOR:
                app.status = ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION
                app.current_authority_role = "DIRECTOR"
            else:
                app.status = ApplicationStatus.AWAITING_UNIT_HEAD
                app.current_authority_role = "UNIT_HEAD"
            app.save()

            LeaveActionHistory.objects.create(
                application=app,
                actor_id=substitute_id,
                actor_name=sub_req.substitute_name,
                actor_role="SUBSTITUTE",
                action="SUBSTITUTE_ACCEPT",
                from_state=ApplicationStatus.AWAITING_SUBSTITUTE,
                to_state=app.status,
                remarks=f"Substitute accepted responsibility assignment. {remarks}"
            )

        elif action.upper() == "DECLINE":
            sub_req.status = "DECLINED"
            sub_req.remarks = remarks
            sub_req.responded_at = timezone.now()
            sub_req.save()

            app.substitute_status = SubstituteStatus.DECLINED
            app.status = ApplicationStatus.APPLICANT_ACTION_REQUIRED
            app.current_authority_role = "APPLICANT"
            app.save()

            LeaveActionHistory.objects.create(
                application=app,
                actor_id=substitute_id,
                actor_name=sub_req.substitute_name,
                actor_role="SUBSTITUTE",
                action="SUBSTITUTE_DECLINE",
                from_state=ApplicationStatus.AWAITING_SUBSTITUTE,
                to_state=ApplicationStatus.APPLICANT_ACTION_REQUIRED,
                remarks=f"Substitute declined responsibility assignment. {remarks}"
            )
        else:
            raise LeaveValidationError("Invalid substitute action. Must be ACCEPT or DECLINE.")

        return app

    @classmethod
    @transaction.atomic
    def nominate_replacement_substitute(cls, applicant_id, application_id, new_substitute_id, new_substitute_name):
        """UC-019: Nominate a replacement substitute after a decline."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)
        if app.applicant_id != applicant_id:
            raise LeaveValidationError("Only the applicant can nominate a replacement substitute.")
        if app.status != ApplicationStatus.APPLICANT_ACTION_REQUIRED:
            raise LeaveValidationError("Application is not in Applicant Action Required state.")

        cls.validate_substitute(new_substitute_id, applicant_id, app.start_date, app.end_date)

        app.substitute_id = new_substitute_id
        app.substitute_name = new_substitute_name
        app.substitute_status = SubstituteStatus.AWAITING_RESPONSE
        app.status = ApplicationStatus.AWAITING_SUBSTITUTE
        app.current_authority_role = "SUBSTITUTE"
        app.save()

        last_count = app.substitute_requests.count()
        SubstituteRequest.objects.create(
            application=app,
            substitute_id=new_substitute_id,
            substitute_name=new_substitute_name,
            status="PENDING",
            replacement_count=last_count
        )

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=applicant_id,
            actor_name=app.applicant_name,
            actor_role=app.applicant_role,
            action="NOMINATE_REPLACEMENT_SUBSTITUTE",
            from_state=ApplicationStatus.APPLICANT_ACTION_REQUIRED,
            to_state=ApplicationStatus.AWAITING_SUBSTITUTE,
            remarks=f"Nominated replacement substitute {new_substitute_name} ({new_substitute_id})."
        )

        return app

    @classmethod
    @transaction.atomic
    def review_unit_head(cls, reviewer_id, reviewer_name, application_id, outcome, remarks=""):
        """UC-003: Review leave-related request at Unit Head."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.status == ApplicationStatus.AWAITING_UNIT_HEAD:
            if app.category in [LeaveCategory.CL, LeaveCategory.RH]:
                # Unit Head is final decision maker for CL and RH
                if outcome.upper() == "APPROVE":
                    app.status = ApplicationStatus.APPROVED
                    app.current_authority_role = "COMPLETED"
                    app.unit_head_recommendation = "APPROVED"
                    app.unit_head_remarks = remarks
                    app.final_decision_by = reviewer_name
                    app.final_decision_remarks = remarks
                    app.save()
                    # Deduct from balance
                    cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                                       availed_delta=app.requested_days, pending_delta=-app.requested_days, balance_delta=-app.requested_days)
                elif outcome.upper() == "REJECT":
                    app.status = ApplicationStatus.REJECTED
                    app.current_authority_role = "COMPLETED"
                    app.unit_head_recommendation = "REJECTED"
                    app.unit_head_remarks = remarks
                    app.final_decision_by = reviewer_name
                    app.final_decision_remarks = remarks
                    app.save()
                    # Release pending balance
                    cls._adjust_balance(app.applicant_id, app.category, app.start_date.year, pending_delta=-app.requested_days)
                else:
                    raise LeaveValidationError("Unit Head decision for CL/RH must be APPROVE or REJECT.")

            else:
                # Higher-sanction leave (SCL, EL, COL, VL) -> Record Recommendation
                if outcome.upper() in ["RECOMMENDED", "NOT_RECOMMENDED"]:
                    app.unit_head_recommendation = outcome.upper()
                    app.unit_head_remarks = remarks
                    
                    # Check Establishment configuration step (configured default True)
                    establishment_configured = True
                    if establishment_configured:
                        app.status = ApplicationStatus.AWAITING_ESTABLISHMENT
                        app.current_authority_role = "DEPUTY_REGISTRAR"
                    else:
                        app.status = ApplicationStatus.AWAITING_FINAL_SANCTION
                        app.current_authority_role = "SANCTIONING_AUTHORITY"
                    app.save()
                else:
                    raise LeaveValidationError("Unit Head review for higher-sanction leave must be RECOMMENDED or NOT_RECOMMENDED.")

        elif app.status == ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD:
            if app.category in [LeaveCategory.CL, LeaveCategory.RH]:
                if outcome.upper() == "APPROVE":
                    app.status = ApplicationStatus.CANCELLED
                    app.current_authority_role = "COMPLETED"
                    app.save()
                    # Restore deducted balance
                    cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                                       availed_delta=-app.requested_days, balance_delta=app.requested_days)
                else:
                    app.status = ApplicationStatus.APPROVED
                    app.current_authority_role = "COMPLETED"
                    app.save()
            else:
                app.unit_head_recommendation = outcome.upper()
                app.status = ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT
                app.current_authority_role = "DEPUTY_REGISTRAR"
                app.save()

        elif app.status == ApplicationStatus.EXTENSION_PENDING_UNIT_HEAD:
            app.unit_head_recommendation = outcome.upper()
            app.status = ApplicationStatus.EXTENSION_PENDING_ESTABLISHMENT
            app.current_authority_role = "DEPUTY_REGISTRAR"
            app.save()

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=reviewer_id,
            actor_name=reviewer_name,
            actor_role="UNIT_HEAD",
            action=f"UNIT_HEAD_{outcome.upper()}",
            from_state=app.status,
            to_state=app.status,
            remarks=remarks
        )

        return app

    @classmethod
    @transaction.atomic
    def verify_establishment(cls, actor_id, actor_name, application_id, remarks=""):
        """UC-004: Establishment verification and routing step."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.status == ApplicationStatus.AWAITING_ESTABLISHMENT:
            app.status = ApplicationStatus.AWAITING_FINAL_SANCTION
            app.current_authority_role = "SANCTIONING_AUTHORITY"
            app.save()
        elif app.status == ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT:
            app.status = ApplicationStatus.CANCELLATION_PENDING_FINAL
            app.current_authority_role = "SANCTIONING_AUTHORITY"
            app.save()
        elif app.status == ApplicationStatus.EXTENSION_PENDING_ESTABLISHMENT:
            app.status = ApplicationStatus.EXTENSION_PENDING_FINAL
            app.current_authority_role = "SANCTIONING_AUTHORITY"
            app.save()
        else:
            raise LeaveValidationError("Application is not in an Establishment routing stage.")

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role="DEPUTY_REGISTRAR",
            action="ESTABLISHMENT_VERIFY",
            from_state=app.status,
            to_state=app.status,
            remarks=remarks
        )
        return app

    @classmethod
    @transaction.atomic
    def make_final_sanction_decision(cls, authority_id, authority_name, authority_role, application_id, decision, remarks=""):
        """UC-005: Make final sanctioning decision."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.status in [ApplicationStatus.AWAITING_FINAL_SANCTION, ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION]:
            if decision.upper() == "APPROVE":
                app.status = ApplicationStatus.APPROVED
                app.current_authority_role = "COMPLETED"
                app.final_decision_by = authority_name
                app.final_decision_remarks = remarks
                app.save()

                cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                                   availed_delta=app.requested_days, pending_delta=-app.requested_days, balance_delta=-app.requested_days)
            elif decision.upper() == "REJECT":
                app.status = ApplicationStatus.REJECTED
                app.current_authority_role = "COMPLETED"
                app.final_decision_by = authority_name
                app.final_decision_remarks = remarks
                app.save()

                cls._adjust_balance(app.applicant_id, app.category, app.start_date.year, pending_delta=-app.requested_days)
            else:
                raise LeaveValidationError("Final decision must be APPROVE or REJECT.")

        elif app.status == ApplicationStatus.CANCELLATION_PENDING_FINAL:
            if decision.upper() == "APPROVE":
                app.status = ApplicationStatus.CANCELLED
                app.current_authority_role = "COMPLETED"
                app.save()
                cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                                   availed_delta=-app.requested_days, balance_delta=app.requested_days)
            else:
                app.status = ApplicationStatus.APPROVED
                app.current_authority_role = "COMPLETED"
                app.save()

        elif app.status == ApplicationStatus.EXTENSION_PENDING_FINAL:
            if decision.upper() == "APPROVE":
                app.status = ApplicationStatus.APPROVED
                app.current_authority_role = "COMPLETED"
                app.save()
                cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                                   availed_delta=app.requested_days, pending_delta=-app.requested_days, balance_delta=-app.requested_days)
            else:
                # Revert extension pending balance
                cls._adjust_balance(app.applicant_id, app.category, app.start_date.year, pending_delta=-app.requested_days)
                app.status = ApplicationStatus.APPROVED
                app.save()

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=authority_id,
            actor_name=authority_name,
            actor_role=authority_role,
            action=f"FINAL_SANCTION_{decision.upper()}",
            from_state=app.status,
            to_state=app.status,
            remarks=remarks
        )
        return app

    @classmethod
    @transaction.atomic
    def withdraw_pending_request(cls, applicant_id, application_id, remarks=""):
        """UC-007: Withdraw pending request before final approval."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.applicant_id != applicant_id:
            raise LeaveValidationError("Only the applicant can withdraw their application.")

        non_withdrawable = [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN, ApplicationStatus.CANCELLED]
        if app.status in non_withdrawable:
            raise LeaveValidationError(f"Cannot withdraw application in '{app.status}' state.")

        prev_status = app.status
        app.status = ApplicationStatus.WITHDRAWN
        app.current_authority_role = "COMPLETED"
        app.save()

        # Release pending balance
        cls._adjust_balance(app.applicant_id, app.category, app.start_date.year, pending_delta=-app.requested_days)

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=applicant_id,
            actor_name=app.applicant_name,
            actor_role=app.applicant_role,
            action="WITHDRAW_PENDING_REQUEST",
            from_state=prev_status,
            to_state=ApplicationStatus.WITHDRAWN,
            remarks=remarks or "Withdrawn by applicant."
        )
        return app

    @classmethod
    @transaction.atomic
    def request_cancellation(cls, applicant_id, application_id, remarks=""):
        """UC-008: Request pre-start cancellation of approved leave."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.applicant_id != applicant_id:
            raise LeaveValidationError("Only the applicant can request cancellation.")
        if app.status != ApplicationStatus.APPROVED:
            raise LeaveValidationError("Cancellation can only be requested for finally Approved leave.")

        if date.today() >= app.start_date:
            raise LeaveValidationError("Pre-start cancellation is unavailable once leave has commenced. Use Resumption or Extension.")

        if app.category in [LeaveCategory.CL, LeaveCategory.RH]:
            app.status = ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD
            app.current_authority_role = "UNIT_HEAD"
        else:
            app.status = ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD
            app.current_authority_role = "UNIT_HEAD"
        app.save()

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=applicant_id,
            actor_name=app.applicant_name,
            actor_role=app.applicant_role,
            action="REQUEST_CANCELLATION",
            from_state=ApplicationStatus.APPROVED,
            to_state=app.status,
            remarks=remarks or "Cancellation requested by employee."
        )
        return app

    @classmethod
    @transaction.atomic
    def submit_resumption(cls, applicant_id, application_id, actual_resumption_date, remarks=""):
        """UC-010: Submit actual return to duty after EL, COL, or VL."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)

        if app.applicant_id != applicant_id:
            raise LeaveValidationError("Only the applicant can submit duty resumption.")
        if app.status != ApplicationStatus.APPROVED:
            raise LeaveValidationError("Resumption can only be submitted for approved ongoing leave.")
        if app.category not in [LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL]:
            raise LeaveValidationError("Formal resumption review applies to EL, COL, and VL.")

        approved_end = app.end_date
        if actual_resumption_date == approved_end:
            r_type = ResumptionType.NORMAL
            delta = Decimal("0.0")
        elif actual_resumption_date < approved_end:
            r_type = ResumptionType.EARLY
            delta = Decimal(str((approved_end - actual_resumption_date).days))
        else:
            r_type = ResumptionType.LATE
            delta = Decimal(str((actual_resumption_date - approved_end).days))

        res_req, created = ResumptionRequest.objects.update_or_create(
            application=app,
            defaults={
                "applicant_id": applicant_id,
                "approved_end_date": approved_end,
                "actual_resumption_date": actual_resumption_date,
                "resumption_type": r_type,
                "delta_days": delta,
                "status": "PENDING_REVIEW",
                "remarks": remarks
            }
        )

        app.status = ApplicationStatus.RESUMPTION_PENDING_REVIEW
        app.current_authority_role = "SANCTIONING_AUTHORITY"
        app.save()

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=applicant_id,
            actor_name=app.applicant_name,
            actor_role=app.applicant_role,
            action="SUBMIT_RESUMPTION",
            from_state=ApplicationStatus.APPROVED,
            to_state=ApplicationStatus.RESUMPTION_PENDING_REVIEW,
            remarks=f"Submitted {r_type} resumption on {actual_resumption_date}."
        )
        return res_req

    @classmethod
    @transaction.atomic
    def review_resumption(cls, reviewer_id, reviewer_name, application_id, remarks=""):
        """UC-011: Review resumption and synchronize balances."""
        app = LeaveApplication.objects.select_for_update().get(id=application_id)
        res_req = ResumptionRequest.objects.get(application=app)

        res_req.status = "REVIEWED"
        res_req.reviewed_by = reviewer_name
        res_req.save()

        app.status = ApplicationStatus.APPROVED
        app.current_authority_role = "COMPLETED"
        app.save()

        if res_req.resumption_type == ResumptionType.EARLY:
            # Restore unused days to balance
            cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                               availed_delta=-res_req.delta_days, balance_delta=res_req.delta_days)
        elif res_req.resumption_type == ResumptionType.LATE:
            # Deduct extra days from balance
            cls._adjust_balance(app.applicant_id, app.category, app.start_date.year,
                               availed_delta=res_req.delta_days, balance_delta=-res_req.delta_days)

        LeaveActionHistory.objects.create(
            application=app,
            actor_id=reviewer_id,
            actor_name=reviewer_name,
            actor_role="SANCTIONING_AUTHORITY",
            action="REVIEW_RESUMPTION",
            from_state=ApplicationStatus.RESUMPTION_PENDING_REVIEW,
            to_state=ApplicationStatus.APPROVED,
            remarks=f"Resumption reviewed. Synchronized {res_req.resumption_type} return."
        )
        return res_req

    @classmethod
    @transaction.atomic
    def record_offline_leave(cls, admin_id, admin_name, employee_id, employee_name, category,
                             start_date, end_date, purpose, reference, sanctioned_by, sanction_date):
        """UC-016: Record already-sanctioned offline leave for record synchronization."""
        days = cls.calculate_requested_days(category, start_date, end_date)

        record = OfflineLeaveRecord.objects.create(
            employee_id=employee_id,
            employee_name=employee_name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            days=days,
            purpose=purpose,
            offline_sanction_reference=reference,
            sanctioned_by=sanctioned_by,
            sanction_date=sanction_date,
            recorded_by=admin_name
        )

        cls._adjust_balance(employee_id, category, start_date.year, availed_delta=days, balance_delta=-days)
        return record

    @classmethod
    @transaction.atomic
    def execute_year_end_processing(cls, year):
        """UC-020: Event-triggered year-end leave processing."""
        records_processed = 0

        # 1. CL, RH, SCL lapse
        LeaveBalance.objects.filter(year=year, category__in=[LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL]).update(balance=Decimal("0.0"))

        # 2. Faculty VL conversion to EL (2 VL : 1 EL)
        vl_balances = LeaveBalance.objects.filter(year=year, category=LeaveCategory.VL, user_category="FACULTY")
        for vl in vl_balances:
            if vl.balance > 0:
                converted_el = Decimal(str(vl.balance / Decimal("2.0")))
                vl.balance = Decimal("0.0")
                vl.save()

                el_bal, _ = LeaveBalance.objects.get_or_create(
                    user_id=vl.user_id,
                    category=LeaveCategory.EL,
                    year=year + 1,
                    defaults={"username": vl.username, "user_category": "FACULTY", "balance": Decimal("0.0"), "allocated": Decimal("0.0"), "availed": Decimal("0.0"), "pending": Decimal("0.0")}
                )
                el_bal.balance += converted_el
                el_bal.save()
                records_processed += 1

        # 3. Carry forward EL and COL
        carry_forward_bals = LeaveBalance.objects.filter(year=year, category__in=[LeaveCategory.EL, LeaveCategory.COL])
        for bal in carry_forward_bals:
            next_bal, _ = LeaveBalance.objects.get_or_create(
                user_id=bal.user_id,
                category=bal.category,
                year=year + 1,
                defaults={"username": bal.username, "user_category": bal.user_category, "balance": Decimal("0.0"), "allocated": Decimal("0.0"), "availed": Decimal("0.0"), "pending": Decimal("0.0")}
            )
            next_bal.balance += bal.balance
            next_bal.save()
            records_processed += 1

        return records_processed

    @staticmethod
    def _adjust_balance(user_id, category, year, allocated_delta=0, availed_delta=0, pending_delta=0, balance_delta=0):
        """Internal helper to safely update leave balances."""
        bal, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            category=category,
            year=year,
            defaults={"allocated": Decimal("0.0"), "availed": Decimal("0.0"), "pending": Decimal("0.0"), "balance": Decimal("0.0")}
        )
        bal.allocated += Decimal(str(allocated_delta))
        bal.availed += Decimal(str(availed_delta))
        bal.pending += Decimal(str(pending_delta))
        bal.balance += Decimal(str(balance_delta))
        bal.save()
        return bal
