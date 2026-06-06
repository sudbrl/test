"""
MODULE: LTV (Loan-to-Value) Calculation Engine
"""

from dataclasses import dataclass, field


# =========================================================
# DATA CLASSES
# =========================================================

@dataclass
class LTVInput:
    loan_amount: float
    property_value: float
    down_payment: float = 0.0


@dataclass
class LTVResult:
    ltv_ratio: float
    loan_amount: float
    property_value: float
    down_payment: float
    effective_loan: float
    equity: float
    risk_tier: str
    max_allowed_ltv: float
    is_approved: bool
    pmi_required: bool
    notes: list = field(default_factory=list)


# =========================================================
# THRESHOLDS
# =========================================================

LTV_THRESHOLDS = {
    "Excellent":    (0,    60),
    "Good":         (60,   75),
    "Fair":         (75,   80),
    "High":         (80,   90),
    "Very High":    (90,   95),
    "Unacceptable": (95,   200),
}

MAX_LTV = 95.0
PMI_THRESHOLD = 80.0


# =========================================================
# HELPERS
# =========================================================

def _get_ltv_tier(value: float) -> str:
    for tier, (lo, hi) in LTV_THRESHOLDS.items():
        if lo <= value < hi:
            return tier
    return "Unacceptable"


# =========================================================
# CALCULATION
# =========================================================

def calculate_ltv(data: LTVInput) -> LTVResult:
    """
    Calculate Loan-to-Value ratio.

    LTV = (Effective Loan / Property Value) x 100
    Effective Loan = Loan Amount - Down Payment
    """
    if data.property_value <= 0:
        raise ValueError("Property value must be greater than zero.")
    if data.loan_amount < 0:
        raise ValueError("Loan amount cannot be negative.")
    if data.down_payment < 0:
        raise ValueError("Down payment cannot be negative.")

    effective_loan = max(data.loan_amount - data.down_payment, 0.0)
    ltv = (effective_loan / data.property_value) * 100.0
    equity = data.property_value - effective_loan
    risk_tier = _get_ltv_tier(ltv)
    approved = ltv <= MAX_LTV
    pmi = ltv > PMI_THRESHOLD

    notes = []
    if ltv > MAX_LTV:
        notes.append(f"LTV {ltv:.1f}% exceeds maximum allowed {MAX_LTV}%.")
    if pmi and approved:
        notes.append("PMI (Private Mortgage Insurance) required above 80% LTV.")
    if ltv <= 60:
        notes.append("Excellent LTV - lowest risk, best rates available.")
    if data.down_payment > 0:
        dp_pct = (data.down_payment / data.property_value) * 100
        notes.append(f"Down payment is {dp_pct:.1f}% of property value.")
    if equity < 0:
        notes.append("Negative equity - loan exceeds property value.")

    return LTVResult(
        ltv_ratio=round(ltv, 2),
        loan_amount=data.loan_amount,
        property_value=data.property_value,
        down_payment=data.down_payment,
        effective_loan=round(effective_loan, 2),
        equity=round(equity, 2),
        risk_tier=risk_tier,
        max_allowed_ltv=MAX_LTV,
        is_approved=approved,
        pmi_required=pmi,
        notes=notes,
    )
