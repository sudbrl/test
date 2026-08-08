import streamlit as st
from supabase import create_client, Client
import os
from datetime import datetime
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rich Data Entry & Search App",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global Styles */
    .main { padding-top: 1rem; }
    .stTextInput > div > div > input { border-radius: 8px; }
    .stTextArea textarea { border-radius: 8px; }
    .stSelectbox > div > div { border-radius: 8px; }
    div[data-testid="stForm"] { border-radius: 12px; padding: 1.5rem; }
    
    /* Card Styles */
    .record-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .record-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    /* Tag Styles */
    .tag {
        background: #e8f0fe;
        color: #1a73e8;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-left: 8px;
        display: inline-block;
    }
    .tag-status-active {
        background: #e6f4ea;
        color: #1e8e3e;
    }
    .tag-status-pending {
        background: #fef7e0;
        color: #f9ab00;
    }
    .tag-status-inactive {
        background: #fce8e6;
        color: #d93025;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e8e8e8;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a73e8;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Search Box */
    .search-box {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    /* Button Styles */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Header Styles */
    h1, h2, h3 {
        color: #2c3e50;
    }
    
    /* Form Container */
    .form-container {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ── SIMPLE LOGIN SYSTEM ──────────────────────────────────────────────────────
def check_login(username, password):
    correct_user = st.secrets.get("APP_USERNAME")
    correct_pass = st.secrets.get("APP_PASSWORD")
    return username == correct_user and password == correct_pass

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_page():
    # Use columns to make the login box small and centered
    _, col2, _ = st.columns([1, 1.2, 1])
    
    with col2:
        st.write("") # Spacing
        st.write("")
        st.markdown("<h2 style='text-align: center;'>🔐 Secure Login</h2>", unsafe_allow_html=True)
        st.write("")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if check_login(username, password):
                st.session_state.authenticated = True
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid username or password")

# ── STOP HERE IF NOT LOGGED IN ───────────────────────────────────────────────
if not st.session_state.authenticated:
    login_page()
    st.stop()


# ── Supabase connection ───────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        st.error("Missing Supabase credentials")
        st.stop()

    return create_client(url, key)

def get_client():
    return get_supabase()


# ── DB helpers ────────────────────────────────────────────────────────────────
def insert_record(client, data: dict):
    return client.table("records").insert(data).execute()

def fetch_all(client):
    return client.table("records").select("*").order("created_at", desc=True).execute()

def search_records(client, query: str, field: str):
    col = field.lower().replace(" ", "_")
    return (
        client.table("records")
        .select("*")
        .ilike(col, f"%{query}%")
        .order("created_at", desc=True)
        .execute()
    )

def delete_record(client, record_id: int):
    return client.table("records").delete().eq("id", record_id).execute()

def update_record(client, record_id: int, data: dict):
    return client.table("records").update(data).eq("id", record_id).execute()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚀 Rich Data Manager")
    st.write("Professional Data Management System")
    st.divider()

    page = st.radio(
        "Navigation",
        ["➕ Add Record", "🔍 Search & Browse", "📊 Analytics Dashboard"],
        label_visibility="collapsed"
    )

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

client = get_client()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 - ADD RECORD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "➕ Add Record":
    st.header("➕ Add New Record")
    st.markdown("Fill out the details below to add a new entity to the database.")

    with st.form("entry_form", clear_on_submit=True):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        # Two-column layout for professional form appearance
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="Enter full name")
            category = st.selectbox("Category", ["Customer", "Lead", "Partner", "Vendor", "Other"])
            phone = st.text_input("Phone Number", placeholder="+1 (555) 000-0000")
            
        with col2:
            email = st.text_input("Email *", placeholder="email@example.com")
            status = st.selectbox("Status", ["Active", "Inactive", "Pending"])
            company = st.text_input("Company", placeholder="Company name")
        
        description = st.text_area("Description", placeholder="Add additional notes or details...", height=100)
        
        # Additional fields in a third column section
        col3, col4 = st.columns(2)
        with col3:
            priority = st.select_slider("Priority", options=["Low", "Medium", "High", "Critical"], value="Medium")
        with col4:
            follow_up = st.date_input("Follow-up Date", min_value=datetime.now().date())

        st.write("") # Spacing
        submitted = st.form_submit_button("💾 Save Record", type="primary", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if not name or not email:
            st.warning("⚠️ Name and Email are required fields.")
        else:
            # Build data dict with only non-empty values for optional fields
            data = {
                "name": name,
                "email": email,
                "category": category,
                "status": status,
                "description": description if description else "",
                "phone": phone if phone else "",
                "company": company if company else "",
                "priority": priority,
            }
            # Only add follow_up if it's set
            if follow_up:
                data["follow_up"] = follow_up.isoformat()
            
            try:
                insert_record(client, data)
                st.success(f"✅ Record for **{name}** saved successfully!")
            except Exception as e:
                st.error(f"❌ Error saving record: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 - SEARCH & BROWSE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Search & Browse":
    st.header("🔍 Search & Browse Records")
    
    # Advanced search filters
    with st.expander("🎯 Advanced Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            filter_category = st.multiselect("Category", ["Customer", "Lead", "Partner", "Vendor", "Other"])
        with filter_col2:
            filter_status = st.multiselect("Status", ["Active", "Inactive", "Pending"])
        with filter_col3:
            filter_priority = st.multiselect("Priority", ["Low", "Medium", "High", "Critical"])
    
    # Search bar layout
    s_col1, s_col2, s_col3 = st.columns([3, 1, 1])
    with s_col1:
        search_query = st.text_input("Search query", placeholder="🔍 Search records by name, email, or company...", label_visibility="collapsed")
    with s_col2:
        search_field = st.selectbox("Field", ["Name", "Email", "Category", "Status", "Company"], label_visibility="collapsed")
    with s_col3:
        sort_order = st.selectbox("Sort", ["Newest", "Oldest", "Name A-Z"], label_visibility="collapsed")

    st.divider()

    # Fetch and filter records
    if search_query:
        result = search_records(client, search_query, search_field)
        records = result.data
    else:
        records = fetch_all(client).data
    
    # Apply filters
    if records:
        if filter_category:
            records = [r for r in records if r.get("category") in filter_category]
        if filter_status:
            records = [r for r in records if r.get("status") in filter_status]
        if filter_priority:
            records = [r for r in records if r.get("priority") in filter_priority]
        
        # Sort records
        if sort_order == "Newest":
            records = sorted(records, key=lambda x: x.get("created_at", ""), reverse=True)
        elif sort_order == "Oldest":
            records = sorted(records, key=lambda x: x.get("created_at", ""), reverse=False)
        elif sort_order == "Name A-Z":
            records = sorted(records, key=lambda x: x.get("name", "").lower())

    if records:
        st.info(f"📊 Found **{len(records)}** record(s)")
        
        for r in records:
            # Get status class for styling
            status_class = f"tag-status-{r.get('status', 'inactive').lower()}"
            
            # Professional Card UI
            st.markdown(f"""
            <div class="record-card">
                <div>
                    <h4 style="margin:0; padding:0; color:#2c3e50;">{r.get('name', 'N/A')}</h4>
                    <small style="color:#666;">📧 {r.get('email', 'N/A')}</small>
                    {'<br><small style="color:#666;">🏢 ' + r.get('company', '') + '</small>' if r.get('company') else ''}
                    {'<br><small style="color:#666;">📱 ' + r.get('phone', '') + '</small>' if r.get('phone') else ''}
                </div>
                <div>
                    <span class="tag">{r.get('category', 'N/A')}</span>
                    <span class="tag {status_class}">{r.get('status', 'N/A')}</span>
                    <span class="tag" style="background: #fff3cd; color: #856404;">{r.get('priority', 'Medium')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Manage Record"):
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_name = st.text_input("Name", r.get("name", ""), key=f"n{r['id']}")
                    new_email = st.text_input("Email", r.get("email", ""), key=f"e{r['id']}")
                    new_company = st.text_input("Company", r.get("company", ""), key=f"c{r['id']}")
                with edit_col2:
                    new_category = st.selectbox("Category", ["Customer", "Lead", "Partner", "Vendor", "Other"], 
                                              index=["Customer", "Lead", "Partner", "Vendor", "Other"].index(r.get("category", "Other")),
                                              key=f"cat{r['id']}")
                    new_status = st.selectbox("Status", ["Active", "Inactive", "Pending"],
                                            index=["Active", "Inactive", "Pending"].index(r.get("status", "Pending")),
                                            key=f"s{r['id']}")
                    new_priority = st.select_slider("Priority", options=["Low", "Medium", "High", "Critical"], 
                                                  value=r.get("priority", "Medium"), key=f"p{r['id']}")

                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("✅ Update Record", key=f"u{r['id']}", use_container_width=True, type="primary"):
                        update_record(client, r["id"], {
                            "name": new_name,
                            "email": new_email,
                            "company": new_company,
                            "category": new_category,
                            "status": new_status,
                            "priority": new_priority,
                            "description": r.get("description", ""),
                            "phone": r.get("phone", ""),
                            "follow_up": r.get("follow_up", ""),
                        })
                        st.rerun()
                with btn_col2:
                    if st.button("🗑️ Delete Record", key=f"d{r['id']}", use_container_width=True):
                        delete_record(client, r["id"])
                        st.rerun()
                st.write("")
    else:
        st.info("📭 No records found matching your criteria.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 - ANALYTICS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics Dashboard":
    st.header("📊 Analytics Dashboard")
    st.write("Comprehensive overview of your data inventory and insights.")

    records = fetch_all(client).data
    total = len(records)
    
    if total > 0:
        # Status breakdown
        active = sum(1 for r in records if r.get("status") == "Active")
        pending = sum(1 for r in records if r.get("status") == "Pending")
        inactive = sum(1 for r in records if r.get("status") == "Inactive")
        
        # Category breakdown
        categories = {}
        for r in records:
            cat = r.get("category", "Other")
            categories[cat] = categories.get(cat, 0) + 1
        
        # Priority breakdown
        priorities = {}
        for r in records:
            pri = r.get("priority", "Medium")
            priorities[pri] = priorities.get(pri, 0) + 1
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent = sum(1 for r in records if r.get("created_at") and 
                    datetime.fromisoformat(r["created_at"].replace('Z', '+00:00')).replace(tzinfo=None) > seven_days_ago)
        
        # Display metrics in cards
        st.write("")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total}</div>
                <div class="metric-label">Total Records</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #1e8e3e;">{active}</div>
                <div class="metric-label">Active</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #f9ab00;">{pending}</div>
                <div class="metric-label">Pending</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m_col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #d93025;">{recent}</div>
                <div class="metric-label">This Week</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
        st.divider()
        
        # Charts section
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("📈 By Category")
            if categories:
                df_cat = pd.DataFrame(list(categories.items()), columns=["Category", "Count"])
                st.bar_chart(df_cat.set_index("Category"))
        
        with chart_col2:
            st.subheader("🎯 By Priority")
            if priorities:
                df_pri = pd.DataFrame(list(priorities.items()), columns=["Priority", "Count"])
                st.bar_chart(df_pri.set_index("Priority"))
        
        st.divider()
        
        # Status distribution pie chart
        st.subheader("📊 Status Distribution")
        status_data = {"Active": active, "Pending": pending, "Inactive": inactive}
        df_status = pd.DataFrame(list(status_data.items()), columns=["Status", "Count"])
        st.bar_chart(df_status.set_index("Status"))
        
    else:
        st.info("📭 No records available. Start by adding some records!")
        st.markdown("""
        <div class="metric-card" style="margin-top: 1rem;">
            <div class="metric-value">0</div>
            <div class="metric-label">Total Records</div>
        </div>
        """, unsafe_allow_html=True)
