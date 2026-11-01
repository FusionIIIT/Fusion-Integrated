from django.contrib import admin

from modules.visitors_hostel import models


@admin.register(models.BookingTransition)
@admin.register(models.StayAlert)
@admin.register(models.Bill)
@admin.register(models.CashSettlement)
@admin.register(models.InventoryChange)
@admin.register(models.NotificationOutbox)
class ReadOnlyAuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (models.Building, models.RoomType, models.Room, models.Booking,
              models.BookingChangeRequest, models.RoomAllocation,
              models.StayRecord, models.Tariff, models.MealBooking,
              models.MealRate, models.InventoryItem,
              models.ReplenishmentRequest):
    admin.site.register(model)
