"""
FRONTEND: Streamlit App - LTV & DTI Calculator
  - Streamlit Cloud secret-based authentication
  - Professional landing page
  - Full analysis dashboard
  - PDF report download (ASCII-safe)
"""

import streamlit as st
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

from ltv import (
    LTVInput, LTVResult, calculate_ltv,
    LTV_THRESHOLDS, MAX_LTV, PMI_THRESHOLD,
)
from dti import (
    DTIInput, DTIResult, calculate_dti,
    DTI_THRESHOLDS, MAX_BACK_DTI, MAX_FRONT_DTI,
)


# =============================================================
# PAGE CONFIG
# =============================================================

st.set_page_config(
    page_title="LTV & DTI Risk Analyzer",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================
# COMBINED ELIGIBILITY (kept in frontend since it joins both)
# =============================================================

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
        elif ltv.risk_tier == "Fair" or dti.risk_tier == "Fair":
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


# =============================================================
# PDF REPORT (ASCII-safe, no unicode symbols)
# =============================================================

def _safe(text: str) -> str:
    """Replace non-latin-1 characters for FPDF compatibility."""
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "*",   # bullet
        "\u2026": "...", # ellipsis
        "\u00b7": ".",   # middle dot
        "\u2010": "-",   # hyphen
        "\u2011": "-",   # non-breaking hyphen
        "\u2012": "-",   # figure dash
        "\u00a0": " ",   # non-breaking space
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Remove any remaining non-latin-1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


class PDFReport(FPDF):
    def __init__(self, analyst_name: str = "System"):
        super().__init__()
        self.analyst_name = _safe(analyst_name)

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "LTV & DTI Assessment Report", ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 5, f"Generated: {ts}  |  Analyst: {self.analyst_name}", ln=True, align="C")
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
        self.cell(0, 9, f"  {_safe(title)}", ln=True, fill=True)
        self.ln(3)

    def kv(self, key: str, value: str, bold_val: bool = False):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.cell(80, 7, _safe(key), border=0)
        self.set_font("Helvetica", "B" if bold_val else "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, _safe(value), ln=True)

    def status(self, label: str, approved: bool):
        self.set_font("Helvetica", "B", 11)
        if approved:
            self.set_text_color(0, 128, 0)
            self.cell(0, 8, f"{_safe(label)}: APPROVED", ln=True)
        else:
            self.set_text_color(200, 0, 0)
            self.cell(0, 8, f"{_safe(label)}: NOT APPROVED", ln=True)
        self.set_text_color(0, 0, 0)

    def notes_block(self, notes: list):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        for note in notes:
            self.cell(5)
            self.multi_cell(0, 5, f"- {_safe(note)}")
        self.ln(2)


def generate_pdf(
    ltv: LTVResult,
    dti: DTIResult,
    combined: dict,
    analyst_name: str = "System",
    borrower_name: str = "N/A",
) -> bytes:

    pdf = PDFReport(analyst_name=analyst_name)
    pdf.alias_nb_pages()
    pdf.add_page()

    # -- Overall
    pdf.section_title("1. Overall Assessment")
    pdf.status("Decision", combined["overall_approved"])
    pdf.kv("Profile Strength:", combined["profile_strength"], bold_val=True)
    pdf.kv("Borrower:", borrower_name)
    if combined["rejection_reasons"]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(200, 0, 0)
        for r in combined["rejection_reasons"]:
            pdf.cell(5)
            pdf.cell(0, 6, f"- {_safe(r)}", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # -- LTV
    pdf.section_title("2. Loan-to-Value (LTV) Analysis")
    pdf.kv("LTV Ratio:", f"{ltv.ltv_ratio}%", bold_val=True)
    pdf.kv("Risk Tier:", ltv.risk_tier, bold_val=True)
    pdf.kv("Max Allowed LTV:", f"{ltv.max_allowed_ltv}%")
    pdf.status("LTV Status", ltv.is_approved)
    pdf.kv("PMI Required:", "Yes" if ltv.pmi_required else "No")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Breakdown:", ln=True)
    pdf.kv("  Loan Amount:", f"${ltv.loan_amount:,.2f}")
    pdf.kv("  Down Payment:", f"${ltv.down_payment:,.2f}")
    pdf.kv("  Effective Loan:", f"${ltv.effective_loan:,.2f}")
    pdf.kv("  Property Value:", f"${ltv.property_value:,.2f}")
    pdf.kv("  Equity:", f"${ltv.equity:,.2f}")
    pdf.ln(2)
    if ltv.notes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Notes:", ln=True)
        pdf.notes_block(ltv.notes)

    # -- DTI
    pdf.section_title("3. Debt-to-Income (DTI) Analysis")
    pdf.kv("Front-End DTI:", f"{dti.front_end_dti}%", bold_val=True)
    pdf.kv("Back-End DTI:", f"{dti.back_end_dti}%", bold_val=True)
    pdf.kv("Risk Tier:", dti.risk_tier, bold_val=True)
    pdf.kv("Max Front-End DTI:", f"{dti.max_allowed_front_dti}%")
    pdf.kv("Max Back-End DTI:", f"{dti.max_allowed_back_dti}%")
    pdf.status("DTI Status", dti.is_approved)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Breakdown:", ln=True)
    pdf.kv("  Gross Monthly Income:", f"${dti.gross_monthly_income:,.2f}")
    pdf.kv("  Total Income:", f"${dti.total_income:,.2f}")
    pdf.kv("  Existing Debts:", f"${dti.existing_debts:,.2f}")
    pdf.kv("  Proposed Payment:", f"${dti.proposed_payment:,.2f}")
    pdf.kv("  Total Monthly Debts:", f"${dti.total_monthly_debts:,.2f}")
    pdf.ln(2)
    if dti.notes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Notes:", ln=True)
        pdf.notes_block(dti.notes)

    # -- Reference
    pdf.add_page()
    pdf.section_title("4. Reference: Risk Tier Thresholds")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "LTV Thresholds:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for tier, (lo, hi) in LTV_THRESHOLDS.items():
        hi_display = f"{hi}%" if hi < 200 else "100%+"
        marker = " <-- CURRENT" if tier == ltv.risk_tier else ""
        pdf.cell(10)
        pdf.cell(0, 6, f"{tier}: {lo}% - {hi_display}{marker}", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "DTI Thresholds:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for tier, (lo, hi) in DTI_THRESHOLDS.items():
        hi_display = f"{hi}%" if hi < 200 else "50%+"
        marker = " <-- CURRENT" if tier == dti.risk_tier else ""
        pdf.cell(10)
        pdf.cell(0, 6, f"{tier}: {lo}% - {hi_display}{marker}", ln=True)
    pdf.ln(5)

    # -- Disclaimer
    pdf.section_title("5. Disclaimer")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, _safe(
        "This report is generated for informational purposes only and does not "
        "constitute a binding loan commitment or financial advice. All calculations "
        "are based on the inputs provided and standard industry thresholds. Actual "
        "lending decisions may involve additional factors including credit score, "
        "employment history, and collateral assessment. Please consult a licensed "
        "financial advisor."
    ))

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# =============================================================
# AUTHENTICATION
# =============================================================

def authenticate():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.user_fullname = ""
        st.session_state.user_role = ""

    if st.session_state.authenticated:
        return True

    try:
        creds = st.secrets["credentials"]
        valid_users = list(creds["usernames"])
        valid_passwords = list(creds["passwords"])
        valid_names = list(creds["names"])
        valid_roles = list(creds["roles"])
    except Exception:
        st.error("Credentials not configured. Add [credentials] to Streamlit secrets.")
        st.stop()

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown("")
        st.markdown("")
        st.title("🏦 LTV & DTI Analyzer")
        st.caption("Sign in to access the risk assessment tool")
        st.markdown("")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if username in valid_users:
                idx = valid_users.index(username)
                if password == valid_passwords[idx]:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_fullname = valid_names[idx]
                    st.session_state.user_role = valid_roles[idx]
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Username not found.")

        st.markdown("---")
        st.caption("Demo credentials: `admin` / `admin123`")

    return False


# =============================================================
# LANDING PAGE
# =============================================================

TIER_ICONS = {
    "Excellent": "🟢", "Good": "🟩", "Fair": "🟡",
    "High": "🟠", "Very High": "🔴", "Unacceptable": "⛔",
}


def show_landing_page():

    st.title("🏦 LTV & DTI Risk Analyzer")
    st.caption("Professional mortgage risk assessment with instant PDF reports")

    st.markdown("---")

    # ── FEATURE HIGHLIGHTS ──────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### 📊 LTV Analysis")
        st.write("Loan-to-Value ratio with risk tiering, PMI detection, and equity analysis.")
    with c2:
        st.markdown("#### 💰 DTI Analysis")
        st.write("Front-end & back-end Debt-to-Income with qualification checks.")
    with c3:
        st.markdown("#### 📄 PDF Reports")
        st.write("Download professional assessment reports for compliance records.")
    with c4:
        st.markdown("#### 🔒 Secure Access")
        st.write("Role-based login with Streamlit Cloud secrets management.")

    st.markdown("---")

    # ── RISK TIER TABLES ────────────────────
    st.subheader("📋 Risk Tier Reference")
    col_a, col_b = st.columns(2)

    with col_a:
        st.write("**LTV Thresholds**")
        ltv_rows = []
        for tier, (lo, hi) in LTV_THRESHOLDS.items():
            hi_d = f"{hi}%" if hi < 200 else "100%+"
            ltv_rows.append({
                "": TIER_ICONS.get(tier, ""),
                "Tier": tier,
                "Range": f"{lo}% - {hi_d}",
            })
        st.table(ltv_rows)
        st.caption(f"Max LTV: **{MAX_LTV}%** | PMI above **{PMI_THRESHOLD}%**")

    with col_b:
        st.write("**DTI Thresholds**")
        dti_rows = []
        for tier, (lo, hi) in DTI_THRESHOLDS.items():
            hi_d = f"{hi}%" if hi < 200 else "50%+"
            dti_rows.append({
                "": TIER_ICONS.get(tier, ""),
                "Tier": tier,
                "Range": f"{lo}% - {hi_d}",
            })
        st.table(dti_rows)
        st.caption(f"Max Front-End DTI: **{MAX_FRONT_DTI}%** | Max Back-End DTI: **{MAX_BACK_DTI}%**")

    st.markdown("---")

    # ── HOW IT WORKS ────────────────────────
    st.subheader("🔄 How It Works")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown("**Step 1: Enter Details**")
        st.write("Input loan amount, property value, income, and debts in the sidebar.")
    with h2:
        st.markdown("**Step 2: Get Analysis**")
        st.write("Instant LTV & DTI calculations with risk tiering and approval status.")
    with h3:
        st.markdown("**Step 3: Download Report**")
        st.write("Generate a professional PDF report for your records and compliance.")

    st.markdown("---")

    # ── FORMULAS ────────────────────────────
    st.subheader("📐 Formulas")
    f1, f2 = st.columns(2)
    with f1:
        st.info("**LTV** = (Loan Amount - Down Payment) / Property Value x 100")
    with f2:
        st.info("**DTI** = Total Monthly Debts / Gross Monthly Income x 100")

    st.markdown("")
    st.caption("Use the sidebar to enter loan details and click Calculate.")


# =============================================================
# RESULTS DISPLAY
# =============================================================

def fmt_c(v): return f"${v:,.2f}"
def fmt_p(v): return f"{v:.2f}%"


def show_results(ltv, dti, combined, borrower_name):

    # ── BANNER ──────────────────────────────
    if combined["overall_approved"]:
        st.success(
            f"**APPROVED** | Profile Strength: {combined['profile_strength']} | "
            f"Borrower: {borrower_name}"
        )
    else:
        reasons = " | ".join(combined["rejection_reasons"])
        st.error(f"**NOT APPROVED** | {reasons} | Borrower: {borrower_name}")

    st.markdown("---")

    # ── METRICS ROW ─────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("LTV Ratio", fmt_p(ltv.ltv_ratio), f"Max {MAX_LTV}%", delta_color="inverse")
    with m2:
        st.metric("Front-End DTI", fmt_p(dti.front_end_dti), f"Max {MAX_FRONT_DTI}%", delta_color="inverse")
    with m3:
        st.metric("Back-End DTI", fmt_p(dti.back_end_dti), f"Max {MAX_BACK_DTI}%", delta_color="inverse")
    with m4:
        st.metric("Equity", fmt_c(ltv.equity))

    st.markdown("---")

    # ── TWO COLUMNS ─────────────────────────
    col_ltv, col_dti = st.columns(2, gap="large")

    # LTV Column
    with col_ltv:
        st.subheader("🏠 LTV Analysis")

        icon = TIER_ICONS.get(ltv.risk_tier, "")
        st.write(f"**Status:** {'Approved ✅' if ltv.is_approved else 'Not Approved ❌'}")
        st.write(f"**Risk Tier:** {icon} **{ltv.risk_tier}**")
        st.write(f"**PMI Required:** {'Yes' if ltv.pmi_required else 'No'}")

        st.markdown("---")
        st.write("**Financial Breakdown**")
        st.table([
            {"Item": "Loan Amount",     "Value": fmt_c(ltv.loan_amount)},
            {"Item": "Down Payment",    "Value": fmt_c(ltv.down_payment)},
            {"Item": "Effective Loan",  "Value": fmt_c(ltv.effective_loan)},
            {"Item": "Property Value",  "Value": fmt_c(ltv.property_value)},
            {"Item": "Equity",          "Value": fmt_c(ltv.equity)},
            {"Item": "LTV Ratio",       "Value": fmt_p(ltv.ltv_ratio)},
        ])

        st.write("**LTV Utilization**")
        st.progress(min(ltv.ltv_ratio / MAX_LTV, 1.0))
        st.caption(f"{fmt_p(ltv.ltv_ratio)} of {MAX_LTV}% limit")

        if ltv.notes:
            with st.expander("LTV Notes"):
                for n in ltv.notes:
                    st.write(f"- {n}")

    # DTI Column
    with col_dti:
        st.subheader("💰 DTI Analysis")

        icon = TIER_ICONS.get(dti.risk_tier, "")
        st.write(f"**Status:** {'Approved ✅' if dti.is_approved else 'Not Approved ❌'}")
        st.write(f"**Risk Tier:** {icon} **{dti.risk_tier}**")

        st.markdown("---")
        st.write("**Income & Debt Breakdown**")
        st.table([
            {"Item": "Gross Monthly Income",  "Value": fmt_c(dti.gross_monthly_income)},
            {"Item": "Total Income",          "Value": fmt_c(dti.total_income)},
            {"Item": "Existing Debts",        "Value": fmt_c(dti.existing_debts)},
            {"Item": "Proposed Payment",      "Value": fmt_c(dti.proposed_payment)},
            {"Item": "Total Monthly Debts",   "Value": fmt_c(dti.total_monthly_debts)},
            {"Item": "Front-End DTI",         "Value": fmt_p(dti.front_end_dti)},
            {"Item": "Back-End DTI",          "Value": fmt_p(dti.back_end_dti)},
        ])

        st.write("**Front-End DTI**")
        st.progress(min(dti.front_end_dti / MAX_FRONT_DTI, 1.0))
        st.caption(f"{fmt_p(dti.front_end_dti)} of {MAX_FRONT_DTI}% limit")

        st.write("**Back-End DTI**")
        st.progress(min(dti.back_end_dti / MAX_BACK_DTI, 1.0))
        st.caption(f"{fmt_p(dti.back_end_dti)} of {MAX_BACK_DTI}% limit")

        if dti.notes:
            with st.expander("DTI Notes"):
                for n in dti.notes:
                    st.write(f"- {n}")

    st.markdown("---")

    # ── PDF DOWNLOAD ────────────────────────
    st.subheader("📄 Download Report")

    pdf_bytes = generate_pdf(
        ltv=ltv,
        dti=dti,
        combined=combined,
        analyst_name=st.session_state.user_fullname,
        borrower_name=borrower_name,
    )

    st.download_button(
        label="Download PDF Report",
        data=pdf_bytes,
        file_name=f"LTV_DTI_Report_{borrower_name.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

    # ── REFERENCE (collapsed) ───────────────
    with st.expander("View Risk Tier Reference Tables"):
        r1, r2 = st.columns(2)
        with r1:
            st.write("**LTV Thresholds**")
            rows = []
            for tier, (lo, hi) in LTV_THRESHOLDS.items():
                hi_d = f"{hi}%" if hi < 200 else "100%+"
                rows.append({
                    "": TIER_ICONS.get(tier, ""),
                    "Tier": tier,
                    "Range": f"{lo}% - {hi_d}",
                    "Current": "<--" if tier == ltv.risk_tier else "",
                })
            st.table(rows)
        with r2:
            st.write("**DTI Thresholds**")
            rows = []
            for tier, (lo, hi) in DTI_THRESHOLDS.items():
                hi_d = f"{hi}%" if hi < 200 else "50%+"
                rows.append({
                    "": TIER_ICONS.get(tier, ""),
                    "Tier": tier,
                    "Range": f"{lo}% - {hi_d}",
                    "Current": "<--" if tier == dti.risk_tier else "",
                })
            st.table(rows)


# =============================================================
# SIDEBAR INPUTS
# =============================================================

def sidebar_inputs():
    with st.sidebar:
        st.markdown(f"**{st.session_state.user_fullname}**")
        st.caption(f"Role: {st.session_state.user_role}")

        if st.button("Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("---")
        st.header("Loan Inputs")

        borrower_name = st.text_input("Borrower Name", value="John Doe")

        st.markdown("---")

        # LTV inputs
        st.subheader("Property & Loan")
        loan_amount = st.number_input(
            "Loan Amount ($)", min_value=0.0, value=300000.0,
            step=5000.0, format="%.2f",
        )
        property_value = st.number_input(
            "Property Value ($)", min_value=1.0, value=400000.0,
            step=5000.0, format="%.2f",
        )
        down_payment = st.number_input(
            "Down Payment ($)", min_value=0.0, value=50000.0,
            step=1000.0, format="%.2f",
        )

        st.markdown("---")

        # DTI inputs
        st.subheader("Income & Debts")
        gross_income = st.number_input(
            "Gross Monthly Income ($)", min_value=1.0, value=8000.0,
            step=100.0, format="%.2f",
        )
        other_income = st.number_input(
            "Other Monthly Income ($)", min_value=0.0, value=0.0,
            step=100.0, format="%.2f",
        )
        monthly_debts = st.number_input(
            "Existing Monthly Debts ($)", min_value=0.0, value=500.0,
            step=50.0, format="%.2f",
        )
        proposed_payment = st.number_input(
            "Proposed Monthly Payment ($)", min_value=0.0, value=1500.0,
            step=50.0, format="%.2f",
        )

        st.markdown("---")
        calc = st.button(
            "Calculate & Analyze",
            use_container_width=True,
            type="primary",
        )

    if calc:
        return {
            "borrower_name": borrower_name,
            "loan_amount": loan_amount,
            "property_value": property_value,
            "down_payment": down_payment,
            "gross_income": gross_income,
            "other_income": other_income,
            "monthly_debts": monthly_debts,
            "proposed_payment": proposed_payment,
        }
    return None


# =============================================================
# MAIN
# =============================================================

def main():
    # 1. Auth gate
    if not authenticate():
        st.stop()

    # 2. Sidebar
    inputs = sidebar_inputs()

    # 3. Landing or Results
    if inputs is None:
        show_landing_page()
    else:
        try:
            ltv_in = LTVInput(
                loan_amount=inputs["loan_amount"],
                property_value=inputs["property_value"],
                down_payment=inputs["down_payment"],
            )
            dti_in = DTIInput(
                gross_monthly_income=inputs["gross_income"],
                monthly_debts=inputs["monthly_debts"],
                proposed_monthly_payment=inputs["proposed_payment"],
                other_income=inputs["other_income"],
            )

            ltv_result = calculate_ltv(ltv_in)
            dti_result = calculate_dti(dti_in)
            combined = combined_eligibility(ltv_result, dti_result)

            show_results(ltv_result, dti_result, combined, inputs["borrower_name"])

        except ValueError as e:
            st.error(f"Input Error: {e}")
        except Exception as e:
            st.error(f"Unexpected Error: {e}")


if __name__ == "__main__":
    main()
