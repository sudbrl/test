"""
DTI (Debt-to-Income) Analysis Module

This module handles DTI calculations for loan approval assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import streamlit as st

# Import from parent directory
import sys
sys.path.insert(0, '/workspace')
from frontend import BaseModule


# ── Data Classes ───────────────────────────────────────────────
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


# ── Thresholds ─────────────────────────────────────────────────
DTI_THRESHOLDS = {
    "Excellent":    (0,    28),
    "Good":         (28,   36),
    "Fair":         (36,   43),
    "High":         (43,   50),
    "Unacceptable": (50,   200),
}

MAX_BACK_DTI = 43.0
MAX_FRONT_DTI = 28.0


# ── Calculation Engine ─────────────────────────────────────────
def calculate_dti(input_data: DTIInput) -> DTIResult:
    """Calculate DTI ratios and determine approval status."""
    
    total_income = input_data.gross_monthly_income + input_data.other_income
    total_monthly_debts = input_data.monthly_debts + input_data.proposed_monthly_payment
    
    # Front-end ratio (housing expenses / income)
    front_end_dti = (input_data.proposed_monthly_payment / total_income * 100) if total_income > 0 else 0
    
    # Back-end ratio (all debts / income)
    back_end_dti = (total_monthly_debts / total_income * 100) if total_income > 0 else 0
    
    # Determine risk tier
    risk_tier = "Unacceptable"
    for tier, (low, high) in DTI_THRESHOLDS.items():
        if low <= back_end_dti < high:
            risk_tier = tier
            break
    
    # Approval decision
    is_approved = back_end_dti <= MAX_BACK_DTI and front_end_dti <= MAX_FRONT_DTI
    
    # Generate notes
    notes = []
    if front_end_dti > MAX_FRONT_DTI:
        notes.append(f"Front-end ratio ({front_end_dti:.1f}%) exceeds limit ({MAX_FRONT_DTI}%)")
    if back_end_dti > MAX_BACK_DTI:
        notes.append(f"Back-end ratio ({back_end_dti:.1f}%) exceeds limit ({MAX_BACK_DTI}%)")
    if is_approved:
        notes.append("✅ Meets all DTI requirements")
    
    return DTIResult(
        front_end_dti=front_end_dti,
        back_end_dti=back_end_dti,
        gross_monthly_income=input_data.gross_monthly_income,
        total_income=total_income,
        existing_debts=input_data.monthly_debts,
        proposed_payment=input_data.proposed_monthly_payment,
        total_monthly_debts=total_monthly_debts,
        risk_tier=risk_tier,
        max_allowed_back_dti=MAX_BACK_DTI,
        max_allowed_front_dti=MAX_FRONT_DTI,
        is_approved=is_approved,
        notes=notes,
    )


# ── Module Class ───────────────────────────────────────────────
class DTIModule(BaseModule):
    """DTI Analysis Module - Calculates Debt-to-Income ratios."""
    
    name = "DTI Analysis"
    icon = "💰"
    key = "dti"
    
    def init_state(self):
        self.sd("applications", [])
        self.sd("ctr", 0)
    
    def reset_state(self):
        for k, v in [("applications", []), ("ctr", 0)]:
            self.ss(k, v)
        st.rerun()
    
    def _next_id(self):
        v = self.sg("ctr", 0)
        self.ss("ctr", v + 1)
        return v
    
    def render_sidebar(self):
        st.markdown("### 📋 Quick Actions")
        
        if st.button("➕ New Application", use_container_width=True, key=self.sk("new_app")):
            self.ss("show_form", True)
        
        st.markdown("---")
        
        if st.button("🗑️ Reset All", type="secondary", use_container_width=True, key=self.sk("reset")):
            self.reset_state()
    
    def render_main(self):
        st.title(f"{self.icon} {self.name}")
        
        if self.sg("show_form", False):
            self._render_application_form()
        
        self._render_dashboard()
        self._render_applications_table()
    
    def _render_application_form(self):
        with st.expander("📝 New DTI Application", expanded=True):
            with st.form(key=self.sk("app_form")):
                col1, col2 = st.columns(2)
                
                with col1:
                    applicant = st.text_input("Applicant Name", key=self.sk("applicant"))
                    gross_income = st.number_input(
                        "Gross Monthly Income (₹)", min_value=0.0, step=1000.0,
                        key=self.sk("gross_income")
                    )
                    other_income = st.number_input(
                        "Other Monthly Income (₹)", min_value=0.0, step=1000.0,
                        key=self.sk("other_income")
                    )
                
                with col2:
                    existing_debts = st.number_input(
                        "Existing Monthly Debts (₹)", min_value=0.0, step=100.0,
                        key=self.sk("existing_debts")
                    )
                    proposed_payment = st.number_input(
                        "Proposed EMI (₹)", min_value=0.0, step=100.0,
                        key=self.sk("proposed_emi")
                    )
                
                submitted = st.form_submit_button("Calculate DTI", use_container_width=True)
                
                if submitted:
                    input_data = DTIInput(
                        gross_monthly_income=gross_income,
                        monthly_debts=existing_debts,
                        proposed_monthly_payment=proposed_payment,
                        other_income=other_income,
                    )
                    result = calculate_dti(input_data)
                    
                    apps = self.sg("applications", [])
                    apps.append({
                        "id": self._next_id(),
                        "applicant": applicant or "Unknown",
                        "gross_income": gross_income,
                        "other_income": other_income,
                        "existing_debts": existing_debts,
                        "proposed_emi": proposed_payment,
                        "front_end_dti": result.front_end_dti,
                        "back_end_dti": result.back_end_dti,
                        "risk_tier": result.risk_tier,
                        "is_approved": result.is_approved,
                        "notes": result.notes,
                        "timestamp": datetime.now().isoformat(),
                    })
                    self.ss("applications", apps)
                    self.ss("show_form", False)
                    st.rerun()
            
            if st.button("Cancel"):
                self.ss("show_form", False)
                st.rerun()
    
    def _render_dashboard(self):
        st.markdown('<div class="section-header">📊 Portfolio Overview</div>', unsafe_allow_html=True)
        
        apps = self.sg("applications", [])
        
        if not apps:
            st.info("👆 Add your first application using the button in the sidebar")
            return
        
        total_apps = len(apps)
        approved = sum(1 for a in apps if a["is_approved"])
        rejected = total_apps - approved
        approval_rate = (approved / total_apps * 100) if total_apps > 0 else 0
        
        avg_back_dti = sum(a["back_end_dti"] for a in apps) / total_apps if total_apps > 0 else 0
        
        cols = st.columns(4)
        
        with cols[0]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Total Applications</div>
                <div class='mv'>{total_apps}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Approved</div>
                <div class='mv dp-pos'>{approved}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Rejected</div>
                <div class='mv dp-neg'>{rejected}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[3]:
            dti_status = "✅ Healthy" if avg_back_dti <= 36 else ("⚠️ Monitor" if avg_back_dti <= 43 else "🔴 High Risk")
            status_cls = "dp-pos" if avg_back_dti <= 36 else ("dp-neg" if avg_back_dti > 43 else "")
            st.markdown(f"""
            <div class='ac'>
                <div class='al'>Avg Back-End DTI</div>
                <div class='av'>{avg_back_dti:.1f}%</div>
                <div class='ms {status_cls}'>{dti_status}</div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_applications_table(self):
        st.markdown('<div class="section-header">📋 Applications</div>', unsafe_allow_html=True)
        
        apps = self.sg("applications", [])
        if not apps:
            return
        
        data = []
        for a in apps:
            data.append({
                "ID": a["id"],
                "Applicant": a["applicant"],
                "Income": f"₹{a['gross_income']:,.0f}",
                "Existing Debts": f"₹{a['existing_debts']:,.0f}",
                "Proposed EMI": f"₹{a['proposed_emi']:,.0f}",
                "Front-End": f"{a['front_end_dti']:.1f}%",
                "Back-End": f"{a['back_end_dti']:.1f}%",
                "Risk": a["risk_tier"],
                "Status": "✅ Approved" if a["is_approved"] else "❌ Rejected",
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
