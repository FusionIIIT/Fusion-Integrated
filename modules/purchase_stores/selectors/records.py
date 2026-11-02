from modules.purchase_stores.models import DepartmentAccess, Indent, PurchaseOrder, StockBalance


def _can_view_all(actor):
    return any(
        actor.has_permission(code)
        for code in (
            "purchase_stores.po.manage",
            "purchase_stores.po.view",
            "purchase_stores.audit.view",
            "purchase_stores.policy.manage",
        )
    )


def departments_for(actor):
    return DepartmentAccess.objects.filter(user_id=actor.user_id, is_active=True).values_list(
        "department_id", flat=True
    )


def indents_for(actor):
    queryset = Indent.objects.prefetch_related("lines", "actions", "approval_steps")
    if _can_view_all(actor):
        return queryset
    if actor.has_permission("purchase_stores.indent.view"):
        return queryset.filter(department_id__in=departments_for(actor))
    return queryset.filter(requestor_user_id=actor.user_id)


def orders_for(actor):
    queryset = PurchaseOrder.objects.select_related("indent", "vendor")
    if _can_view_all(actor):
        return queryset
    if actor.has_permission("purchase_stores.po.view"):
        return queryset.filter(indent__department_id__in=departments_for(actor))
    return queryset.filter(indent__requestor_user_id=actor.user_id)


def stock_for(actor):
    queryset = StockBalance.objects.all()
    if _can_view_all(actor):
        return queryset
    if actor.has_permission("purchase_stores.stock.manage"):
        return queryset.filter(department_id__in=departments_for(actor))
    if actor.has_permission("purchase_stores.stock.view"):
        return queryset.filter(is_central=True)
    return queryset.none()


def transfers_for(actor):
    from modules.purchase_stores.models import StockTransfer

    queryset = StockTransfer.objects.all()
    if _can_view_all(actor):
        return queryset
    department_ids = departments_for(actor)
    return queryset.filter(source_department_id__in=department_ids) | queryset.filter(
        destination_department_id__in=department_ids
    )
