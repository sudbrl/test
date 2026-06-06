# ============================================================
# FRONTEND: Streamlit App for LTV & DTI Calculator
# ============================================================

import streamlit as st
from ltv_dti import (
    LTVInput, DTIInput,
    calculate_ltv, calculate_dti, combined_eligibility,
    LTV_THRESHOLDS, DTI_THRESHOLDS,
    MAX_LTV, MAX_DTI, MAX_FRONT_END_DTI, PMI_THRESHOLD,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="LTV & DTI Calculator",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

TIER_COLORS = {
    "Excellent":    "🟢",
    "Good":         "🟩",
    "Fair":         "🟡",
    "High":         "🟠",
    "Very High":    "🔴",
    "Unacceptable": "⛔",
}

def tier_badge(tier: str) -> str:
    icon = TIER_COLORS.get(tier, "⚪")
    return f"{icon} **{tier}**"

def format_currency(value: float) -> str:
    return f"${value:,.2f}"

def format_percent(value: float) -> str:
    return f"{value:.2f}%"


# ─────────────────────────────────────────────
# SIDEBAR — INPUTS
# ─────────────────────────────────────────────

with st.sidebar:
    st.title("🏦 Loan Calculator")
    st.caption("Enter your loan details below")

    st.markdown("---")

    # ── LTV INPUTS ──────────────────────────
    st.subheader("🏠 LTV Inputs")

    loan_amount = st.number_input(
        "Loan Amount ($)",
        min_value=0.0,
        value=300_000.0,
        step=1_000.0,
        format="%.2f",
    )
    property_value = st.number_input(
        "Property Value ($)",
        min_value=1.0,
        value=400_000.0,
        step=1_000.0,
        format="%.2f",
    )
    down_payment = st.number_input(
        "Down Payment ($)",
        min_value=0.0,
        value=50_000.0,
        step=1_000.0,
        format="%.2f",
    )

    st.markdown("---")

    # ── DTI INPUTS ──────────────────────────
    st.subheader("💰 DTI Inputs")

    gross_income = st.number_input(
        "Gross Monthly Income ($)",
        min_value=1.0,
        value=8_000.0,
        step=100.0,
        format="%.2f",
    )
    other_income = st.number_input(
        "Other Monthly Income ($)",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
    )
    monthly_debts = st.number_input(
        "Existing Monthly Debts ($)",
        min_value=0.0,
        value=500.0,
        step=50.0,
        format="%.2f",
    )
    proposed_payment = st.number_input(
        "Proposed Monthly Payment ($)",
        min_value=0.0,
        value=1_500.0,
        step=50.0,
        format="%.2f",
    )

    st.markdown("---")
    calculate_btn = st.button("🔍 Calculate", use_container_width=True, type="primary")


# ─────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────

st.title("🏦 LTV & DTI Mortgage Calculator")
st.caption("Analyze your Loan-to-Value and Debt-to-Income ratios instantly.")

if not calculate_btn:
    # ── WELCOME / REFERENCE SCREEN ──────────
    st.info("👈 Enter your loan details in the sidebar and click **Calculate**.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 LTV Thresholds")
        rows = []
        for tier, (low, high) in LTV_THRESHOLDS.items():
            icon = TIER_COLORS.get(tier, "⚪")
            rows.append({"Risk Tier": f"{icon} {tier}", "LTV Range": f"{low}% – {high}%"})
        st.table(rows)
        st.caption(f"Max Allowed LTV: **{MAX_LTV}%** | PMI Required above: **{PMI_THRESHOLD}%**")

    with col2:
        st.subheader("📊 DTI Thresholds")
        rows = []
        for tier, (low, high) in DTI_THRESHOLDS.items():
            icon = TIER_COLORS.get(tier, "⚪")
            rows.append({"Risk Tier": f"{icon} {tier}", "DTI Range": f"{low}% – {high}%"})
        st.table(rows)
        st.caption(
            f"Max Back-End DTI: **{MAX_DTI}%** | "
            f"Max Front-End DTI: **{MAX_FRONT_END_DTI}%**"
        )

else:
    # ── RUN CALCULATIONS ────────────────────
    try:
        ltv_input = LTVInput(
            loan_amount=loan_amount,
            property_value=property_value,
            down_payment=down_payment,
        )
        dti_input = DTIInput(
            gross_monthly_income=gross_income,
            monthly_debts=monthly_debts,
            proposed_monthly_payment=proposed_payment,
            other_income=other_income,
        )

        ltv = calculate_ltv(ltv_input)
        dti = calculate_dti(dti_input)
        combined = combined_eligibility(ltv, dti)

    except ValueError as e:
        st.error(f"⚠️ Input Error: {e}")
        st.stop()

    # ══════════════════════════════════════
    # OVERALL RESULT BANNER
    # ══════════════════════════════════════
    if combined["overall_approved"]:
        st.success(f"## {combined['summary']} — Loan meets LTV & DTI requirements.")
    else:
        st.error(f"## {combined['summary']} — Loan does not meet requirements.")
        for reason in combined["rejection_reasons"]:
            st.write(f"- {reason}")

    st.markdown("---")

    # ══════════════════════════════════════
    # TWO COLUMNS: LTV | DTI
    # ══════════════════════════════════════
    col_ltv, col_dti = st.columns(2, gap="large")

    # ─── LTV COLUMN ────────────────────────
    with col_ltv:
        st.subheader("🏠 LTV Analysis")

        # Big metric
        st.metric(
            label="LTV Ratio",
            value=format_percent(ltv.ltv_ratio),
            delta=f"Max: {MAX_LTV}%",
            delta_color="inverse",
        )

        # Status
        approved_text = "✅ Approved" if ltv.is_approved else "❌ Not Approved"
        st.write(f"**Status:** {approved_text}")
        st.write(f"**Risk Tier:** {tier_badge(ltv.risk_tier)}")
        st.write(f"**PMI Required:** {'Yes ⚠️' if ltv.pmi_required else 'No ✅'}")

        st.markdown("---")

        # Breakdown table
        st.write("**Breakdown**")
        st.table([
            {"Item": "Loan Amount",     "Value": format_currency(ltv.loan_amount)},
            {"Item": "Down Payment",    "Value": format_currency(ltv.down_payment)},
            {"Item": "Property Value",  "Value": format_currency(ltv.property_value)},
            {"Item": "Equity",          "Value": format_currency(ltv.equity)},
            {"Item": "LTV Ratio",       "Value": format_percent(ltv.ltv_ratio)},
        ])

        # Progress bar
        st.write("**LTV vs Max Allowed**")
        progress = min(ltv.ltv_ratio / MAX_LTV, 1.0)
        st.progress(progress)
        st.caption(f"{format_percent(ltv.ltv_ratio)} of {MAX_LTV}% limit")

        # Notes
        if ltv.notes:
            st.markdown("**Notes:**")
            for note in ltv.notes:
                st.write(note)

    # ─── DTI COLUMN ────────────────────────
    with col_dti:
        st.subheader("💰 DTI Analysis")

        # Big metrics
        m1, m2 = st.columns(2)
        with m1:
            st.metric(
                label="Front-End DTI",
                value=format_percent(dti.front_end_dti),
                delta=f"Max: {MAX_FRONT_END_DTI}%",
                delta_color="inverse",
            )
        with m2:
            st.metric(
                label="Back-End DTI",
                value=format_percent(dti.back_end_dti),
                delta=f"Max: {MAX_DTI}%",
                delta_color="inverse",
            )

        # Status
        approved_text = "✅ Approved" if dti.is_approved else "❌ Not Approved"
        st.write(f"**Status:** {approved_text}")
        st.write(f"**Risk Tier:** {tier_badge(dti.risk_tier)}")

        st.markdown("---")

        # Breakdown table
        total_income = gross_income + other_income
        st.write("**Breakdown**")
        st.table([
            {"Item": "Gross Monthly Income",  "Value": format_currency(dti.gross_monthly_income)},
            {"Item": "Other Income",          "Value": format_currency(other_income)},
            {"Item": "Total Income",          "Value": format_currency(total_income)},
            {"Item": "Existing Debts",        "Value": format_currency(dti.gross_monthly_income - dti.gross_monthly_income + monthly_debts)},
            {"Item": "Proposed Payment",      "Value": format_currency(dti.proposed_payment)},
            {"Item": "Total Monthly Debts",   "Value": format_currency(dti.total_monthly_debts)},
        ])

        # Progress bars
        st.write("**Front-End DTI vs Max**")
        st.progress(min(dti.front_end_dti / MAX_FRONT_END_DTI, 1.0))
        st.caption(f"{format_percent(dti.front_end_dti)} of {MAX_FRONT_END_DTI}% limit")

        st.write("**Back-End DTI vs Max**")
        st.progress(min(dti.back_end_dti / MAX_DTI, 1.0))
        st.caption(f"{format_percent(dti.back_end_dti)} of {MAX_DTI}% limit")

        # Notes
        if dti.notes:
            st.markdown("**Notes:**")
            for note in dti.notes:
                st.write(note)

    # ══════════════════════════════════════
    # REFERENCE TABLES (collapsed)
    # ══════════════════════════════════════
    with st.expander("📖 View Risk Tier Reference Tables"):
        c1, c2 = st.columns(2)
        with c1:
            st.write("**LTV Thresholds**")
            rows = []
            for tier, (low, high) in LTV_THRESHOLDS.items():
                icon = TIER_COLORS.get(tier, "⚪")
                rows.append({
                    "Risk Tier": f"{icon} {tier}",
                    "LTV Range": f"{low}% – {high}%",
                    "Current": "◀" if tier == ltv.risk_tier else "",
                })
            st.table(rows)

        with c2:
            st.write("**DTI Thresholds**")
            rows = []
            for tier, (low, high) in DTI_THRESHOLDS.items():
                icon = TIER_COLORS.get(tier, "⚪")
                rows.append({
                    "Risk Tier": f"{icon} {tier}",
                    "DTI Range": f"{low}% – {high}%",
                    "Current": "◀" if tier == dti.risk_tier else "",
                })
            st.table(rows)
