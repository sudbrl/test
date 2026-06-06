# ============================================================
# MODULE: LTV (Loan-to-Value) & DTI (Debt-to-Income)
# ============================================================

from dataclasses import dataclass
from typing import Optional

# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class LTVInput:
    loan_amount: float          # Total loan requested
    property_value: float       # Appraised property value
    down_payment: float = 0.0   # Optional down payment

@dataclass
class LTVResult:
    ltv_ratio: float            # As percentage e.g. 80.0
    loan_amount: float
    property_value: float
    down_payment: float
    equity: float
    risk_tier: str
    max_allowed_ltv: float
    is_approved: bool
    pmi_required: bool
    notes: list[str]

@dataclass
class DTIInput:
    gross_monthly_income: float         # Before tax
    monthly_debts: float                # Existing monthly debt payments
    proposed_monthly_payment: float     # New loan monthly payment
    other_income: float = 0.0           # Additional income sources

@dataclass
class DTIResult:
    front_end_dti: float        # Housing expense ratio
    back_end_dti: float         # Total debt ratio
    gross_monthly_income: float
    total_monthly_debts: float
    proposed_payment: float
    risk_tier: str
    max_allowed_dti: float
    is_approved: bool
    notes: list[str]


# ─────────────────────────────────────────────
# CONSTANTS / THRESHOLDS
# ─────────────────────────────────────────────

LTV_THRESHOLDS = {
    "Excellent":    (0,    60),
    "Good":         (60,   75),
    "Fair":         (75,   80),
    "High":         (80,   90),
    "Very High":    (90,   95),
    "Unacceptable": (95,  100),
}

DTI_THRESHOLDS = {
    "Excellent":    (0,    28),
    "Good":         (28,   36),
    "Fair":         (36,   43),
    "High":         (43,   50),
    "Unacceptable": (50,  100),
}

MAX_LTV = 95.0      # Conventional loan max
PMI_THRESHOLD = 80.0
MAX_DTI = 43.0      # Standard QM rule (Qualified Mortgage)
MAX_FRONT_END_DTI = 28.0


# ─────────────────────────────────────────────
# LTV CALCULATION
# ─────────────────────────────────────────────

def calculate_ltv(data: LTVInput) -> LTVResult:
    """
    Calculate Loan-to-Value ratio.
    LTV = (Loan Amount / Property Value) × 100
    """
    if data.property_value <= 0:
        raise ValueError("Property value must be greater than zero.")
    if data.loan_amount < 0:
        raise ValueError("Loan amount cannot be negative.")
    if data.down_payment < 0:
        raise ValueError("Down payment cannot be negative.")

    effective_loan = data.loan_amount - data.down_payment
    if effective_loan < 0:
        effective_loan = 0.0

    ltv_ratio = (effective_loan / data.property_value) * 100
    equity = data.property_value - effective_loan

    # Determine risk tier
    risk_tier = "Unacceptable"
    for tier, (low, high) in LTV_THRESHOLDS.items():
        if low <= ltv_ratio < high:
            risk_tier = tier
            break
    if ltv_ratio >= 100:
        risk_tier = "Unacceptable"

    is_approved = ltv_ratio <= MAX_LTV
    pmi_required = ltv_ratio > PMI_THRESHOLD

    # Build notes
    notes = []
    if ltv_ratio > MAX_LTV:
        notes.append(f"❌ LTV {ltv_ratio:.1f}% exceeds maximum allowed {MAX_LTV}%.")
    if pmi_required and is_approved:
        notes.append("⚠️ PMI (Private Mortgage Insurance) is required above 80% LTV.")
    if ltv_ratio <= 60:
        notes.append("✅ Excellent LTV — lowest risk tier, best rates available.")
    if data.down_payment > 0:
        pct = (data.down_payment / data.property_value) * 100
        notes.append(f"ℹ️ Down payment is {pct:.1f}% of property value.")
    if equity < 0:
        notes.append("⚠️ Negative equity — loan exceeds property value.")

    return LTVResult(
        ltv_ratio=round(ltv_ratio, 2),
        loan_amount=data.loan_amount,
        property_value=data.property_value,
        down_payment=data.down_payment,
        equity=round(equity, 2),
        risk_tier=risk_tier,
        max_allowed_ltv=MAX_LTV,
        is_approved=is_approved,
        pmi_required=pmi_required,
        notes=notes,
    )


# ─────────────────────────────────────────────
# DTI CALCULATION
# ─────────────────────────────────────────────

def calculate_dti(data: DTIInput) -> DTIResult:
    """
    Calculate Debt-to-Income ratio.
    Front-End DTI = (Proposed Housing Payment / Gross Income) × 100
    Back-End DTI  = ((All Debts + Proposed Payment) / Gross Income) × 100
    """
    total_income = data.gross_monthly_income + data.other_income

    if total_income <= 0:
        raise ValueError("Total monthly income must be greater than zero.")
    if data.monthly_debts < 0:
        raise ValueError("Monthly debts cannot be negative.")
    if data.proposed_monthly_payment < 0:
        raise ValueError("Proposed monthly payment cannot be negative.")

    front_end_dti = (data.proposed_monthly_payment / total_income) * 100
    total_debts = data.monthly_debts + data.proposed_monthly_payment
    back_end_dti = (total_debts / total_income) * 100

    # Determine risk tier (based on back-end DTI)
    risk_tier = "Unacceptable"
    for tier, (low, high) in DTI_THRESHOLDS.items():
        if low <= back_end_dti < high:
            risk_tier = tier
            break
    if back_end_dti >= 100:
        risk_tier = "Unacceptable"

    is_approved = back_end_dti <= MAX_DTI and front_end_dti <= MAX_FRONT_END_DTI

    # Build notes
    notes = []
    if back_end_dti > MAX_DTI:
        notes.append(f"❌ Back-end DTI {back_end_dti:.1f}% exceeds maximum allowed {MAX_DTI}%.")
    if front_end_dti > MAX_FRONT_END_DTI:
        notes.append(f"❌ Front-end DTI {front_end_dti:.1f}% exceeds maximum allowed {MAX_FRONT_END_DTI}%.")
    if is_approved:
        notes.append("✅ DTI ratios are within acceptable limits.")
    if data.other_income > 0:
        notes.append(f"ℹ️ Additional income of ${data.other_income:,.2f}/mo included in calculation.")
    if back_end_dti <= 28:
        notes.append("✅ Excellent DTI — strong borrower profile.")

    return DTIResult(
        front_end_dti=round(front_end_dti, 2),
        back_end_dti=round(back_end_dti, 2),
        gross_monthly_income=data.gross_monthly_income,
        total_monthly_debts=round(total_debts, 2),
        proposed_payment=data.proposed_monthly_payment,
        risk_tier=risk_tier,
        max_allowed_dti=MAX_DTI,
        is_approved=is_approved,
        notes=notes,
    )


# ─────────────────────────────────────────────
# COMBINED SUMMARY
# ─────────────────────────────────────────────

def combined_eligibility(ltv_result: LTVResult, dti_result: DTIResult) -> dict:
    """
    Returns overall eligibility based on both LTV and DTI results.
    """
    overall = ltv_result.is_approved and dti_result.is_approved

    reasons = []
    if not ltv_result.is_approved:
        reasons.append(f"LTV too high ({ltv_result.ltv_ratio}% > {ltv_result.max_allowed_ltv}%)")
    if not dti_result.is_approved:
        reasons.append(f"DTI too high ({dti_result.back_end_dti}% > {dti_result.max_allowed_dti}%)")

    return {
        "overall_approved": overall,
        "ltv_approved": ltv_result.is_approved,
        "dti_approved": dti_result.is_approved,
        "rejection_reasons": reasons,
        "summary": "✅ APPROVED" if overall else "❌ NOT APPROVED",
    }
