"""
FRONTEND: Streamlit App — LTV & DTI Calculator
  - Secret-based authentication
  - Professional landing page
  - Full analysis with PDF download
"""

import streamlit as st
from ltv_dti import (
    LTVInput, DTIInput,
    calculate_ltv, calculate_dti, combined_eligibility,
    generate_pdf_report,
    LTV_THRESHOLDS, DTI_THRESHOLDS,
    MAX_LTV, MAX_BACK_DTI, MAX_FRONT_DTI, PMI_THRESHOLD,
)

# ═══════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="LTV & DTI Risk Analyzer",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════
# CUSTOM CSS
# ═══════════════════════════════════════════════
st.markdown("""
<style>
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #003366 0%, #0077b6 50%, #00b4d8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
    .hero-sub {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-top: 0;
    }
    .card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #e0e0e0;
        margin-bottom: 16px;
    }
    .card h3 { margin-top: 0; color: #003366; }
    .stat-big {
        font-size: 2.5rem;
        font-weight: 700;
        color: #003366;
        text-align: center;
    }
    .badge-approved {
        background: #d4edda; color: #155724;
        padding: 8px 20px; border-radius: 8px;
        font-weight: 700; font-size: 1.1rem;
        text-align: center; display: inline-block;
    }
    .badge-rejected {
        background: #f8d7da; color: #721c24;
        padding: 8px 20px; border-radius: 8px;
        font-weight: 700; font-size: 1.1rem;
        text-align: center; display: inline-block;
    }
    .footer-note {
        text-align: center; color: #aaa;
        font-size: 0.8rem; margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════

def authenticate():
    """Login using Streamlit Cloud secrets."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.user_fullname = ""
        st.session_state.user_role = ""

    if st.session_state.authenticated:
        return True

    # Load credentials from secrets
    try:
        creds = st.secrets["credentials"]
        valid_users = list(creds["usernames"])
        valid_passwords = list(creds["passwords"])
        valid_names = list(creds["names"])
        valid_roles = list(creds["roles"])
    except Exception:
        st.error("❌ Credentials not configured. Add `[credentials]` to Streamlit secrets.")
        st.stop()

    # Center the login form
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown('<p class="hero-title">🏦</p>', unsafe_allow_html=True)
        st.markdown('<p class="hero-sub">Sign in to continue</p>', unsafe_allow_html=True)
        st.markdown("")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
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
                    st.error("❌ Incorrect password.")
            else:
                st.error("❌ Username not found.")

        st.caption("Demo: `admin` / `admin123`")

    return False


# ═══════════════════════════════════════════════
# LANDING PAGE (shown after login, before calc)
# ═══════════════════════════════════════════════

def show_landing_page():
    # Hero
    st.markdown('<p class="hero-title">LTV & DTI Risk Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Professional mortgage risk assessment with instant PDF reports</p>', unsafe_allow_html=True)
    st.markdown("")

    # Feature cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="card">
            <h3>📊 LTV Analysis</h3>
            <p>Calculate Loan-to-Value ratio with risk tiering, PMI detection, and equity analysis.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="card">
            <h3>💰 DTI Analysis</h3>
            <p>Front-end & back-end Debt-to-Income ratios with qualification check.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="card">
            <h3>📄 PDF Reports</h3>
            <p>Download professional assessment reports for records and compliance.</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="card">
            <h3>🔒 Secure Access</h3>
            <p>Role-based authentication with Streamlit Cloud secrets management.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Risk tier reference
    st.subheader("📋 Risk Tier Reference")
    col_a, col_b = st.columns(2)

    tier_icons = {
        "Excellent": "🟢", "Good": "🟩", "Fair": "🟡",
        "High": "🟠", "Very High": "🔴", "Unacceptable": "⛔",
    }

    with col_a:
        st.write("**LTV Thresholds**")
        ltv_rows = []
        for tier, (lo, hi) in LTV_THRESHOLDS.items():
            display_hi = f"{hi}%" if hi < 200 else "100%+"
            ltv_rows.append({
                "": tier_icons.get(tier, ""),
                "Tier": tier,
                "Range": f"{lo}% – {display_hi}",
            })
        st.table(ltv_rows)
        st.caption(f"Max LTV: **{MAX_LTV}%** · PMI above **{PMI_THRESHOLD}%**")

    with col_b:
        st.write("**DTI Thresholds**")
        dti_rows = []
        for tier, (lo, hi) in DTI_THRESHOLDS.items():
            display_hi = f"{hi}%" if hi < 200 else "50%+"
            dti_rows.append({
                "": tier_icons.get(tier, ""),
                "Tier": tier,
                "Range": f"{lo}% – {display_hi}",
            })
        st.table(dti_rows)
        st.caption(f"Max Front-End DTI: **{MAX_FRONT_DTI}%** · Max Back-End DTI: **{MAX_BACK_DTI}%**")

    st.markdown("---")

    # How it works
    st.subheader("🔄 How It Works")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown("""
        <div class="card">
            <h3>Step 1</h3>
            <p><strong>Enter Details</strong><br>Input loan amount, property value, income, and debts in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
    with h2:
        st.markdown("""
        <div class="card">
            <h3>Step 2</h3>
            <p><strong>Get Analysis</strong><br>Instant LTV & DTI calculations with risk tiering and approval status.</p>
        </div>
        """, unsafe_allow_html=True)
    with h3:
        st.markdown("""
        <div class="card">
            <h3>Step 3</h3>
            <p><strong>Download Report</strong><br>Generate a professional PDF report for your records.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<p class="footer-note">Built with Streamlit · For demonstration purposes only</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# RESULTS PAGE
# ═══════════════════════════════════════════════

TIER_ICONS = {
    "Excellent": "🟢", "Good": "🟩", "Fair": "🟡",
    "High": "🟠", "Very High": "🔴", "Unacceptable": "⛔",
}

def fmt_curr(v): return f"${v:,.2f}"
def fmt_pct(v):  return f"{v:.2f}%"

def show_results(ltv, dti, combined, borrower_name):
    """Render the full results dashboard."""

    # ── OVERALL BANNER ──────────────────────
    st.markdown("")
    if combined["overall_approved"]:
        st.markdown(
            f'<div class="badge-approved" style="width:100%;text-align:center;">'
            f'✅ APPROVED — Profile Strength: {combined["profile_strength"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        reasons_text = " · ".join(combined["rejection_reasons"])
        st.markdown(
            f'<div class="badge-rejected" style="width:100%;text-align:center;">'
            f'❌ NOT APPROVED — {reasons_text}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")

    # ── KEY METRICS ROW ─────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("LTV Ratio", fmt_pct(ltv.ltv_ratio), f"Max {MAX_LTV}%", delta_color="inverse")
    with m2:
        st.metric("Front-End DTI", fmt_pct(dti.front_end_dti), f"Max {MAX_FRONT_DTI}%", delta_color="inverse")
    with m3:
        st.metric("Back-End DTI", fmt_pct(dti.back_end_dti), f"Max {MAX_BACK_DTI}%", delta_color="inverse")
    with m4:
        st.metric("Equity", fmt_curr(ltv.equity))

    st.markdown("---")

    # ── TWO COLUMN DETAIL ───────────────────
    col_ltv, col_dti = st.columns(2, gap="large")

    with col_ltv:
        st.subheader("🏠 LTV Analysis")

        icon = TIER_ICONS.get(ltv.risk_tier, "⚪")
        approved_str = "✅ Approved" if ltv.is_approved else "❌ Not Approved"
        pmi_str = "Yes ⚠️" if ltv.pmi_required else "No ✅"

        st.write(f"**Status:** {approved_str}")
        st.write(f"**Risk Tier:** {icon} **{ltv.risk_tier}**")
        st.write(f"**PMI Required:** {pmi_str}")

        st.markdown("---")
        st.write("**Financial Breakdown**")
        st.table([
            {"Item": "Loan Amount",     "Value": fmt_curr(ltv.loan_amount)},
            {"Item": "Down Payment",    "Value": fmt_curr(ltv.down_payment)},
            {"Item": "Effective Loan",  "Value": fmt_curr(ltv.effective_loan)},
            {"Item": "Property Value",  "Value": fmt_curr(ltv.property_value)},
            {"Item": "Equity",          "Value": fmt_curr(ltv.equity)},
            {"Item": "LTV Ratio",       "Value": fmt_pct(ltv.ltv_ratio)},
        ])

        st.write("**LTV Utilization**")
        st.progress(min(ltv.ltv_ratio / MAX_LTV, 1.0))
        st.caption(f"{fmt_pct(ltv.ltv_ratio)} of {MAX_LTV}% limit")

        if ltv.notes:
            with st.expander("📝 LTV Notes"):
                for n in ltv.notes:
                    st.write(f"• {n}")

    with col_dti:
        st.subheader("💰 DTI Analysis")

        icon = TIER_ICONS.get(dti.risk_tier, "⚪")
        approved_str = "✅ Approved" if dti.is_approved else "❌ Not Approved"

        st.write(f"**Status:** {approved_str}")
        st.write(f"**Risk Tier:** {icon} **{dti.risk_tier}**")

        st.markdown("---")
        st.write("**Income & Debt Breakdown**")
        st.table([
            {"Item": "Gross Monthly Income",  "Value": fmt_curr(dti.gross_monthly_income)},
            {"Item": "Total Income",          "Value": fmt_curr(dti.total_income)},
            {"Item": "Existing Debts",        "Value": fmt_curr(dti.existing_debts)},
            {"Item": "Proposed Payment",      "Value": fmt_curr(dti.proposed_payment)},
            {"Item": "Total Monthly Debts",   "Value": fmt_curr(dti.total_monthly_debts)},
            {"Item": "Front-End DTI",         "Value": fmt_pct(dti.front_end_dti)},
            {"Item": "Back-End DTI",          "Value": fmt_pct(dti.back_end_dti)},
        ])

        st.write("**Front-End DTI**")
        st.progress(min(dti.front_end_dti / MAX_FRONT_DTI, 1.0))
        st.caption(f"{fmt_pct(dti.front_end_dti)} of {MAX_FRONT_DTI}% limit")

        st.write("**Back-End DTI**")
        st.progress(min(dti.back_end_dti / MAX_BACK_DTI, 1.0))
        st.caption(f"{fmt_pct(dti.back_end_dti)} of {MAX_BACK_DTI}% limit")

        if dti.notes:
            with st.expander("📝 DTI Notes"):
                for n in dti.notes:
                    st.write(f"• {n}")

    st.markdown("---")

    # ── PDF DOWNLOAD ────────────────────────
    st.subheader("📄 Download Report")
    pdf_bytes = generate_pdf_report(
        ltv=ltv,
        dti=dti,
        combined=combined,
        analyst_name=st.session_state.user_fullname,
        borrower_name=borrower_name,
    )
    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_bytes,
        file_name=f"LTV_DTI_Report_{borrower_name.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )


# ═══════════════════════════════════════════════
# SIDEBAR — INPUT FORM
# ═══════════════════════════════════════════════

def sidebar_inputs():
    """Renders sidebar inputs. Returns None until user clicks Calculate."""

    with st.sidebar:
        # User info
        st.markdown(f"**👤 {st.session_state.user_fullname}**")
        st.caption(f"Role: {st.session_state.user_role}")
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("---")
        st.title("📝 Loan Inputs")

        # Borrower
        borrower_name = st.text_input("Borrower Name", value="John Doe")

        st.markdown("---")

        # ── LTV ─────────────────────────────
        st.subheader("🏠 Property & Loan")
        loan_amount = st.number_input("Loan Amount ($)", min_value=0.0, value=300_000.0, step=5_000.0, format="%.2f")
        property_value = st.number_input("Property Value ($)", min_value=1.0, value=400_000.0, step=5_000.0, format="%.2f")
        down_payment = st.number_input("Down Payment ($)", min_value=0.0, value=50_000.0, step=1_000.0, format="%.2f")

        st.markdown("---")

        # ── DTI ─────────────────────────────
        st.subheader("💰 Income & Debts")
        gross_income = st.number_input("Gross Monthly Income ($)", min_value=1.0, value=8_000.0, step=100.0, format="%.2f")
        other_income = st.number_input("Other Monthly Income ($)", min_value=0.0, value=0.0, step=100.0, format="%.2f")
        monthly_debts = st.number_input("Existing Monthly Debts ($)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
        proposed_payment = st.number_input("Proposed Monthly Payment ($)", min_value=0.0, value=1_500.0, step=50.0, format="%.2f")

        st.markdown("---")
        calc = st.button("🔍 Calculate & Analyze", use_container_width=True, type="primary")

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


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    # 1) Authentication gate
    if not authenticate():
        st.stop()

    # 2) Sidebar inputs
    inputs = sidebar_inputs()

    # 3) Landing page or results
    if inputs is None:
        show_landing_page()
    else:
        try:
            ltv_input = LTVInput(
                loan_amount=inputs["loan_amount"],
                property_value=inputs["property_value"],
                down_payment=inputs["down_payment"],
            )
            dti_input = DTIInput(
                gross_monthly_income=inputs["gross_income"],
                monthly_debts=inputs["monthly_debts"],
                proposed_monthly_payment=inputs["proposed_payment"],
                other_income=inputs["other_income"],
            )

            ltv_result = calculate_ltv(ltv_input)
            dti_result = calculate_dti(dti_input)
            combined = combined_eligibility(ltv_result, dti_result)

            show_results(ltv_result, dti_result, combined, inputs["borrower_name"])

        except ValueError as e:
            st.error(f"⚠️ Input Error: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected Error: {e}")

if __name__ == "__main__":
    main()
