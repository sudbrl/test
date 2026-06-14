# Loan Analysis Engine - Modular Architecture

## Overview

This application uses a modular architecture that makes it easy to add new analysis modules like LTV, DTI, Credit Score, etc. Each module is self-contained and follows a consistent pattern.

## Project Structure

```
/workspace/
├── frontend.py              # Main application + BaseModule class
├── modules/                 # Module packages directory
│   ├── __init__.py          # Package initialization
│   ├── ltv_module.py        # LTV Analysis module
│   ├── dti_module.py        # DTI Analysis module
│   └── template_module.py   # Template for creating new modules
└── README_MODULES.md        # This file
```

## Design Philosophy

### Modern Industry Design
- **Clean Typography**: Inter font family with JetBrains Mono for numbers
- **Professional Color Palette**: Slate/Blue tones (Tailwind-inspired)
- **Card-Based Layout**: Clear visual hierarchy with subtle shadows
- **Responsive Components**: Consistent spacing and sizing

### Modular Architecture
- **BaseModule Class**: Abstract base class defining the module interface
- **Namespaced State**: Each module has isolated session state
- **Auto-Registration**: Modules automatically appear in navigation
- **Independent Development**: Modules can be developed separately

## Adding a New Module (3 Steps)

### Step 1: Create Module File

Create a new file in `modules/` directory:

```python
# modules/credit_score.py

from frontend import BaseModule
import streamlit as st

class CreditScoreModule(BaseModule):
    name = "Credit Score"
    icon = "📈"
    key = "credit"
    
    def init_state(self):
        self.sd("scores", [])
    
    def reset_state(self):
        self.ss("scores", [])
        st.rerun()
    
    def render_sidebar(self):
        st.markdown("### 📋 Actions")
        if st.button("➕ Add Score"):
            self.ss("show_form", True)
    
    def render_main(self):
        st.title(f"{self.icon} {self.name}")
        st.write("Your credit score analysis here...")
```

### Step 2: Register the Module

Edit `frontend.py` in the MODULE REGISTRY section:

```python
from modules.credit_score import CreditScoreModule

MODULES: list[BaseModule] = [
    LTVModule(),
    DTIModule(),
    CreditScoreModule(),  # ← Add here
]
```

### Step 3: Done!

The sidebar navigation auto-updates. Your module is ready to use.

## BaseModule Interface

All modules must implement these methods:

| Method | Purpose | Required |
|--------|---------|----------|
| `name` | Display name | Yes (class attribute) |
| `icon` | Emoji icon | Yes (class attribute) |
| `key` | Unique identifier | Yes (class attribute) |
| `init_state()` | Initialize session state | Yes |
| `reset_state()` | Clear all state | Yes |
| `render_sidebar()` | Sidebar controls | Yes |
| `render_main()` | Main content area | Yes |

### Helper Methods

The BaseModule provides these helpers for state management:

```python
self.sk("key")           # Get namespaced session key string
self.sg("key", default)  # Get value from session state
self.ss("key", value)    # Set value in session state  
self.sd("key", default)  # Set default (only if not exists)
```

## Best Practices

### 1. State Management
- Always use helper methods (`sd`, `sg`, `ss`) for state access
- Namespace your state keys to avoid collisions
- Implement proper reset functionality

### 2. UI Components
- Use the provided CSS classes for consistency:
  - `.mc` - Light metric card
  - `.ac` - Dark aggregate card
  - `.section-header` - Section dividers
  - `.dp-pos` / `.dp-neg` - Positive/negative text colors

### 3. Code Organization
- Keep business logic separate from UI rendering
- Use private methods (prefix `_`) for internal helpers
- Document your module with clear docstrings

## Example: Complete Module

See `modules/template_module.py` for a complete template with:
- Form handling
- Dashboard/KPIs
- Data tables
- Settings panel

## Styling Guidelines

The modern design uses:
- **Font**: Inter (UI), JetBrains Mono (numbers)
- **Colors**: 
  - Primary: Blue (#2563eb)
  - Success: Green (#16a34a)
  - Warning: Amber (#d97706)
  - Error: Red (#dc2626)
- **Cards**: White background, subtle shadows, rounded corners
- **Spacing**: Consistent padding (1.5rem standard)

## Questions?

Refer to existing modules (LTV, DTI) for implementation examples.
