from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VisitorViewSet, RoomViewSet, TariffViewSet, BookingViewSet,
    StayViewSet, MealViewSet, BillingViewSet, InventoryViewSet
)

router = DefaultRouter()
router.register(r'visitors', VisitorViewSet, basename='vh-visitor')
router.register(r'rooms', RoomViewSet, basename='vh-room')
router.register(r'tariffs', TariffViewSet, basename='vh-tariff')
router.register(r'bookings', BookingViewSet, basename='vh-booking')
router.register(r'stays', StayViewSet, basename='vh-stay')
router.register(r'meals', MealViewSet, basename='vh-meal')
router.register(r'bills', BillingViewSet, basename='vh-bill')
router.register(r'inventory', InventoryViewSet, basename='vh-inventory')

urlpatterns = [
    path('', include(router.urls)),
]
