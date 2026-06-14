"""
LTV (Loan-to-Value) Analysis Module

This module handles LTV calculations and analysis for loan collateral assessment.
"""

import copy
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF

# Import from parent directory
import sys
sys.path.insert(0, '/workspace')
from frontend import BaseModule, safe_str


class LTVPdf(FPDF):
    """PDF generator for LTV reports."""
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(30, 27, 75)
        self.cell(0, 10, "LTV ANALYSIS REPORT", 0, 1, "L")
        self.set_draw_color(124, 58, 237)
        self.set_line_width(0.5)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(
            0, 10,
            safe_str(
                f"Page {self.page_no()} | LTV Engine | "
                f"{datetime.now().strftime('%B %d, %Y')}"
            ),
            0, 0, "C",
        )


class LTVModule(BaseModule):
    """LTV Analysis Module - Calculates and validates Loan-to-Value ratios."""
    
    name = "LTV Analysis"
    icon = "🏦"
    key = "ltv"

    _DEFAULT_POLICY = [
        {"Loan Type": "Home Loan",                "Max LTV%": 50.0,  "Unsecured": False},
        {"Loan Type": "Mortgage Loan",            "Max LTV%": 50.0,  "Unsecured": False},
        {"Loan Type": "Auto Loan",                "Max LTV%": None,  "Unsecured": False},
        {"Loan Type": "First Time Home Buyer",    "Max LTV%": 70.0,  "Unsecured": False},
        {"Loan Type": "Personal Term Loan (PTL)", "Max LTV%": 50.0,  "Unsecured": False},
        {"Loan Type": "Education Loan",           "Max LTV%": 50.0,  "Unsecured": False},
        {"Loan Type": "Professional T/L",         "Max LTV%": None,  "Unsecured": False},
        {"Loan Type": "Professional OD",          "Max LTV%": None,  "Unsecured": False},
        {"Loan Type": "Cash Credit",              "Max LTV%": 70.0,  "Unsecured": False},
        {"Loan Type": "Permanent WC Loan",        "Max LTV%": 70.0,  "Unsecured": False},
        {"Loan Type": "Personal OD",              "Max LTV%": 50.0,  "Unsecured": True},
    ]

    def init_state(self):
        self.sd("loans",  [])
        self.sd("fmv",    [])
        self.sd("policy", copy.deepcopy(self._DEFAULT_POLICY))
        self.sd("lctr",   0)
        self.sd("fctr",   0)
        self._migrate()

    def reset_state(self):
        for k, v in [
            ("loans",    []),
            ("fmv",      []),
            ("policy",   copy.deepcopy(self._DEFAULT_POLICY)),
            ("lctr",     0),
            ("fctr",     0),
            ("pdf",      None),
            ("pdf_name", None),
        ]:
            self.ss(k, v)
        st.rerun()

    def _migrate(self):
        """Ensure legacy session data has required fields."""
        fctr = self.sg("fctr", 0)
        for s in self.sg("fmv", []):
            if "id" not in s:
                s["id"] = fctr
                fctr += 1
        self.ss("fctr", fctr)

        lctr = self.sg("lctr", 0)
        for loan in self.sg("loans", []):
            loan.setdefault("collateral_mode", "pool")
            loan.setdefault("assigned_collateral_ids", [])
            if "_loan_id" not in loan:
                loan["_loan_id"] = lctr
                lctr += 1
        self.ss("lctr", lctr)

    def _next_lid(self):
        v = self.sg("lctr", 0)
        self.ss("lctr", v + 1)
        return v

    def _next_fid(self):
        v = self.sg("fctr", 0)
        self.ss("fctr", v + 1)
        return v

    def _calc_ltv(self, loan_amt: float, collaterals: list) -> tuple:
        """Calculate LTV ratio given loan amount and list of collateral values."""
        total_value = sum(c.get("value", 0) for c in collaterals)
        if total_value == 0:
            return 0.0, 0.0
        ltv = (loan_amt / total_value) * 100
        return ltv, total_value

    def _get_policy_limit(self, loan_type: str) -> float:
        """Get max LTV% from policy for a given loan type."""
        for p in self.sg("policy", []):
            if p["Loan Type"].lower() == loan_type.lower():
                return p.get("Max LTV%")
        return None

    def render_sidebar(self):
        """Render sidebar controls for LTV module."""
        st.markdown("### 📋 Quick Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Loan", use_container_width=True, key=self.sk("add_loan_btn")):
                self.ss("show_add_loan", True)
        with col2:
            if st.button("🏷️ Add Collateral", use_container_width=True, key=self.sk("add_coll_btn")):
                self.ss("show_add_coll", True)
        
        st.markdown("---")
        
        if st.button("🗑️ Reset All", type="secondary", use_container_width=True, key=self.sk("reset")):
            self.reset_state()
        
        # Export options
        st.markdown("### 📤 Export")
        if st.button("📄 Generate PDF", use_container_width=True, key=self.sk("pdf")):
            self._generate_pdf()
        
        # Policy management
        st.markdown("---")
        st.markdown("### ⚙️ Policy Settings")
        if st.checkbox("Edit Policy", value=False, key=self.sk("edit_policy")):
            self._render_policy_editor()

    def _render_policy_editor(self):
        """Render policy editor in sidebar."""
        policy = self.sg("policy", [])
        for i, p in enumerate(policy):
            cols = st.columns([2, 1])
            with cols[0]:
                new_type = st.text_input(
                    "Type", value=p["Loan Type"],
                    key=self.sk(f"ptype_{i}"), label_visibility="collapsed"
                )
            with cols[1]:
                new_limit = st.number_input(
                    "Max %", value=p.get("Max LTV%", 50),
                    key=self.sk(f"plimit_{i}"), label_visibility="collapsed"
                )
            p["Loan Type"] = new_type
            p["Max LTV%"] = new_limit if new_limit else None
        self.ss("policy", policy)

    def render_main(self):
        """Render main content area for LTV module."""
        st.title(f"{self.icon} {self.name}")
        
        # Add Loan Form
        if self.sg("show_add_loan", False):
            self._render_add_loan_form()
        
        # Add Collateral Form
        if self.sg("show_add_coll", False):
            self._render_add_collateral_form()
        
        # Dashboard
        self._render_dashboard()
        
        # Loans Table
        self._render_loans_table()
        
        # Collaterals Table
        self._render_collaterals_table()

    def _render_add_loan_form(self):
        """Render form to add a new loan."""
        with st.expander("📝 Add New Loan", expanded=True):
            with st.form(key=self.sk("loan_form")):
                col1, col2 = st.columns(2)
                with col1:
                    loan_type = st.selectbox(
                        "Loan Type",
                        [p["Loan Type"] for p in self.sg("policy", [])],
                        key=self.sk("loan_type")
                    )
                    loan_amount = st.number_input(
                        "Loan Amount", min_value=0.0, step=1000.0,
                        key=self.sk("loan_amt")
                    )
                with col2:
                    borrower = st.text_input("Borrower Name", key=self.sk("borrower"))
                    collateral_mode = st.radio(
                        "Collateral Mode",
                        ["pool", "specific"],
                        horizontal=True,
                        key=self.sk("coll_mode")
                    )
                
                submitted = st.form_submit_button("Add Loan", use_container_width=True)
                if submitted:
                    loans = self.sg("loans", [])
                    loans.append({
                        "_loan_id": self._next_lid(),
                        "type": loan_type,
                        "amount": loan_amount,
                        "borrower": borrower or "Unknown",
                        "collateral_mode": collateral_mode,
                        "assigned_collateral_ids": [],
                        "added": datetime.now().isoformat()
                    })
                    self.ss("loans", loans)
                    self.ss("show_add_loan", False)
                    st.rerun()
            
            if st.button("Cancel"):
                self.ss("show_add_loan", False)
                st.rerun()

    def _render_add_collateral_form(self):
        """Render form to add new collateral."""
        with st.expander("🏷️ Add New Collateral", expanded=True):
            with st.form(key=self.sk("coll_form")):
                col1, col2 = st.columns(2)
                with col1:
                    coll_type = st.selectbox(
                        "Collateral Type",
                        ["Property", "Vehicle", "Equipment", "Inventory", "Securities", "Other"],
                        key=self.sk("coll_type")
                    )
                    coll_value = st.number_input(
                        "Fair Market Value", min_value=0.0, step=1000.0,
                        key=self.sk("coll_value")
                    )
                with col2:
                    coll_desc = st.text_input("Description", key=self.sk("coll_desc"))
                    haircuts = st.slider("Haircut %", 0, 50, 10, key=self.sk("haircut"))
                
                submitted = st.form_submit_button("Add Collateral", use_container_width=True)
                if submitted:
                    fmvs = self.sg("fmv", [])
                    fmvs.append({
                        "id": self._next_fid(),
                        "type": coll_type,
                        "value": coll_value,
                        "description": coll_desc or coll_type,
                        "haircut": haircuts,
                        "adjusted_value": coll_value * (1 - haircuts/100),
                        "added": datetime.now().isoformat()
                    })
                    self.ss("fmv", fmvs)
                    self.ss("show_add_coll", False)
                    st.rerun()
            
            if st.button("Cancel", key=self.sk("cancel_coll")):
                self.ss("show_add_coll", False)
                st.rerun()

    def _render_dashboard(self):
        """Render KPI dashboard."""
        st.markdown('<div class="section-header">📊 Portfolio Overview</div>', unsafe_allow_html=True)
        
        loans = self.sg("loans", [])
        fmvs = self.sg("fmv", [])
        
        if not loans:
            st.info("👆 Add your first loan using the buttons in the sidebar")
            return
        
        total_exposure = sum(l.get("amount", 0) for l in loans)
        total_collateral = sum(f.get("adjusted_value", 0) for f in fmvs)
        avg_ltv = (total_exposure / total_collateral * 100) if total_collateral > 0 else 0
        
        cols = st.columns(4)
        with cols[0]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Total Exposure</div>
                <div class='mv'>₹{total_exposure:,.0f}</div>
                <div class='ms'>{len(loans)} active loans</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Total Collateral</div>
                <div class='mv'>₹{total_collateral:,.0f}</div>
                <div class='ms'>{len(fmvs)} assets pledged</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            ltv_status = "✅ Healthy" if avg_ltv <= 50 else ("⚠️ Monitor" if avg_ltv <= 70 else "🔴 Critical")
            status_cls = "dp-pos" if avg_ltv <= 50 else ("dp-neg" if avg_ltv > 70 else "")
            st.markdown(f"""
            <div class='ac'>
                <div class='al'>Portfolio LTV</div>
                <div class='av'>{avg_ltv:.1f}%</div>
                <div class='ms {status_cls}'>{ltv_status}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[3]:
            unallocated = total_collateral - total_exposure
            alloc_status = "✅ Surplus" if unallocated >= 0 else "🔴 Deficit"
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Coverage Gap</div>
                <div class='mv'>₹{abs(unallocated):,.0f}</div>
                <div class='ms'>{alloc_status}</div>
            </div>
            """, unsafe_allow_html=True)

    def _render_loans_table(self):
        """Render loans data table."""
        st.markdown('<div class="section-header">📋 Active Loans</div>', unsafe_allow_html=True)
        
        loans = self.sg("loans", [])
        fmvs = self.sg("fmv", [])
        
        if not loans:
            return
        
        # Build table data
        data = []
        for loan in loans:
            ltv, coll_value = self._calc_ltv(
                loan.get("amount", 0),
                [f for f in fmvs if f["id"] in loan.get("assigned_collateral_ids", [])]
            )
            policy_limit = self._get_policy_limit(loan.get("type", ""))
            status = "Pass" if (policy_limit is None or ltv <= policy_limit) else "Fail"
            
            data.append({
                "ID": loan.get("_loan_id", 0),
                "Borrower": loan.get("borrower", "Unknown"),
                "Type": loan.get("type", ""),
                "Amount": f"₹{loan.get('amount', 0):,.0f}",
                "Collateral Value": f"₹{coll_value:,.0f}",
                "LTV %": f"{ltv:.1f}%",
                "Policy Limit": f"{policy_limit or 'N/A'}%",
                "Status": status
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    def _render_collaterals_table(self):
        """Render collaterals data table."""
        st.markdown('<div class="section-header">🏷️ Pledged Collaterals</div>', unsafe_allow_html=True)
        
        fmvs = self.sg("fmv", [])
        if not fmvs:
            return
        
        data = []
        for f in fmvs:
            data.append({
                "ID": f["id"],
                "Type": f["type"],
                "Description": f.get("description", ""),
                "FMV": f"₹{f.get('value', 0):,.0f}",
                "Haircut": f"{f.get('haircut', 0)}%",
                "Adj. Value": f"₹{f.get('adjusted_value', 0):,.0f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    def _generate_pdf(self):
        """Generate PDF report."""
        pdf = LTVPdf()
        pdf.add_page()
        pdf.set_font("Arial", "", 11)
        
        loans = self.sg("loans", [])
        fmvs = self.sg("fmv", [])
        
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Loans Summary", 0, 1)
        pdf.set_font("Arial", "", 10)
        
        for loan in loans:
            pdf.cell(0, 8, f"- {loan.get('borrower', 'Unknown')}: ₹{loan.get('amount', 0):,.0f} ({loan.get('type', '')})", 0, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Collaterals", 0, 1)
        pdf.set_font("Arial", "", 10)
        
        for f in fmvs:
            pdf.cell(0, 8, f"- {f.get('type', '')}: ₹{f.get('value', 0):,.0f}", 0, 1)
        
        # Save to session
        filename = f"LTV_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        self.ss("pdf_name", filename)
        self.ss("pdf", pdf.output(dest='S').encode('latin-1'))
        
        st.success(f"PDF generated: {filename}")
