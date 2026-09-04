# 🚀 How to Use the Loan Analysis Engine

## Quick Start Guide

### 1. **Run Locally**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run frontend.py
```

The app will open at: **http://localhost:8501**

---

### 2. **Login Credentials**

When you first access the app, you'll see a login screen:
- **Password**: `admin123` (default)

---

### 3. **Navigate Between Modules**

Use the **sidebar navigation** on the left:

| Module | Icon | Description |
|--------|------|-------------|
| 🏠 Dashboard | Overview | Summary of all metrics |
| 📊 LTV Analysis | Loan-to-Value | Calculate LTV ratios & risk |
| 💰 DTI Analysis | Debt-to-Income | Calculate DTI ratios & approval |

---

### 4. **Using Each Module**

#### **LTV Analysis Module:**
1. Click **"LTV Analysis"** in sidebar
2. Enter loan details:
   - **Loan Amount**: Total loan requested
   - **Property Value**: Appraised property value
   - **Down Payment**: Optional additional down payment
3. View results:
   - LTV Ratio percentage
   - Risk classification (Low/Medium/High)
   - Visual gauge chart
   - Recommendations

#### **DTI Analysis Module:**
1. Click **"DTI Analysis"** in sidebar
2. Enter financial data:
   - **Gross Monthly Income**: Before taxes
   - **Monthly Debt Payments**: Existing debts
   - **Proposed Housing Payment**: New mortgage payment
3. View results:
   - Front-end DTI (housing only)
   - Back-end DTI (total debt)
   - Approval recommendation
   - Risk assessment

---

## 🔧 Adding New Modules (Easy!)

Want to add a new analysis module like **Credit Score** or **Employment Verification**?

### Step-by-Step:

#### **Step 1: Create Module File**
Create `modules/credit_score.py`:

```python
from frontend import BaseModule
import streamlit as st

class CreditScoreModule(BaseModule):
    name = "Credit Score"
    icon = "📈"
    key = "credit"
    
    def init_state(self):
        self.sd("score", 700)
        self.sd("history", [])
    
    def reset_state(self):
        self.ss("score", 700)
        self.ss("history", [])
        st.rerun()
    
    def render_sidebar(self):
        st.markdown("### ⚙️ Settings")
        score = st.slider(
            "Credit Score",
            300, 850, 
            self.sg("score"),
            key=self.sk("score_slider")
        )
        self.ss("score", score)
    
    def render_main(self):
        st.title(f"{self.icon} {self.name}")
        
        score = self.sg("score")
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="mc">
                <div class="ml">Credit Score</div>
                <div class="mv">{score}</div>
                <div class="ms">{'Excellent' if score > 750 else 'Good' if score > 650 else 'Fair'}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.info("Add your credit score analysis logic here!")
```

#### **Step 2: Register the Module**
Edit `frontend.py` around line 2047:

```python
from modules.ltv_module import LTVModule
from modules.dti_module import DTIModule
from modules.credit_score import CreditScoreModule  # ← Add this

MODULES: list[BaseModule] = [
    LTVModule(),
    DTIModule(),
    CreditScoreModule(),  # ← Add this
    # Add more modules here...
]
```

#### **Step 3: Done!**
Restart the app and your new module appears in the sidebar automatically!

---

## 🌐 Deploy to Streamlit Cloud (GitHub Integration)

### Prerequisites:
- GitHub account
- Your code pushed to a GitHub repository

### Steps:

1. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Go to Streamlit Cloud**:
   - Visit: https://share.streamlit.io
   - Sign in with GitHub

3. **Deploy Your App**:
   - Click **"New App"**
   - Select your repository
   - Branch: `main`
   - Main file path: `frontend.py`
   - Click **"Deploy!"**

4. **Configure Secrets** (Optional):
   - In Streamlit Cloud dashboard, go to your app
   - Click **"Settings"** → **"Secrets"**
   - Add configuration:
     ```toml
     [password]
     hash = "your_hashed_password"
     ```

---

## 📁 Project Structure

```
/workspace
├── frontend.py           # Main app (run this!)
├── requirements.txt      # Dependencies
├── README_MODULES.md     # Developer documentation
├── HOW_TO_USE.md         # This file
└── modules/              # Module directory
    ├── __init__.py
    ├── ltv_module.py     # LTV Analysis
    ├── dti_module.py     # DTI Analysis
    └── template_module.py # Template for new modules
```

---

## 💡 Tips & Best Practices

### For Users:
- ✅ Use the sidebar to switch between analyses
- ✅ Reset individual modules using the "Reset" button in each sidebar
- ✅ Export reports using the download buttons
- ✅ Logout securely when done

### For Developers:
- ✅ Always subclass `BaseModule` for new features
- ✅ Use helper methods: `sk()` (key), `sg()` (get), `ss()` (set), `sd()` (setdefault)
- ✅ Keep modules independent and focused
- ✅ Follow the existing CSS classes for consistent styling:
  - `.mc` - Metric card (light)
  - `.ac` - Aggregate card (dark)
  - `.sb` - Status banner
  - `.sp` - Success state
  - `.sf` - Failure state

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| App won't start | Check `pip install -r requirements.txt` |
| Module not showing | Verify it's added to `MODULES` list in `frontend.py` |
| Login not working | Default password is `admin123` |
| Styling broken | Clear browser cache, hard refresh (Ctrl+Shift+R) |
| Deployment fails | Ensure `frontend.py` is the main file path |

---

## 📞 Need Help?

- Check `README_MODULES.md` for detailed architecture docs
- Review `modules/template_module.py` for a complete example
- Examine existing modules (`ltv_module.py`, `dti_module.py`) for patterns
