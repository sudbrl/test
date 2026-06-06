"""
MODULE: LTV (Loan-to-Value) & DTI (Debt-to-Income)
  - Data models
  - Calculation engines
  - PDF report generation
"""

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

# ═══════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# THRESHOLDS
# ═══════════════════════════════════════════════

LTV_THRESHOLDS = {
    "Excellent":    (0,    60),
    "Good":         (60,   75),
    "Fair":         (75,   80),
    "High":         (80,   90),
    "Very High":    (90,   95),
    "Unacceptable": (95,   200),
}

DTI_THRESHOLDS = {
    "Excellent":    (0,    28),
    "Good":         (28,   36),
    "Fair":         (36,   43),
    "High":         (43,   50),
    "Unacceptable": (50,   200),
}

MAX_LTV = 95.0
PMI_THRESHOLD = 80.0
MAX_BACK_DTI = 43.0
MAX_FRONT_DTI = 28.0


def _get_tier(value: float, thresholds: dict) -> str:
    for tier, (lo, hi) in thresholds.items():
        if lo <= value < hi:
            return tier
    return "Unacceptable"


# ═══════════════════════════════════════════════
# LTV CALCULATION
# ═══════════════════════════════════════════════

def calculate_ltv(data: LTVInput) -> LTVResult:
    if data.property_value <= 0:
        raise ValueError("Property value must be greater than zero.")
    if data.loan_amount < 0:
        raise ValueError("Loan amount cannot be negative.")
    if data.down_payment < 0:
        raise ValueError("Down payment cannot be negative.")

    effective_loan = max(data.loan_amount - data.down_payment, 0.0)
    ltv = (effective_loan / data.property_value) * 100.0
    equity = data.property_value - effective_loan
    risk_tier = _get_tier(ltv, LTV_THRESHOLDS)
    approved = ltv <= MAX_LTV
    pmi = ltv > PMI_THRESHOLD

    notes = []
    if ltv > MAX_LTV:
        notes.append(f"LTV {ltv:.1f}% exceeds maximum allowed {MAX_LTV}%.")
    if pmi and approved:
        notes.append("PMI (Private Mortgage Insurance) required above 80% LTV.")
    if ltv <= 60:
        notes.append("Excellent LTV — lowest risk, best rates available.")
    if data.down_payment > 0:
        dp_pct = (data.down_payment / data.property_value) * 100
        notes.append(f"Down payment is {dp_pct:.1f}% of property value.")
    if equity < 0:
        notes.append("Negative equity — loan exceeds property value.")

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


# ═══════════════════════════════════════════════
# DTI CALCULATION
# ═══════════════════════════════════════════════

def calculate_dti(data: DTIInput) -> DTIResult:
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

    risk_tier = _get_tier(back, DTI_THRESHOLDS)
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
        notes.append("Excellent DTI — strong borrower profile.")

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


# ═══════════════════════════════════════════════
# COMBINED ELIGIBILITY
# ═══════════════════════════════════════════════

def combined_eligibility(ltv: LTVResult, dti: DTIResult) -> dict:
    overall = ltv.is_approved and dti.is_approved
    reasons = []
    if not ltv.is_approved:
        reasons.append(f"LTV {ltv.ltv_ratio}% exceeds {ltv.max_allowed_ltv}%")
    if not dti.is_approved:
        reasons.append(f"DTI {dti.back_end_dti}% exceeds {dti.max_allowed_back_dti}%")

    if overall:
        if ltv.risk_tier in ("Excellent", "Good") and dti.risk_tier in ("Excellent", "Good"):
            strength = "Strong"
        elif ltv.risk_tier in ("Fair",) or dti.risk_tier in ("Fair",):
            strength = "Moderate"
        else:
            strength = "Weak (borderline)"
    else:
        strength = "N/A"

    return {
        "overall_approved": overall,
        "ltv_approved": ltv.is_approved,
        "dti_approved": dti.is_approved,
        "rejection_reasons": reasons,
        "profile_strength": strength,
        "summary": "APPROVED" if overall else "NOT APPROVED",
    }


# ═══════════════════════════════════════════════
# PDF REPORT GENERATION
# ═══════════════════════════════════════════════

class PDFReport(FPDF):
    """Custom PDF with header/footer."""
    def __init__(self, analyst_name: str = "System"):
        super().__init__()
        self.analyst_name = analyst_name

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "LTV & DTI Assessment Report", ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Analyst: {self.analyst_name}", ln=True, align="C")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Confidential", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 51, 102)
        self.set_fill_color(230, 240, 250)
        self.cell(0, 9, f"  {title}", ln=True, fill=True)
        self.ln(3)

    def key_value(self, key: str, value: str, bold_val: bool = False):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.cell(80, 7, key, border=0)
        self.set_font("Helvetica", "B" if bold_val else "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, value, ln=True)

    def status_badge(self, label: str, approved: bool):
        self.set_font("Helvetica", "B", 11)
        if approved:
            self.set_text_color(0, 128, 0)
            self.cell(0, 8, f"{label}: APPROVED", ln=True)
        else:
            self.set_text_color(200, 0, 0)
            self.cell(0, 8, f"{label}: NOT APPROVED", ln=True)
        self.set_text_color(0, 0, 0)

    def notes_block(self, notes: list):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        for note in notes:
            clean = note.replace("✅", "[OK]").replace("❌", "[X]").replace("⚠️", "[!]").replace("ℹ️", "[i]")
            self.cell(5)
            self.multi_cell(0, 5, f"- {clean}")
        self.ln(2)


def generate_pdf_report(
    ltv: LTVResult,
    dti: DTIResult,
    combined: dict,
    analyst_name: str = "System",
    borrower_name: str = "N/A",
) -> bytes:
    """Generate a complete PDF report and return as bytes."""

    pdf = PDFReport(analyst_name=analyst_name)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── OVERALL RESULT ──────────────────────
    pdf.section_title("1. Overall Assessment")
    pdf.status_badge("Decision", combined["overall_approved"])
    pdf.key_value("Profile Strength:", combined["profile_strength"], bold_val=True)
    pdf.key_value("Borrower:", borrower_name)
    if combined["rejection_reasons"]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(200, 0, 0)
        for r in combined["rejection_reasons"]:
            pdf.cell(5)
            pdf.cell(0, 6, f"- {r}", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # ── LTV SECTION ─────────────────────────
    pdf.section_title("2. Loan-to-Value (LTV) Analysis")
    pdf.key_value("LTV Ratio:", f"{ltv.ltv_ratio}%", bold_val=True)
    pdf.key_value("Risk Tier:", ltv.risk_tier, bold_val=True)
    pdf.key_value("Max Allowed LTV:", f"{ltv.max_allowed_ltv}%")
    pdf.status_badge("LTV Status", ltv.is_approved)
    pdf.key_value("PMI Required:", "Yes" if ltv.pmi_required else "No")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Breakdown:", ln=True)
    pdf.key_value("  Loan Amount:", f"${ltv.loan_amount:,.2f}")
    pdf.key_value("  Down Payment:", f"${ltv.down_payment:,.2f}")
    pdf.key_value("  Effective Loan:", f"${ltv.effective_loan:,.2f}")
    pdf.key_value("  Property Value:", f"${ltv.property_value:,.2f}")
    pdf.key_value("  Equity:", f"${ltv.equity:,.2f}")
    pdf.ln(2)

    if ltv.notes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Notes:", ln=True)
        pdf.notes_block(ltv.notes)

    # ── DTI SECTION ─────────────────────────
    pdf.section_title("3. Debt-to-Income (DTI) Analysis")
    pdf.key_value("Front-End DTI:", f"{dti.front_end_dti}%", bold_val=True)
    pdf.key_value("Back-End DTI:", f"{dti.back_end_dti}%", bold_val=True)
    pdf.key_value("Risk Tier:", dti.risk_tier, bold_val=True)
    pdf.key_value("Max Front-End DTI:", f"{dti.max_allowed_front_dti}%")
    pdf.key_value("Max Back-End DTI:", f"{dti.max_allowed_back_dti}%")
    pdf.status_badge("DTI Status", dti.is_approved)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Breakdown:", ln=True)
    pdf.key_value("  Gross Monthly Income:", f"${dti.gross_monthly_income:,.2f}")
    pdf.key_value("  Total Income:", f"${dti.total_income:,.2f}")
    pdf.key_value("  Existing Debts:", f"${dti.existing_debts:,.2f}")
    pdf.key_value("  Proposed Payment:", f"${dti.proposed_payment:,.2f}")
    pdf.key_value("  Total Monthly Debts:", f"${dti.total_monthly_debts:,.2f}")
    pdf.ln(2)

    if dti.notes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Notes:", ln=True)
        pdf.notes_block(dti.notes)

    # ── THRESHOLDS REFERENCE ────────────────
    pdf.add_page()
    pdf.section_title("4. Reference: Risk Tier Thresholds")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "LTV Thresholds:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for tier, (lo, hi) in LTV_THRESHOLDS.items():
        marker = " <-- CURRENT" if tier == ltv.risk_tier else ""
        pdf.cell(10)
        pdf.cell(0, 6, f"{tier}: {lo}% - {hi}%{marker}", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "DTI Thresholds:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for tier, (lo, hi) in DTI_THRESHOLDS.items():
        marker = " <-- CURRENT" if tier == dti.risk_tier else ""
        pdf.cell(10)
        pdf.cell(0, 6, f"{tier}: {lo}% - {hi}%{marker}", ln=True)
    pdf.ln(5)

    # ── DISCLAIMER ──────────────────────────
    pdf.section_title("5. Disclaimer")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4,
        "This report is generated for informational purposes only and does not constitute "
        "a binding loan commitment or financial advice. All calculations are based on the "
        "inputs provided and standard industry thresholds. Actual lending decisions may "
        "involve additional factors including credit score, employment history, and "
        "collateral assessment. Please consult a licensed financial advisor."
    )

    # Output
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
