# Views for Department Module - local 32b parameter LLM style implementation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import (
    DepartmentAnnouncement, InventoryItem,
    StockRequest, StockMovementLog,
)

def get_user_context(request):
    # Extracts actor info from request.user or headers/body for flexible testing
    user = getattr(request, "user", None)
    username = getattr(user, "username", "") or request.headers.get("X-Username") or request.data.get("username") or request.query_params.get("username", "guest")
    role = getattr(user, "active_role", None) or getattr(user, "kind", None) or request.headers.get("X-Role") or request.data.get("role") or request.query_params.get("role", "Student")
    program = request.headers.get("X-Program") or request.query_params.get("program", "ALL")
    batch_year = request.headers.get("X-Batch-Year") or request.query_params.get("batch_year", None)
    if batch_year:
        try:
            batch_year = int(batch_year)
        except ValueError:
            batch_year = None
    return {
        "username": str(username),
        "role": str(role).strip(),
        "program": str(program).strip(),
        "batch_year": batch_year,
    }

class AnnouncementListCreateView(APIView):
    # UC-DEPT-001 (View Announcements) & UC-DEPT-002 (Create Announcement)
    def get(self, request):
        ctx = get_user_context(request)
        viewer_role = ctx["role"].lower()
        viewer_program = ctx["program"].lower()
        viewer_year = ctx["batch_year"]
        announcements = DepartmentAnnouncement.objects.filter(is_active=True)
        relevant_list = []
        for ann in announcements:
            # BR-DEPT-002: Announcement Visibility Filtering
            target_r = ann.target_role.lower()
            if target_r != "all" and target_r != viewer_role:
                continue
            target_p = ann.target_program.lower()
            if target_p != "all" and target_p != viewer_program:
                continue
            if ann.target_academic_year is not None and viewer_year is not None:
                if ann.target_academic_year != viewer_year:
                    continue
            relevant_list.append({
                "id": ann.id, "title": ann.title, "content": ann.content,
                "author_username": ann.author_username, "author_role": ann.author_role,
                "target_role": ann.target_role, "target_program": ann.target_program,
                "target_academic_year": ann.target_academic_year,
                "created_at": ann.created_at.strftime("%Y-%m-%d %H:%M"),
            })
        return Response({"announcements": relevant_list, "count": len(relevant_list)}, status=status.HTTP_200_OK)

    def post(self, request):
        # UC-DEPT-002: Create announcement
        ctx = get_user_context(request)
        author_role = ctx["role"]
        # BR-DEPT-001: Only Faculty, Dept_Admin, or HOD can publish
        allowed_roles = ["faculty", "dept_admin", "hod", "admin", "department_admin"]
        if author_role.lower() not in allowed_roles:
            return Response({"error": "Unauthorized: Only Faculty, Dept_Admin, or HOD can publish announcements."}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get("title", "").strip()
        content = request.data.get("content", "").strip()
        target_role = request.data.get("target_role", "ALL").strip()
        target_program = request.data.get("target_program", "ALL").strip()
        target_academic_year = request.data.get("target_academic_year", None)
        # BR-DEPT-003: Validation of publication completeness
        if not title or not content:
            return Response({"error": "Validation Error: Title and content are required."}, status=status.HTTP_400_BAD_REQUEST)
        if target_academic_year:
            try:
                target_academic_year = int(target_academic_year)
            except ValueError:
                target_academic_year = None
        ann = DepartmentAnnouncement.objects.create(
            title=title, content=content, author_username=ctx["username"],
            author_role=author_role, target_role=target_role,
            target_program=target_program, target_academic_year=target_academic_year,
            is_active=True,
        )
        return Response({"message": "Announcement created successfully.", "announcement_id": ann.id, "title": ann.title}, status=status.HTTP_201_CREATED)

class InventoryItemListView(APIView):
    # Inventory items list and stock insertion by Dept_Admin
    def get(self, request):
        items = InventoryItem.objects.all().order_by("item_name")
        data = [{"id": i.id, "item_name": i.item_name, "description": i.description, "available_quantity": i.available_quantity, "unit": i.unit} for i in items]
        return Response({"items": data}, status=status.HTTP_200_OK)

    def post(self, request):
        ctx = get_user_context(request)
        if ctx["role"].lower() not in ["dept_admin", "admin", "department_admin"]:
            return Response({"error": "Unauthorized: Only Dept_Admin can manage inventory."}, status=status.HTTP_403_FORBIDDEN)
        item_name = request.data.get("item_name", "").strip()
        quantity = int(request.data.get("quantity", 0))
        unit = request.data.get("unit", "units").strip()
        description = request.data.get("description", "").strip()
        if not item_name or quantity <= 0:
            return Response({"error": "Item name and positive quantity required."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            item, created = InventoryItem.objects.get_or_create(
                item_name=item_name, defaults={"description": description, "available_quantity": quantity, "unit": unit}
            )
            if not created:
                item.available_quantity += quantity
                item.save()
            # BR-DEPT-016: Immutable audit log for insertion
            StockMovementLog.objects.create(
                item=item, movement_type="INSERTION", quantity=quantity,
                performed_by=ctx["username"], notes=f"Stock insertion of {quantity} {unit}",
            )
        return Response({"message": "Stock added successfully.", "item_id": item.id, "available_quantity": item.available_quantity}, status=status.HTTP_201_CREATED)

class StockRequestCreateListView(APIView):
    # Handles UC-DEPT-004: Request Stock Item
    def get(self, request):
        ctx = get_user_context(request)
        role = ctx["role"].lower()
        if role in ["hod", "dept_admin", "admin"]:
            requests = StockRequest.objects.all()
        else:
            requests = StockRequest.objects.filter(requester_username=ctx["username"])
        data = [{
            "id": r.id, "item_id": r.item.id, "item_name": r.item.item_name,
            "requester_username": r.requester_username, "requester_role": r.requester_role,
            "quantity": r.quantity, "purpose": r.purpose, "status": r.status,
            "hod_remarks": r.hod_remarks, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
        } for r in requests]
        return Response({"requests": data}, status=status.HTTP_200_OK)

    def post(self, request):
        ctx = get_user_context(request)
        requester_role = ctx["role"]
        # BR-DEPT-005: Only Faculty can request stock
        if requester_role.lower() not in ["faculty", "admin"]:
            return Response({"error": "Unauthorized: Only Faculty members may request stock items."}, status=status.HTTP_403_FORBIDDEN)
        item_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        purpose = request.data.get("purpose", "").strip()
        if not item_id or not quantity:
            return Response({"error": "Item ID and quantity are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
            if quantity <= 0: raise ValueError()
        except ValueError:
            return Response({"error": "Quantity must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"error": "Inventory item not found."}, status=status.HTTP_404_NOT_FOUND)
        # BR-DEPT-015: Stock Availability Validation at request time
        if quantity > item.available_quantity:
            return Response({"error": f"Stock unavailable: Requested ({quantity}) exceeds available ({item.available_quantity})."}, status=status.HTTP_400_BAD_REQUEST)
        stock_request = StockRequest.objects.create(
            item=item, requester_username=ctx["username"], requester_role=requester_role,
            quantity=quantity, purpose=purpose, status="PENDING_HOD_APPROVAL",
        )
        return Response({"message": "Stock request submitted in Pending HOD Approval state.", "request_id": stock_request.id, "status": stock_request.status}, status=status.HTTP_201_CREATED)

class StockRequestApprovalView(APIView):
    # Handles UC-DEPT-005: Approve or Reject Stock Request
    def post(self, request, pk):
        ctx = get_user_context(request)
        role = ctx["role"].lower()
        # BR-DEPT-006: Only HOD can approve or reject
        if role not in ["hod", "admin"]:
            return Response({"error": "Unauthorized: Only HOD can approve or reject stock requests."}, status=status.HTTP_403_FORBIDDEN)
        try:
            stock_request = StockRequest.objects.get(id=pk)
        except StockRequest.DoesNotExist:
            return Response({"error": "Stock request not found."}, status=status.HTTP_404_NOT_FOUND)
        if stock_request.status != "PENDING_HOD_APPROVAL":
            return Response({"error": f"Request is in '{stock_request.status}' state and cannot be modified."}, status=status.HTTP_400_BAD_REQUEST)
        decision = request.data.get("decision", "").strip().upper()
        remarks = request.data.get("remarks", "").strip()
        if decision == "APPROVE":
            stock_request.status = "APPROVED_FOR_ISSUANCE"
            stock_request.hod_remarks = remarks
            stock_request.save()
            return Response({"message": "Stock request approved for issuance.", "status": stock_request.status}, status=status.HTTP_200_OK)
        elif decision == "REJECT":
            stock_request.status = "REJECTED"
            stock_request.hod_remarks = remarks
            stock_request.save()
            return Response({"message": "Stock request has been rejected.", "status": stock_request.status}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid decision. Choose APPROVE or REJECT."}, status=status.HTTP_400_BAD_REQUEST)

class StockRequestIssueView(APIView):
    # Handles UC-DEPT-006: Allocate and Issue Stock
    def post(self, request, pk):
        ctx = get_user_context(request)
        role = ctx["role"].lower()
        # BR-DEPT-007: Only Dept_Admin can issue stock
        if role not in ["dept_admin", "admin", "department_admin"]:
            return Response({"error": "Unauthorized: Only Dept_Admin can allocate and issue stock."}, status=status.HTTP_403_FORBIDDEN)
        try:
            stock_request = StockRequest.objects.get(id=pk)
        except StockRequest.DoesNotExist:
            return Response({"error": "Stock request not found."}, status=status.HTTP_404_NOT_FOUND)
        # Check precondition
        if stock_request.status != "APPROVED_FOR_ISSUANCE":
            return Response({"error": f"Stock cannot be issued: Request status is '{stock_request.status}'. HOD approval required."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            item = stock_request.item
            if item.available_quantity < stock_request.quantity:
                return Response({"error": f"Cannot issue: available inventory ({item.available_quantity}) < requested ({stock_request.quantity})."}, status=status.HTTP_400_BAD_REQUEST)
            # AFR-DEPT-013: Automatically decrement quantity
            item.available_quantity -= stock_request.quantity
            item.save()
            stock_request.status = "ISSUED"
            stock_request.save()
            # BR-DEPT-016 & AFR-DEPT-015: Immutable stock-movement log
            StockMovementLog.objects.create(
                item=item, stock_request=stock_request, movement_type="ISSUANCE",
                quantity=stock_request.quantity, performed_by=ctx["username"],
                notes=f"Issued to {stock_request.requester_username} for {stock_request.purpose}",
            )
        return Response({
            "message": "Stock successfully issued and inventory updated.",
            "request_id": stock_request.id, "item_name": item.item_name,
            "remaining_quantity": item.available_quantity, "status": stock_request.status,
        }, status=status.HTTP_200_OK)

class StockMovementLogListView(APIView):
    # BR-DEPT-016: Immutable audit trail view
    def get(self, request):
        logs = StockMovementLog.objects.all().order_by("-created_at")
        data = [{
            "id": log.id, "item_name": log.item.item_name, "movement_type": log.movement_type,
            "quantity": log.quantity, "performed_by": log.performed_by, "notes": log.notes,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        } for log in logs]
        return Response({"logs": data}, status=status.HTTP_200_OK)
