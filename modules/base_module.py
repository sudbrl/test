"""
Base Module - Shared base class for all analysis modules.

This module provides the abstract BaseModule class that all analysis
modules must inherit from. It's kept separate to avoid circular imports.
"""

from abc import ABC, abstractmethod
import streamlit as st


class BaseModule(ABC):
    """Abstract base class for all analysis modules."""

    name: str = "Unnamed Module"
    icon: str = "📊"
    key: str = "unknown"

    @property
    def label(self) -> str:
        return f"{self.icon} {self.name}"

    # ──────────────────────────────────────────────────────────────
    # Session-state helpers (namespaced by module key)
    # ──────────────────────────────────────────────────────────────
    def _ns(self, k: str) -> str:
        return f"{self.key}:{k}"

    def sk(self, k: str):
        """Generate a unique Streamlit key for widgets."""
        return self._ns(k)

    def sg(self, k: str, default=None):
        """Get value from session state."""
        return st.session_state.get(self._ns(k), default)

    def ss(self, k: str, v):
        """Set value in session state."""
        st.session_state[self._ns(k)] = v

    def sd(self, k: str, default):
        """Set default value in session state (idempotent)."""
        key = self._ns(k)
        if key not in st.session_state:
            st.session_state[key] = default

    def safe_str(self, s) -> str:
        """Safely convert to string, handling None/NaN."""
        if s is None:
            return ""
        try:
            if pd.isna(s):
                return ""
        except Exception:
            pass
        return str(s)

    # ──────────────────────────────────────────────────────────────
    # Abstract interface - MUST be implemented by subclasses
    # ──────────────────────────────────────────────────────────────
    @abstractmethod
    def init_state(self):
        """Initialize default session state (called once on first load)."""
        pass

    @abstractmethod
    def reset_state(self):
        """Reset module state to defaults (triggered by user action)."""
        pass

    @abstractmethod
    def render_sidebar(self):
        """Render sidebar controls specific to this module."""
        pass

    @abstractmethod
    def render_main(self):
        """Render main content area for this module."""
        pass

    # ──────────────────────────────────────────────────────────────
    # Optional hooks - override if needed
    # ──────────────────────────────────────────────────────────────
    def on_load(self):
        """Called every time the module is selected/navigated to."""
        pass

    def on_unload(self):
        """Called when navigating away from this module."""
        pass


# Import pandas here to make it available to safe_str
try:
    import pandas as pd
except ImportError:
    pd = None
