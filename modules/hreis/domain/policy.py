from decimal import Decimal, InvalidOperation


class HRPolicy:
    @staticmethod
    def validate_authorities(value: object) -> tuple[str, ...]:
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(v, str) or not v.strip() for v in value)
        ):
            raise ValueError("Authorities must be a non-empty list of strings.")
        trimmed_values = [v.strip() for v in value]
        unique_roles = set(trimmed_values)
        if len(unique_roles) != len(trimmed_values):
            raise ValueError("Duplicate role names are not allowed.")
        return tuple(trimmed_values)

    @staticmethod
    def available_leave(balance_map: dict, leave_type: str, days: Decimal) -> Decimal:
        try:
            balance = Decimal(str(balance_map.get(leave_type)))
        except (TypeError, InvalidOperation) as exc:
            raise ValueError("Invalid balance type or value.") from exc

        if not balance.is_finite() or balance < 0:
            raise ValueError("Balance must be a finite and non-negative number.")

        if not days.is_finite() or days <= 0:
            raise ValueError("Days must be a positive, finite decimal number.")

        if days > balance:
            raise ValueError(f"Cannot take more leave than available: {balance} vs. {days}")

        return balance - days

    @staticmethod
    def valid_claim_documents(documents: object) -> bool:
        if not isinstance(documents, list) or not documents:
            return False

        return all(isinstance(doc, str) and bool(doc.strip()) for doc in documents)
