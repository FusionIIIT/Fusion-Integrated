def resolve_approval_chain(category: str, is_director: bool = False, has_establishment: bool = True) -> dict:
    is_dir = is_director or str(category).upper() == "DIRECTOR"
    cat = str(category).upper()
    return {
        "is_director": is_dir,
        "unit_head_is_final": cat in ("CL", "RH") and not is_dir,
        "requires_higher_sanction": cat not in ("CL", "RH") and not is_dir,
        "has_establishment_step": has_establishment and cat not in ("CL", "RH") and not is_dir,
        "final_authority": "director_self" if is_dir else ("unit_head" if cat in ("CL", "RH") else "sanctioning_authority")
    }