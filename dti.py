"""
MODULE: DTI (Debt-to-Income) Calculation Engine
"""

from dataclasses import dataclass, field


# =========================================================
# DATA CLASSES
# =========================================================

@dataclass
class DTIInput:
    gross_monthly_income: float
    monthly_debts: float
    proposed_monthly_payment: float
    other_income: float = 0.0


@dataclass
class DTIResult:
    front_end_dti: float
    back_end_dti: float
    gross_monthly_income: float
    total_income: float
    existing_debts: float
    proposed_payment: float
    total_monthly_debts: float
    risk_tier: str
    max_allowed_back_dti: float
    max_allowed_front_dti: float
    is_approved: bool
    notes: list = field(default_factory=list)


# =========================================================
# THRESHOLDS
# =========================================================

DTI_THRESHOLDS = {
    "Excellent":    (0,    28),
    "Good":         (28,   36),
    "Fair":         (36,   43),
    "High":         (43,   50),
    "Unacceptable": (50,   200),
}

MAX_BACK_DTI = 43.0
MAX_FRONT_DTI = 28.0


# =========================================================
# HELPERS
# =========================================================

def _get_dti_tier(value: float) -> str:
    for tier, (lo, hi) in DTI_THRESHOLDS.items():
        if lo <= value < hi:
            return tier
    return "Unacceptable"


# =========================================================
# CALCULATION
# =========================================================

def calculate_dti(data: DTIInput) -> DTIResult:
    """
    Calculate Debt-to-Income ratio.

    Front-End DTI = (Proposed Payment / Total Income) x 100
    Back-End DTI  = (All Debts / Total Income) x 100
    """
    total_income = data.gross_monthly_income + data.other_income

    if total_income <= 0:
        raise ValueError("Total monthly income must be greater than zero.")
    if data.monthly_debts < 0:
        raise ValueError("Monthly debts cannot be negative.")
    if data.proposed_monthly_payment < 0:
        raise ValueError("Proposed payment cannot be negative.")

    front = (data.proposed_monthly_payment / total_income) * 100.0
    total_debts = data.monthly_debts + data.proposed_monthly_payment
    back = (total_debts / total_income) * 100.0

    risk_tier = _get_dti_tier(back)
    approved = back <= MAX_BACK_DTI and front <= MAX_FRONT_DTI

    notes = []
    if back > MAX_BACK_DTI:
        notes.append(f"Back-end DTI {back:.1f}% exceeds maximum {MAX_BACK_DTI}%.")
    if front > MAX_FRONT_DTI:
        notes.append(f"Front-end DTI {front:.1f}% exceeds maximum {MAX_FRONT_DTI}%.")
    if approved:
        notes.append("DTI ratios within acceptable limits.")
    if data.other_income > 0:
        notes.append(f"Additional income of ${data.other_income:,.2f}/mo included.")
    if back <= 28:
        notes.append("Excellent DTI - strong borrower profile.")

    return DTIResult(
        front_end_dti=round(front, 2),
        back_end_dti=round(back, 2),
        gross_monthly_income=data.gross_monthly_income,
        total_income=round(total_income, 2),
        existing_debts=data.monthly_debts,
        proposed_payment=data.proposed_monthly_payment,
        total_monthly_debts=round(total_debts, 2),
        risk_tier=risk_tier,
        max_allowed_back_dti=MAX_BACK_DTI,
        max_allowed_front_dti=MAX_FRONT_DTI,
        is_approved=approved,
        notes=notes,
    )
