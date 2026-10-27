# Task: fix assertions and test setups in modules/leave/tests/test_services.py (output the COMPLETE file)

Fix the following 4 tests in `modules/leave/tests/test_services.py`:

1. In `test_apply_overlap_raises`:
   `LeaveApplication.objects.create` must include `user_id=user_principal.user_id`:
   ```python
   @pytest.mark.django_db
   def test_apply_overlap_raises(cl_cat, user_principal):
       # Setup existing application
       existing_app = LeaveApplication.objects.create(
           user_id=user_principal.user_id,
           category=cl_cat,
           start_date=date(2026, 11, 1),
           end_date=date(2026, 11, 5),
           half_day="",
           days_charged=Decimal("5.0"),
           balance_deducted=Decimal("5.0"),
           reason="Existing",
           is_station_leave=False,
           substitute_user_id=None,
           recommendation="",
           applicant_is_director=False,
           actual_resumption_date=None,
           resumption_status="none",
           status=AWAITING_UNIT_HEAD,
       )
   ```

2. In `test_apply_insufficient_balance_raises`:
   Casual Leave excludes weekends. From Nov 1 to Nov 11 is only 8 working days (equal to balance).
   To test insufficient balance (> 8.0 days), set `end_date=date(2026, 11, 13)` (which is 10 working days):
   ```python
   @pytest.mark.django_db
   def test_apply_insufficient_balance_raises(cl_cat, cl_balance, user_principal):
       # Balance is 8.0 days. Nov 1 to Nov 13 has 10 working days (> 8.0).
       with pytest.raises(ConflictError) as excinfo:
           leave_services.apply(
               user_id=user_principal.user_id,
               category_code=cl_cat.code,
               start_date=date(2026, 11, 1),
               end_date=date(2026, 11, 13),
               reason="Insufficient balance test",
           )
       assert "Insufficient leave balance" in str(excinfo.value)
   ```

3. In `test_transition_cancellation_restores_balance`:
   In setup step 1, set the balance to 6.0 to reflect that 2.0 was already deducted for this approved application:
   ```python
   @pytest.mark.django_db
   def test_transition_cancellation_restores_balance(cl_cat, cl_balance, user_principal):
       # 1. Setup: Approved application with 2.0 days deducted
       cl_balance.balance_days = Decimal("6.0")
       cl_balance.save()

       app = LeaveApplication.objects.create(
           user_id=user_principal.user_id,
           category=cl_cat,
           start_date=date(2026, 11, 2),
           end_date=date(2026, 11, 3),
           half_day="",
           days_charged=Decimal("2.0"),
           balance_deducted=Decimal("2.0"),
           reason="Original reason",
           is_station_leave=False,
           substitute_user_id=None,
           recommendation="",
           applicant_is_director=False,
           actual_resumption_date=None,
           resumption_status="none",
           status=APPROVED,
       )
       # Verify initial balance before cancellation
       balance = LeaveBalance.objects.get(category=cl_cat, user_id=1, year=2026)
       assert balance.balance_days == Decimal("6.0")
   ```

4. In `test_transition_unauthorized_actor_raises`:
   An employee attempting to approve is rejected by role / state machine (`"Your role cannot make that change."`), while a unit head lacking the permission is rejected by permission check (`"This action needs leave_management.application.review"`):
   ```python
   @pytest.mark.django_db
   def test_transition_unauthorized_actor_raises(cl_cat, application_instance, user_principal):
       # 1. Employee attempting to approve (state machine rejects employee actor)
       employee_principal = DummyPrincipal(user_id=1, permissions=["leave_management.application.delete"])
       with pytest.raises(PermissionDeniedError) as excinfo:
           leave_services.transition(
               application_id=application_instance.pk,
               to_status=APPROVED,
               actor=employee_principal,
               reason="Attempt to approve",
           )
       assert "Your role cannot make that change." in str(excinfo.value) or "This action needs" in str(excinfo.value)

       # 2. User with unit_head role but without required review permission
       unauthorized_principal = DummyPrincipal(user_id=99, permissions=[], actor_kind="unit_head")
       with pytest.raises(PermissionDeniedError) as excinfo:
           leave_services.transition(
               application_id=application_instance.pk,
               to_status=APPROVED,
               actor=unauthorized_principal,
               reason="Attempt to approve",
           )
       assert "This action needs leave_management.application.review" in str(excinfo.value)
   ```

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
