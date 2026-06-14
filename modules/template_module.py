"""
[Module Name] Module

Template for creating new analysis modules.
Copy this file and customize for your specific module needs.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

# Import from parent directory
import sys
sys.path.insert(0, '/workspace')
from frontend import BaseModule


class TemplateModule(BaseModule):
    """
    [Module Name] Analysis Module
    
    Replace this docstring with a description of your module's purpose.
    """
    
    # ── Module Metadata ────────────────────────────────────────
    name = "Template"     # Display name in sidebar/title
    icon = "📊"           # Emoji icon
    key = "template"      # Unique identifier (no spaces, lowercase)
    
    # ── Default Configuration ──────────────────────────────────
    _DEFAULT_CONFIG = {
        # Add your default settings here
        "setting1": "default_value",
        "setting2": 0,
    }
    
    # ── Lifecycle Methods ──────────────────────────────────────
    def init_state(self):
        """Initialize module state (called once per session)."""
        self.sd("data", [])
        self.sd("config", self._DEFAULT_CONFIG.copy())
    
    def reset_state(self):
        """Reset module to initial state."""
        for k, v in [
            ("data", []),
            ("config", self._DEFAULT_CONFIG.copy()),
        ]:
            self.ss(k, v)
        st.rerun()
    
    # ── Sidebar Controls ───────────────────────────────────────
    def render_sidebar(self):
        """Render sidebar controls for this module."""
        st.markdown("### 📋 Quick Actions")
        
        if st.button("➕ Add Item", use_container_width=True, key=self.sk("add_btn")):
            self.ss("show_add_form", True)
        
        st.markdown("---")
        
        if st.button("🗑️ Reset", type="secondary", use_container_width=True, key=self.sk("reset")):
            self.reset_state()
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        self._render_settings()
    
    def _render_settings(self):
        """Render settings panel in sidebar."""
        config = self.sg("config", {})
        # Add your setting inputs here
        # Example:
        # value = st.slider("Parameter", 0, 100, config.get("setting2", 0))
        # config["setting2"] = value
        # self.ss("config", config)
    
    # ── Main Content ───────────────────────────────────────────
    def render_main(self):
        """Render main content area."""
        st.title(f"{self.icon} {self.name}")
        
        # Show add form if requested
        if self.sg("show_add_form", False):
            self._render_add_form()
        
        # Dashboard/KPIs
        self._render_dashboard()
        
        # Data table
        self._render_data_table()
    
    def _render_add_form(self):
        """Render form to add new data."""
        with st.expander("📝 Add New Item", expanded=True):
            with st.form(key=self.sk("add_form")):
                # Add your form fields here
                # field1 = st.text_input("Field 1", key=self.sk("field1"))
                # field2 = st.number_input("Field 2", key=self.sk("field2"))
                
                submitted = st.form_submit_button("Add", use_container_width=True)
                if submitted:
                    # Process and save data
                    data = self.sg("data", [])
                    # data.append({...})
                    self.ss("data", data)
                    self.ss("show_add_form", False)
                    st.rerun()
            
            if st.button("Cancel"):
                self.ss("show_add_form", False)
                st.rerun()
    
    def _render_dashboard(self):
        """Render KPI dashboard."""
        st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)
        
        data = self.sg("data", [])
        
        if not data:
            st.info("👆 Add your first item using the button in the sidebar")
            return
        
        # Calculate metrics
        # total = sum(...)
        # avg = ...
        
        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"""
            <div class='mc'>
                <div class='ml'>Total Items</div>
                <div class='mv'>{len(data)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Add more metric cards as needed
    
    def _render_data_table(self):
        """Render data table."""
        st.markdown('<div class="section-header">📋 Data</div>', unsafe_allow_html=True)
        
        data = self.sg("data", [])
        if not data:
            return
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
