# Management command to seed default rooms, tariffs, and initial inventory.
from datetime import date

from django.core.management.base import BaseCommand

from modules.vh.domain.tariffs import DEFAULT_TARIFFS
from modules.vh.models.inventory import InventoryItem
from modules.vh.models.room import Room
from modules.vh.models.tariff import TariffConfig


class Command(BaseCommand):
    help = "Seeds initial rooms, category tariffs, and baseline inventory for Visitors Hostel."

    def handle(self, *args, **options):
        # 1. Seed Rooms (10 suites, 20 non-suites)
        rooms_created = 0
        for i in range(101, 111):
            _, created = Room.objects.get_or_create(
                room_number=str(i),
                defaults={"room_type": "suite", "floor": 1, "capacity": 2, "is_active": True},
            )
            if created:
                rooms_created += 1

        for i in range(201, 221):
            _, created = Room.objects.get_or_create(
                room_number=str(i),
                defaults={"room_type": "non_suite", "floor": 2, "capacity": 2, "is_active": True},
            )
            if created:
                rooms_created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {rooms_created} new rooms."))

        # 2. Seed Default Tariffs
        tariffs_created = 0
        eff_date = date(2026, 1, 1)
        for key, rate in DEFAULT_TARIFFS.items():
            _, created = TariffConfig.objects.get_or_create(
                category=key.category,
                room_type=key.room_type,
                occupancy=key.occupancy,
                effective_from=eff_date,
                defaults={"daily_rate": rate, "is_active": True},
            )
            if created:
                tariffs_created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {tariffs_created} tariff rules."))

        # 3. Seed Default Inventory
        sample_items = [
            ("Bedsheets Single", "linen", 50, 15, "pieces"),
            ("Bedsheets Double", "linen", 30, 10, "pieces"),
            ("Pillow Covers", "linen", 80, 20, "pieces"),
            ("Bath Towels", "linen", 40, 10, "pieces"),
            ("Electric Kettles", "utensils", 25, 5, "pieces"),
            ("Tea Cups Set", "utensils", 30, 8, "sets"),
            ("Water Jugs", "utensils", 35, 10, "pieces"),
            ("Toilet Paper Rolls", "consumables", 100, 25, "rolls"),
            ("Bath Soaps", "consumables", 120, 30, "pieces"),
            ("Hand Sanitizers", "consumables", 45, 12, "bottles"),
        ]
        inv_created = 0
        for name, cat, qty, min_th, unit in sample_items:
            _, created = InventoryItem.objects.get_or_create(
                item_name=name,
                defaults={
                    "category": cat,
                    "current_quantity": qty,
                    "minimum_threshold": min_th,
                    "unit": unit,
                    "is_threshold_alert": qty < min_th,
                },
            )
            if created:
                inv_created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {inv_created} inventory items."))
