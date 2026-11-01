import django.db.transaction
from django.utils.timezone import now

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.department.domain.stock import IllegalTransition, next_state
from modules.department.models import Department, InventoryItem, StockMovement, StockRequest
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.department.selectors.stock import current_role_user_id
from modules.department.services import notifications
from modules.department.services.authz import require


def _notify(topic, request, recipient, subject):
    """Sends a notification if a recipient is provided."""
    if recipient:
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"{topic}:{request.id}",
            subject=subject,
            body=f"Notification for {topic}",
            recipient_user_id=recipient,
            payload={"request_id": request.id}
        )

def insert_stock(*, actor, department_id, name, unit, quantity):
    """Inserts or updates stock quantity for an inventory item."""
    require(actor, "department.inventory.create")

    if quantity <= 0:
        raise ConflictError("The insertion quantity must be positive.")

    with django.db.transaction.atomic():
        try:
            department = Department.objects.select_for_update().get(pk=department_id)
            if department_id not in department_ids_for_role(actor, "dept_admin"):
                raise NotFoundError("Department not held by actor as dept_admin")

            item, created = InventoryItem.objects.select_for_update().get_or_create(
                department=department,
                name=name,
                defaults={'unit': unit, 'quantity': 0}
            )

            if not created:
                # Lock item to ensure atomic update
                item = InventoryItem.objects.select_for_update().get(pk=item.pk)
                item.quantity += quantity
                item.save()

                # Record movement
                StockMovement.objects.create(
                    item=item,
                    kind='insertion',
                    quantity=quantity,
                    actor_user_id=actor.user_id
                )
            else:
                # For newly created item, insertion quantity is added once (handled by initial quantity=0 and then adding)
                # If it was created, we set the quantity to the insertion quantity as per requirement 8
                item.quantity = quantity
                item.save()

                # Record movement for creation
                StockMovement.objects.create(
                    item=item,
                    kind='insertion',
                    quantity=quantity,
                    actor_user_id=actor.user_id
                )

            return item
        except Department.DoesNotExist:
            raise NotFoundError("Department not found")

def request_stock(*, actor, item_id, quantity):
    """Creates a stock request for an item."""
    require(actor, "department.stock_request.create")

    if quantity <= 0:
        raise ConflictError("The requested quantity must be positive.")

    with django.db.transaction.atomic():
        try:
            item = InventoryItem.objects.select_for_update().get(pk=item_id)
            department = item.department

            if department.code not in member_department_codes(actor):
                raise NotFoundError("Item department not accessible to actor")

            # Check stock level
            if item.quantity < quantity:
                raise ConflictError("Insufficient stock available for this request.")

            # Create request
            request = StockRequest.objects.create(
                department=department,
                item=item,
                requester_user_id=actor.user_id,
                quantity=quantity,
                state='pending_hod_approval'
            )

            # Notifications
            hod_user_id = current_role_user_id(item.department, 'hod')
            dept_admin_user_id = current_role_user_id(item.department, 'dept_admin')

            # Swapped: stock.requested goes to dept_admin holder, stock.authorization_required goes to hod holder
            _notify("stock.requested", request, dept_admin_user_id, f"Stock requested for {item.name}")
            _notify("stock.authorization_required", request, hod_user_id, "Stock request requires authorization")

            return request
        except InventoryItem.DoesNotExist:
            raise NotFoundError("Inventory item not found")

def decide_request(*, actor, request_id, outcome):
    """Approves or rejects a stock request."""
    require(actor, "department.stock_request.approve")

    with django.db.transaction.atomic():
        try:
            request = StockRequest.objects.select_for_update().get(pk=request_id)

            # Department-held check
            if request.department.id not in department_ids_for_role(actor, "hod"):
                raise NotFoundError("Request department not held by actor as HOD")

            if outcome not in ['approve', 'reject']:
                raise BadRequestError("Invalid outcome provided. Outcome must be 'approve' or 'reject'.")

            # Compute next state
            try:
                next_state_str = next_state(request.state, outcome, "hod")
            except IllegalTransition:
                raise ConflictError("Illegal transition attempted for this request state.")

            # Update state
            request.state = next_state_str
            request.decided_by_user_id = actor.user_id
            request.decided_at = now()
            request.save()

            # Notification on rejection
            if outcome == 'reject':
                _notify("stock.rejected", request, request.requester_user_id, "Stock request rejected")
            elif outcome == 'approve':
                # If approved, trigger next step (e.g., issue stock)
                pass

            return request
        except StockRequest.DoesNotExist:
            raise NotFoundError("Stock request not found")

def issue_stock(*, actor, request_id):
    """Issues stock based on an approved request."""
    require(actor, "department.stock_request.update")

    with django.db.transaction.atomic():
        try:
            request = StockRequest.objects.select_for_update().get(pk=request_id)

            # Department-held check
            if request.department.id not in department_ids_for_role(actor, "dept_admin"):
                raise NotFoundError("Request department not held by actor as Dept Admin")

            # Compute next state
            try:
                next_state_str = next_state(request.state, 'issue', "dept_admin")
            except IllegalTransition:
                raise ConflictError("Illegal transition attempted for this request state.")

            # Lock item
            item = InventoryItem.objects.select_for_update().get(pk=request.item.pk)

            # Check stock availability before decrementing
            if item.quantity < request.quantity:
                raise ConflictError("Insufficient stock available to fulfill this request.")

            # Decrease quantity and record movement
            item.quantity -= request.quantity
            item.save()

            StockMovement.objects.create(
                item=item,
                kind='issuance',
                quantity=request.quantity,
                request=request,
                actor_user_id=actor.user_id
            )

            # Update request state
            request.state = next_state_str
            request.issued_by_user_id = actor.user_id
            request.issued_at = now()
            request.save()

            # Notification to requester
            _notify("stock.issued", request, request.requester_user_id, f"Stock issued for {request.item.name}")

            return request
        except StockRequest.DoesNotExist:
            raise NotFoundError("Stock request not found")
