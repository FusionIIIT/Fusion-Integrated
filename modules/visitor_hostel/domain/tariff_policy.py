from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any

class TariffNotFoundError(Exception):
    pass

def get_applicable_tariff(category: str, room_type: str, stay_date: date, tariff_entries: List[Dict[str, Any]]) -> Decimal:
    valid_entries = [entry for entry in tariff_entries if entry['category'] == category and entry['room_type'] == room_type and entry['effective_from'] <= stay_date]
    
    if not valid_entries:
        raise TariffNotFoundError(f"No tariff found for category {category}, room type {room_type} on date {stay_date}")
        
    return max(valid_entries, key=lambda entry: entry['effective_from'])['rate']

def calculate_room_charge(rate_per_day: Decimal, check_in_date: date, check_out_date: date, num_rooms: int = 1) -> Decimal:
    total_days = max(1, (check_out_date - check_in_date).days)
    
    return rate_per_day * total_days * num_rooms
