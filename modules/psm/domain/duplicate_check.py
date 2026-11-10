from typing import List, Dict, Any

def is_possible_duplicate(new_indent: Dict[str, Any], existing_indents: List[Dict[str, Any]]) -> bool:
    """Pure logic to detect duplicate indents by item name and estimated cost."""
    for existing in existing_indents:
        if (
            existing["item_name"].strip().lower() == new_indent["item_name"].strip().lower()
            and abs(float(existing["estimated_cost"]) - float(new_indent["estimated_cost"])) < 0.01
            and existing["status"] not in {"REJECTED", "WITHDRAWN"}
        ):
            return True
    return False