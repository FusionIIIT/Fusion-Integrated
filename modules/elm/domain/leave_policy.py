from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


class LeavePolicyError(ValueError):
    """Base exception for leave-policy errors."""


class InvalidLeaveCategoryError(LeavePolicyError):
    """Raised when a leave category is unsupported."""


class InvalidLeaveIntervalError(LeavePolicyError):
    """Raised when a leave date interval is invalid."""


class UnsupportedLeaveCountingError(LeavePolicyError):
    """Raised when the counting method is not defined for an interval."""


class InvalidLeaveBalanceError(LeavePolicyError):
    """Raised when a leave balance is invalid."""


class LeavePolicy:
    SINGLE_DAY_CATEGORIES = {
        LeaveCategory.CL,
        LeaveCategory.RH,
        LeaveCategory.SCL,
    }

    CONTINUOUS_DAY_CATEGORIES = {
        LeaveCategory.EL,
        LeaveCategory.COL,
        LeaveCategory.VL,
    }

    def __init__(
        self,
        category: LeaveCategory,
        annual_entitlement: Decimal,
    ) -> None:
        try:
            self.category = LeaveCategory(category)
        except (TypeError, ValueError) as err:
            raise InvalidLeaveCategoryError(
                f"Invalid leave category: {category!r}"
            ) from err

        entitlement = self.validate_numeric_input(annual_entitlement)

        if entitlement < 0:
            raise ValueError("Annual entitlement cannot be negative")

        self.annual_entitlement = entitlement

    @staticmethod
    def validate_numeric_input(value: object) -> Decimal:
        """Convert a value to a finite Decimal."""
        try:
            number = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as err:
            raise ValueError("Invalid numeric input") from err

        if not number.is_finite():
            raise ValueError("Numeric input must be finite")

        return number

    @staticmethod
    def validate_date_interval(
        start_date: date,
        end_date: date,
    ) -> None:
        """Validate the types and ordering of a leave interval."""
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise TypeError("Date inputs must be datetime.date objects")

        if start_date > end_date:
            raise InvalidLeaveIntervalError(
                "Start date must be on or before end date"
            )

    def calculate_days(
        self,
        start_date: date,
        end_date: date,
        *,
        half_day: bool = False,
    ) -> Decimal:
        """Calculate leave days according to the category's counting rules."""
        self.validate_date_interval(start_date, end_date)

        if not isinstance(half_day, bool):
            raise TypeError("half_day must be a boolean")

        if half_day:
            if self.category != LeaveCategory.CL:
                raise LeavePolicyError(
                    "Half-day leave is supported only for CL"
                )

            if start_date != end_date:
                raise InvalidLeaveIntervalError(
                    "Half-day CL must apply to a single date"
                )

            return Decimal("0.5")

        if self.category in self.SINGLE_DAY_CATEGORIES:
            if start_date != end_date:
                raise UnsupportedLeaveCountingError(
                    f"Multi-date counting is not defined for "
                    f"{self.category.value}"
                )

            return Decimal("1")

        if self.category in self.CONTINUOUS_DAY_CATEGORIES:
            days = (end_date - start_date).days + 1
            return Decimal(days)

        raise InvalidLeaveCategoryError(
            f"Unsupported leave category: {self.category}"
        )

    def year_end_treatment(self, balance: Decimal) -> Decimal:
        """Calculate the year-end balance or conversion credit."""
        balance = self.validate_numeric_input(balance)

        if balance < 0:
            raise InvalidLeaveBalanceError(
                "Leave balance cannot be negative"
            )

        if self.category in self.SINGLE_DAY_CATEGORIES:
            return Decimal("0")

        if self.category in {LeaveCategory.EL, LeaveCategory.COL}:
            return balance

        if self.category == LeaveCategory.VL:
            return balance / Decimal("2")

        raise InvalidLeaveCategoryError(
            f"Unsupported leave category: {self.category}"
        )
