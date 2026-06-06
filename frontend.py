"""
Loan Analysis Engine  ·  Modular Architecture
═══════════════════════════════════════════════════════════════════
ADDING A NEW MODULE  (3 steps — that's it)
───────────────────────────────────────────────────────────────────
1. Subclass BaseModule and implement the abstract methods
2. Add an instance to MODULES list  (search "MODULE REGISTRY")
3. Done — navigation auto-updates

Minimal template
─────────────────
class CreditScoreModule(BaseModule):
    name = "Credit Score"   # sidebar / title label
    icon = "📈"             # emoji prefix
    key  = "cs"             # unique short id — no spaces

    def init_state(self):
        self.sd("loans", [])        # sd = setdefault (idempotent)

    def reset_state(self):
        self.ss("loans", [])        # ss = set
        st.rerun()

    def render_sidebar(self):
        st.markdown("### ⚙️ Settings")
        val = st.slider("Min Score", 300, 850, 650, key=self.sk("thr"))
        self.ss("threshold", val)

    def render_main(self):
        st.title(self.label)
        st.metric("Threshold", self.sg("threshold"))  # sg = get
═══════════════════════════════════════════════════════════════════
"""

import copy
import hmac
from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF

# ──────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Loan Analysis Engine",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────
# SHARED CSS
# ──────────────────────────────────────────────────────────────────
_STYLES = """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:#1a1f36;letter-spacing:-.01em}
.block-container{max-width:96%!important;padding-top:1.5rem!important}
.main{background:linear-gradient(135deg,#f0f4ff 0%,#faf5ff 100%)}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input{
  border-radius:10px!important;border:1px solid #e2e8f0!important;
  padding:.65rem .9rem!important;font-size:.95rem!important;background:#f8fafc!important;transition:all .2s}
div[data-testid="stTextInput"] input:focus,div[data-testid="stNumberInput"] input:focus{
  border-color:#7c3aed!important;box-shadow:0 0 0 3px rgba(124,58,237,.12)!important;background:#fff!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#1e1b4b 0%,#312e81 100%);box-shadow:4px 0 24px rgba(0,0,0,.18)}
[data-testid="stSidebar"] *{color:#e0e7ff}
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],[data-testid="stSidebar"] input{
  background:rgba(255,255,255,.95)!important;color:#1e1b4b!important;font-weight:600}
div.stButton>button[kind="primary"]{background-color:#7c3aed!important;border-color:#7c3aed!important;
  color:#fff!important;border-radius:8px;font-weight:600;transition:all .2s ease}
div.stButton>button[kind="primary"]:hover{background-color:#6d28d9!important;transform:translateY(-1px)}
.mc{background:linear-gradient(135deg,#fff,#f5f3ff);padding:1.25rem 1.5rem;
  border-radius:14px;border:1px solid #ddd6fe;box-shadow:0 4px 14px rgba(124,58,237,.08)}
.ml{font-size:.75rem;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.35rem}
.mv{font-size:1.7rem;font-weight:700;color:#1e1b4b;font-family:'DM Mono',monospace;line-height:1.1}
.ms{font-size:.8rem;font-weight:600;margin-top:.3rem}
.ac{background:linear-gradient(135deg,#1e1b4b,#312e81);padding:1.25rem 1.5rem;
  border-radius:14px;border:1px solid #4338ca;box-shadow:0 4px 14px rgba(30,27,75,.18)}
.al{font-size:.75rem;font-weight:700;color:#a5b4fc;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.35rem}
.av{font-size:1.7rem;font-weight:700;color:#fff;font-family:'DM Mono',monospace;line-height:1.1}
.sb{padding:.9rem 1.5rem;border-radius:12px;font-weight:700;font-size:1rem;text-align:center;margin:1.25rem 0}
.sp{background:#d1fae5;border:2px solid #059669;color:#065f46}
.sf{background:#fee2e2;border:2px solid #dc2626;color:#991b1b}
.gw{margin-top:.4rem;height:7px;background:#e2e8f0;border-radius:99px;overflow:hidden}
.go{height:100%;border-radius:99px;background:#059669}
.gx{height:100%;border-radius:99px;background:#f59e0b}
.gf{height:100%;border-radius:99px;background:#dc2626}
.dp-pos{color:#059669}
.dp-neg{color:#dc2626}
.is{background:#fff;padding:2rem;border-radius:16px;border-left:4px solid #3b82f6;
  box-shadow:0 8px 32px rgba(0,0,0,.08);margin-bottom:2rem}
</style>"""

# ──────────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────────
_AUTH_CSS = """<style>
#MainMenu,footer,header{visibility:hidden}
.stApp{background:linear-gradient(135deg,#f0f4ff,#faf5ff)!important}
.block-container{max-width:480px!important;padding-top:2rem!important}
.lc{background:#fff;border-radius:16px;padding:1.75rem;
  box-shadow:0 4px 24px rgba(124,58,237,.12);border:1px solid #ede9fe}
.lb{display:inline-block;background:#ede9fe;color:#6d28d9;font-size:.65rem;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;padding:.15rem .6rem;border-radius:99px}
.er{background:#fef2f2;border:1.5px solid #fca5a5;color:#991b1b;border-radius:8px;
  padding:.75rem;font-size:.85rem;font-weight:600;margin-top:.75rem;text-align:center;line-height:1.5}
.tp{background:#fee2e2;padding:.2rem .4rem;border-radius:4px;font-family:monospace;font-weight:700}
div[data-testid="stTextInput"]>div>div>input{border-radius:8px!important;border:1.5px solid #e5e7eb!important}
div[data-testid="stTextInput"]>div>div>input:focus{border-color:#7c3aed!important}
div[data-testid="stTextInput"] label{display:none!important}
div.stButton>button{background:linear-gradient(135deg,#7c3aed,#6d28d9)!important;
  color:#fff!important;border:none!important;border-radius:8px!important;
  font-weight:700!important;width:100%!important}
</style>"""


def _check_creds(u: str, p: str) -> bool:
    """Constant-time credential check to prevent timing attacks."""
    try:
        stored = str(st.secrets["passwords"].get(u.strip(), "")).strip()
        # hmac.compare_digest prevents timing-based user enumeration
        return hmac.compare_digest(stored, p.strip()) and stored != ""
    except Exception:
        return False


def _all_pwds() -> list:
    try:
        return [str(v).strip() for v in st.secrets["passwords"].values()]
    except Exception:
        return []


def _show_login():
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("_lerr", "")
    with st.container():
        st.markdown("""
        <div class="lc">
          <div style="text-align:center;margin-bottom:1.25rem">
            <div style="font-size:2.25rem">🏦</div>
            <div style="font-size:1.25rem;font-weight:800;color:#1e1b4b">Loan Analysis Engine</div>
            <span class="lb">Secure Sign In</span>
          </div>""", unsafe_allow_html=True)

        st.markdown(
            '<span style="font-size:.7rem;font-weight:700;color:#374151;'
            'text-transform:uppercase">👤 Username</span>',
            unsafe_allow_html=True,
        )
        u = st.text_input(
            "u", placeholder="admin", key="_lu", label_visibility="collapsed"
        )
        st.markdown(
            '<span style="font-size:.7rem;font-weight:700;color:#374151;'
            'text-transform:uppercase">🔒 Password</span>',
            unsafe_allow_html=True,
        )
        p = st.text_input(
            "p", placeholder="Password", type="password",
            key="_lp", label_visibility="collapsed",
        )

        if st.button("Sign In", key="_lbtn", use_container_width=True):
            u_s, p_s = u.strip(), p.strip()
            if not u_s:
                st.session_state["_lerr"] = (
                    "⚠️ Enter username: <span class='tp'>admin</span>"
                )
            elif not p_s:
                st.session_state["_lerr"] = "⚠️ Please enter your password."
            elif _check_creds(u_s, p_s):
                st.session_state.update(
                    authenticated=True, auth_user=u_s, _lerr=""
                )
            elif u_s in _all_pwds():
                # User typed their password into the username field
                st.session_state["_lerr"] = (
                    f"❌ <b>Password entered as username!</b><br>"
                    f"Username: <span class='tp'>admin</span> · "
                    f"Password: <span class='tp'>{u_s}</span>"
                )
            else:
                st.session_state["_lerr"] = (
                    f"❌ Invalid credentials for '{u_s}'"
                )
            st.rerun()

        if err := st.session_state.get("_lerr", ""):
            st.markdown(f'<div class="er">{err}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;font-size:.7rem;color:#9ca3af;margin-top:1rem">'
            "🔐 Secured by Streamlit Cloud</div></div>",
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────
# SHARED UTILITIES
# ──────────────────────────────────────────────────────────────────

def safe_str(t) -> str:
    """Encode text as latin-1 safe string for FPDF."""
    _MAP = {
        "\u2014": "-",  "\u2013": "-",  "\u2018": "'",  "\u2019": "'",
        "\u201c": '"',  "\u201d": '"',  "\u2022": "*",  "\u00a0": " ",
        "\u20b9": "Rs.", "\u2265": ">=", "\u2264": "<=", "\u2026": "...",
    }
    s = str(t)
    for c, r in _MAP.items():
        s = s.replace(c, r)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _gc(v: float, warn: float = 50.0, fail: float = 65.0) -> str:
    """Return CSS gauge-fill class based on value thresholds."""
    return "go" if v <= warn else ("gx" if v <= fail else "gf")


def _kpi(label: str, value: str, sub: str = "", sub_cls: str = "") -> str:
    """Render a metric card (white/purple)."""
    sub_html = f"<div class='ms {sub_cls}'>{sub}</div>" if sub else ""
    return (
        f"<div class='mc'>"
        f"<div class='ml'>{label}</div>"
        f"<div class='mv'>{value}</div>"
        f"{sub_html}</div>"
    )


def _agg_kpi(label: str, value: str, sub: str = "") -> str:
    """Render an aggregate metric card (dark/indigo)."""
    sub_html = (
        f"<div style='font-size:.8rem;font-weight:600;margin-top:.3rem;"
        f"color:#c7d2fe'>{sub}</div>"
        if sub
        else ""
    )
    return (
        f"<div class='ac'>"
        f"<div class='al'>{label}</div>"
        f"<div class='av'>{value}</div>"
        f"{sub_html}</div>"
    )


def _status_banner(ok: bool, msg_pass: str, msg_fail: str):
    cls = "sp" if ok else "sf"
    msg = msg_pass if ok else msg_fail
    st.markdown(f"<div class='sb {cls}'>{msg}</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# BASE MODULE
# ══════════════════════════════════════════════════════════════════

class BaseModule(ABC):
    """
    All modules subclass this.  State keys are automatically namespaced
    by self.key to prevent collisions between modules.

    Helpers
    -------
    sk(name)          → namespaced session-state key string
    sg(name, default) → get from session state
    ss(name, value)   → set in session state
    sd(name, default) → setdefault (only sets if key absent)
    """

    name: str = ""  # e.g. "LTV Analysis"
    icon: str = ""  # e.g. "🏦"
    key: str = ""   # unique short id, e.g. "ltv"

    def sk(self, n: str) -> str:
        return f"_m_{self.key}_{n}"

    def sg(self, n: str, d=None):
        return st.session_state.get(self.sk(n), d)

    def ss(self, n: str, v):
        st.session_state[self.sk(n)] = v

    def sd(self, n: str, v):
        st.session_state.setdefault(self.sk(n), v)

    @property
    def label(self) -> str:
        return f"{self.icon} {self.name}"

    def init_state(self):
        """Called once per session; override to set default state."""
        pass

    def reset_state(self):
        """Called by Reset button; override to clear module state."""
        pass

    @abstractmethod
    def render_sidebar(self):
        """Render sidebar controls for this module."""
        ...

    @abstractmethod
    def render_main(self):
        """Render main content area for this module."""
        ...


# ══════════════════════════════════════════════════════════════════
# LTV MODULE
# ══════════════════════════════════════════════════════════════════

class _LTVPdf(FPDF):
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

    # ── Lifecycle ──────────────────────────────────────────────
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

    # ── Private helpers ────────────────────────────────────────
    def _migrate(self):
        """Ensure legacy session data has required fields."""
        fctr = self.sg("fctr", 0)
        for s in self.sg("fmv", []):
            if "id" not in s:
                # FIX: Only assign a new id if the key is genuinely missing;
                # do NOT call _next_fid() (which would increment the counter)
                # for entries that already have an id.
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

    def _next_fid(self) -> int:
        n = self.sg("fctr", 0)
        self.ss("fctr", n + 1)
        return n

    def _next_lid(self) -> int:
        n = self.sg("lctr", 0)
        self.ss("lctr", n + 1)
        return n

    def _policy_dict(self) -> dict:
        return {
            p["Loan Type"]: (None if p["Unsecured"] else p["Max LTV%"])
            for p in self.sg("policy", [])
        }

    def _assigned_in_use(self) -> set:
        return {
            cid
            for loan in self.sg("loans", [])
            for cid in loan.get("assigned_collateral_ids", [])
            if loan.get("collateral_mode") == "assigned"
        }

    def _coll_names(self, ids: list) -> list:
        m = {s["id"]: s["Plot"] for s in self.sg("fmv", []) if "id" in s}
        return [m[i] for i in ids if i in m]

    # ── Portfolio Engine ───────────────────────────────────────
    def _run_engine(self) -> tuple:
        loans  = self.sg("loans", [])
        fmvs   = [s for s in self.sg("fmv", []) if "id" in s]
        policy = self._policy_dict()

        # Build collateral → loan usage map
        coll_usage = {s["id"]: [] for s in fmvs}
        for loan in loans:
            if loan.get("collateral_mode") == "assigned":
                for cid in loan.get("assigned_collateral_ids", []):
                    if cid in coll_usage:
                        coll_usage[cid].append(loan["_loan_id"])

        assigned_ids = {cid for cid, users in coll_usage.items() if users}
        pool_ids     = {s["id"] for s in fmvs if s["id"] not in assigned_ids}
        fmv_map      = {s["id"]: s["Amount"] for s in fmvs}

        # Proportionally split shared collateral FMV among loans that reference it
        loan_shares = {l["_loan_id"]: {} for l in loans}
        for cid in assigned_ids:
            user_lids = coll_usage[cid]
            cfmv      = fmv_map.get(cid, 0.0)
            if len(user_lids) == 1:
                loan_shares[user_lids[0]][cid] = cfmv
            else:
                sharing = [l for l in loans if l["_loan_id"] in user_lids]
                tot_p   = sum(l["Principal"] for l in sharing)
                for sl in sharing:
                    share = (
                        cfmv * (sl["Principal"] / tot_p)
                        if tot_p > 0
                        else cfmv / len(sharing)
                    )
                    loan_shares[sl["_loan_id"]][cid] = share

        assigned_fmv = {
            l["_loan_id"]: (
                sum(loan_shares.get(l["_loan_id"], {}).values())
                if l.get("collateral_mode") == "assigned"
                else 0.0
            )
            for l in loans
        }

        # Waterfall pool allocation
        # FIX: High-priority (50% LTV) loans are funded first; within the same
        # priority tier loans are sorted by descending principal so larger
        # facilities are satisfied before smaller ones.  The last loan in the
        # waterfall no longer receives ALL remaining FMV unconditionally —
        # it receives only what it actually needs (capped by what remains).
        pool_fmv = sum(s["Amount"] for s in fmvs if s["id"] in pool_ids)

        def _sort_key(l):
            m = policy.get(l["Loan Type"])
            # Unsecured loans (m is None) go last; among secured, lower max-LTV
            # (higher priority) goes first; ties broken by descending principal.
            if m is None:
                return (2, 0)
            return (0 if m <= 50 else 1, -l["Principal"])

        pool_parts = sorted(
            [
                l for l in loans
                if policy.get(l["Loan Type"]) is not None
                and l.get("collateral_mode", "pool") == "pool"
            ],
            key=_sort_key,
        )

        rem        = pool_fmv
        pool_alloc = {}
        for loan in pool_parts:
            lid = loan["_loan_id"]
            m   = policy.get(loan["Loan Type"])
            if m is None:
                pool_alloc[lid] = 0.0
                continue
            # Required FMV for this loan given its max-LTV and already-assigned FMV
            req   = max(0.0, loan["Principal"] / (m / 100.0) - assigned_fmv.get(lid, 0.0))
            # FIX: never give more than needed, even for the last loan
            alloc = min(req, rem)
            pool_alloc[lid] = alloc
            rem   = max(0.0, rem - alloc)

        total_fmv = sum(s["Amount"] for s in fmvs)
        results   = []
        for loan in loans:
            lid  = loan["_loan_id"]
            lt   = loan["Loan Type"]
            m    = policy.get(lt)
            p    = loan["Principal"]
            mode = loan.get("collateral_mode", "pool")

            if m is None:
                results.append({
                    **loan,
                    "Max LTV%":             None,
                    "Assigned FMV":         0.0,
                    "Pool FMV":             0.0,
                    "Total FMV":            0.0,
                    "LTV%":                 None,
                    "Pass_Status":          True,
                    "Is_Unsecured":         True,
                    "Collateral_Mode":      mode,
                    "Collateral_Names":     [],
                    "Shared_Collateral_Ids": [],
                })
                continue

            afmv   = assigned_fmv.get(lid, 0.0)
            pfmv   = pool_alloc.get(lid, 0.0)
            tot    = afmv + pfmv
            ltv    = (p / tot * 100) if tot > 0 else float("inf")
            shared = [
                c for c in loan.get("assigned_collateral_ids", [])
                if len(coll_usage.get(c, [])) > 1
            ]
            results.append({
                **loan,
                "Max LTV%":              m,
                "Assigned FMV":          afmv,
                "Pool FMV":              pfmv,
                "Total FMV":             tot,
                "LTV%":                  ltv,
                "Pass_Status":           (ltv <= m) if tot > 0 else False,
                "Is_Unsecured":          False,
                "Collateral_Mode":       mode,
                "Collateral_Names":      self._coll_names(
                    loan.get("assigned_collateral_ids", [])
                ),
                "Shared_Collateral_Ids": shared,
            })

        sec     = [r for r in results if not r["Is_Unsecured"]]
        tot_sp  = sum(r["Principal"] for r in sec)
        tot_af  = sum(r["Total FMV"] for r in sec)
        wtd_ltv = (tot_sp / tot_af * 100) if tot_af > 0 else 0.0
        agg_ltv = (tot_sp / total_fmv * 100) if total_fmv > 0 else 0.0

        return results, {
            "total_fmv":               total_fmv,
            "pool_fmv":                pool_fmv,
            "remaining_pool":          rem,
            "total_exposure":          sum(r["Principal"] for r in results),
            "total_secured_principal": tot_sp,
            "total_alloc_fmv":         tot_af,
            "wtd_ltv":                 wtd_ltv,
            "aggregate_ltv":           agg_ltv,
            "overall_pass":            all(r["Pass_Status"] for r in results),
            "collateral_usage":        coll_usage,
            "assigned_collateral_ids": assigned_ids,
            "pool_collateral_ids":     pool_ids,
        }

    # ── PDF Generation ─────────────────────────────────────────
    def _gen_pdf(
        self, client: str, results: list, summary: dict
    ) -> bytes:
        fmvs = self.sg("fmv", [])
        pdf  = _LTVPdf()
        pdf.add_page()
        tf = summary["total_fmv"]
        te = summary["total_exposure"]
        wl = summary["wtd_ltv"]
        al = summary["aggregate_ltv"]
        ok = summary["overall_pass"]

        def kv(lbl, val):
            pdf.set_font("Arial", "", 10)
            pdf.cell(80, 6, safe_str(lbl), 0, 0)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, safe_str(str(val)), 0, 1)

        # Executive summary
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 8, "EXECUTIVE SUMMARY", 0, 1)
        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        kv("Client Name:",               client)
        kv("Analysis Date:",             datetime.now().strftime("%B %d, %Y"))
        kv("Total Loan Exposure:",        f"Rs. {te:,.2f}")
        kv("Total Collateral FMV:",       f"Rs. {tf:,.2f}")
        kv("Aggregate LTV%:",             f"{al:.2f}%")
        kv("Weighted Avg LTV% (secured):", f"{wl:.2f}%")
        pdf.ln(3)
        if ok:
            pdf.set_text_color(5, 150, 105)
        else:
            pdf.set_text_color(220, 38, 38)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(
            0, 7,
            safe_str(
                f"Assessment Result: {'APPROVED' if ok else 'DECLINED'} — "
                f"{'Within' if ok else 'Exceeds'} LTV Limits"
            ),
            0, 1,
        )
        pdf.set_text_color(0, 0, 0)

        # Collateral table
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 8, "COLLATERAL / FMV SOURCES", 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        cu   = summary["collateral_usage"]
        ai   = summary["assigned_collateral_ids"]
        id2t = {l["_loan_id"]: l["Loan Type"] for l in self.sg("loans", [])}
        cw   = [70, 35, 25, 60]
        pdf.set_font("Arial", "B", 7)
        pdf.set_fill_color(237, 233, 254)
        for hdr, w in zip(
            ["Plot / Property", "FMV (Rs.)", "Type", "Assigned To"], cw
        ):
            pdf.cell(w, 7, hdr, 1, 0, "C", True)
        pdf.ln()
        for i, s in enumerate(fmvs):
            fid  = s.get("id", i)
            fill = i % 2 == 0
            if fill:
                pdf.set_fill_color(248, 245, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            users   = cu.get(fid, [])
            asgn_to = (
                ", ".join(id2t.get(u, str(u)) for u in users)
                if users
                else "Pool (shared)"
            )
            pdf.set_font("Arial", "", 7)
            pdf.cell(cw[0], 6, safe_str(s["Plot"]),              1, 0, "L", fill)
            pdf.cell(cw[1], 6, f"{s['Amount']:,.0f}",            1, 0, "R", fill)
            pdf.cell(cw[2], 6, "Assigned" if fid in ai else "Pool", 1, 0, "C", fill)
            pdf.cell(cw[3], 6, safe_str(asgn_to[:30]),           1, 1, "L", fill)
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(237, 233, 254)
        pdf.cell(cw[0], 6, "TOTAL",         1, 0, "R", True)
        pdf.cell(cw[1], 6, f"{tf:,.0f}",    1, 0, "R", True)
        pdf.cell(cw[2] + cw[3], 6, "",      1, 1, "",  True)

        # Facility table
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 8, "FACILITY LTV BREAKDOWN", 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        cw2  = [44, 22, 22, 22, 18, 18, 18, 26]
        hdrs = [
            "Facility Type", "Principal", "Asgn.FMV", "Pool FMV",
            "Tot.FMV", "LTV%", "MaxLTV", "Status",
        ]
        pdf.set_font("Arial", "B", 7)
        pdf.set_fill_color(237, 233, 254)
        for hdr, w in zip(hdrs, cw2):
            pdf.cell(w, 7, hdr, 1, 0, "C", True)
        pdf.ln()

        def _dsort(r):
            m = r.get("Max LTV%")
            return (2, 0) if m is None else (0 if m <= 50 else 1, -r.get("Principal", 0))

        for idx, row in enumerate(sorted(results, key=_dsort)):
            fill = idx % 2 == 0
            if fill:
                pdf.set_fill_color(248, 245, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            u  = row.get("Is_Unsecured", False)
            lv = row.get("LTV%")
            ml = row.get("Max LTV%")
            cells = [
                (row["Loan Type"],                                       cw2[0], "L"),
                (f"{row['Principal']:,.0f}",                             cw2[1], "R"),
                ("N/A" if u else f"{row['Assigned FMV']:,.0f}",          cw2[2], "R"),
                ("N/A" if u else f"{row['Pool FMV']:,.0f}",              cw2[3], "R"),
                ("N/A" if u else f"{row['Total FMV']:,.0f}",             cw2[4], "R"),
                ("N/A" if (u or lv is None) else f"{lv:.1f}%",           cw2[5], "C"),
                ("N/A" if (u or ml is None) else f"{ml:.0f}%",           cw2[6], "C"),
            ]
            pdf.set_font("Arial", "", 7)
            for val, w, aln in cells:
                pdf.cell(w, 6, safe_str(val), 1, 0, aln, fill)
            st_txt = "PASS" if row["Pass_Status"] else "FAIL"
            if st_txt == "PASS":
                pdf.set_text_color(5, 150, 105)
            else:
                pdf.set_text_color(220, 38, 38)
            pdf.cell(cw2[7], 6, st_txt, 1, 1, "C", fill)
            pdf.set_text_color(0, 0, 0)

        # FIX: handle both str and bytes return from fpdf.output()
        out = pdf.output(dest="S")
        return out.encode("latin-1") if isinstance(out, str) else bytes(out)

    # ── Sidebar ────────────────────────────────────────────────
    def render_sidebar(self):
        fmv   = self.sg("fmv", [])
        loans = self.sg("loans", [])

        st.markdown(
            "<div style='background:rgba(255,255,255,.08);border-radius:8px;"
            "padding:.5rem .85rem;font-size:.78rem;color:#c7d2fe;margin-bottom:.25rem'>"
            "📌 <b>Step 1</b>: Add properties &nbsp;→&nbsp; <b>Step 2</b>: Add loans</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # ── Step 1: Properties
        st.markdown("### 📍 Step 1 — Add Properties")
        plot    = st.text_input(
            "Plot / Property Reference",
            placeholder="e.g. Plot No. 42-B",
            key=self.sk("sb_plot"),
        )
        fmv_amt = st.number_input(
            "Fair Market Value (Rs.)", min_value=0.0, step=50000.0,
            key=self.sk("sb_fmv"),
        )
        if st.button("➕ Add Property", type="primary", key=self.sk("add_fmv")):
            if fmv_amt <= 0:
                st.error("FMV must be > 0")
            elif not plot.strip():
                st.error("Enter a property reference")
            else:
                fmv.append({
                    "id":     self._next_fid(),
                    "Plot":   plot.strip(),
                    "Amount": fmv_amt,
                })
                self.ss("fmv", fmv)
                st.success(f"✅ Added: {plot.strip()}")
                st.rerun()

        if fmv:
            aiu     = self._assigned_in_use()
            pool_av = sum(s["Amount"] for s in fmv if s.get("id") not in aiu)
            tot_fmv = sum(s["Amount"] for s in fmv)
            st.markdown(
                f"<div style='background:rgba(255,255,255,.1);border-radius:8px;"
                f"padding:.6rem .9rem;margin:.5rem 0;font-size:.85rem'>"
                f"💰 Total: <b>Rs.{tot_fmv:,.0f}</b><br>"
                f"🌊 Pool: <b>Rs.{pool_av:,.0f}</b><br>"
                f"📦 Properties: <b>{len(fmv)}</b></div>",
                unsafe_allow_html=True,
            )
            for s in fmv:
                sid    = s.get("id", "?")
                in_use = sid in aiu
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(
                        f"<div style='font-size:.78rem;color:#c7d2fe;padding:.2rem 0'>"
                        f"{'🔒' if in_use else '🌊'} <b>[{sid}]</b> {s.get('Plot','')}<br>"
                        f"&nbsp;&nbsp;Rs.{s.get('Amount', 0):,.0f}</div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("🗑", key=self.sk(f"delfmv_{sid}")):
                        self.ss("fmv", [x for x in fmv if x.get("id") != sid])
                        # Remove deleted property from any loan's assigned list
                        for loan in self.sg("loans", []):
                            asgn = loan.get("assigned_collateral_ids", [])
                            if sid in asgn:
                                asgn.remove(sid)
                        st.rerun()

        st.markdown("---")

        # ── Step 2: Loans
        st.markdown("### 📋 Step 2 — Add Loan Facility")
        policy  = self._policy_dict()
        lt_list = list(policy.keys())
        if lt_list:
            l_type  = st.selectbox(
                "Facility Type", lt_list, key=self.sk("sb_ltype")
            )
            l_amt   = st.number_input(
                "Principal (Rs.)", step=10000.0, min_value=0.0,
                key=self.sk("sb_lamt"),
            )
            max_ltv    = policy.get(l_type)
            sel_colls  = []
            coll_mode  = "pool"

            if max_ltv is not None:
                plbl = "High Priority (50%)" if max_ltv <= 50 else "Normal (70%)"
                st.markdown(
                    f"<div style='background:rgba(255,255,255,.08);border-radius:6px;"
                    f"padding:.4rem .75rem;font-size:.76rem;color:#a5b4fc;margin:.3rem 0'>"
                    f"📊 Max LTV: <b>{max_ltv:.0f}%</b> · {plbl}</div>",
                    unsafe_allow_html=True,
                )
                use_ded = st.checkbox(
                    "🔒 Assign dedicated collateral(s)?",
                    key=self.sk("sb_ded"),
                    help=(
                        "✅ Checked → link specific properties.\n"
                        "☐ Unchecked → draw from shared pool."
                    ),
                )
                coll_mode = "assigned" if use_ded else "pool"
                if use_ded:
                    if fmv:
                        aiu  = self._assigned_in_use()
                        opts = {}
                        for s in fmv:
                            sid  = s.get("id")
                            base = (
                                f"[{sid}] {s.get('Plot','?')} "
                                f"— Rs.{s.get('Amount', 0):,.0f}"
                            )
                            opts[f"{'⚠️' if sid in aiu else '✅'} {base}"] = sid
                        sel_labels = st.multiselect(
                            "Select Collateral(s)",
                            list(opts.keys()),
                            key=self.sk("sb_selc"),
                        )
                        sel_colls = [opts[lbl] for lbl in sel_labels]
                        if any(c in aiu for c in sel_colls):
                            st.warning(
                                "⚠️ Some properties already assigned — "
                                "FMV split proportionally."
                            )
                    else:
                        st.warning("⚠️ Add properties first (Step 1)")
            else:
                st.markdown(
                    "<div style='background:rgba(245,158,11,.15);border-left:3px solid #f59e0b;"
                    "padding:.5rem .75rem;border-radius:6px;font-size:.8rem;"
                    "color:#fde68a;margin-top:.5rem'>"
                    "⚡ Unsecured — no collateral required</div>",
                    unsafe_allow_html=True,
                )

            if st.button("Add to Portfolio", type="primary", key=self.sk("add_loan")):
                if l_amt <= 0:
                    st.error("Principal must be > 0")
                elif coll_mode == "assigned" and not sel_colls:
                    st.error("Select at least one property for dedicated mode")
                else:
                    lid = self._next_lid()
                    loans.append({
                        "Loan Type":               l_type,
                        "Principal":               l_amt,
                        "_loan_id":                lid,
                        "collateral_mode":         coll_mode,
                        "assigned_collateral_ids": sel_colls,
                    })
                    self.ss("loans", loans)
                    st.success(
                        f"✅ Added {l_type} "
                        f"({'🔒 Dedicated' if coll_mode == 'assigned' else '🌊 Pool'})"
                    )
                    st.rerun()

        if loans:
            st.markdown("---")
            st.markdown("**Current Portfolio**")
            for loan in loans:
                icon = {"pool": "🌊", "assigned": "🔒"}.get(
                    loan.get("collateral_mode", "pool"), "🌊"
                )
                st.markdown(
                    f"<div style='font-size:.76rem;color:#c7d2fe;padding:.15rem 0'>"
                    f"{icon} {loan['Loan Type']}<br>"
                    f"&nbsp;&nbsp;Rs.{loan['Principal']:,.0f}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        if st.button("🔄 Reset LTV Data", type="primary", key=self.sk("reset")):
            self.reset_state()

    # ── Main ───────────────────────────────────────────────────
    def render_main(self):
        st.title(self.label)
        st.markdown(
            "Multi-collateral LTV — assign dedicated collateral or draw "
            "from the shared waterfall pool."
        )

        loans = self.sg("loans", [])
        fmv   = self.sg("fmv", [])

        if not loans:
            self._landing()
            return
        if not fmv:
            st.warning(
                "⚠️ Add at least one property in the sidebar (Step 1)."
            )
            return

        results, s = self._run_engine()

        self._kpi_row(s)
        _status_banner(
            s["overall_pass"],
            "✅ PORTFOLIO APPROVED — All Facilities Within LTV Limits",
            "⚠️ PORTFOLIO DECLINED — One or More Facilities Exceed Maximum LTV",
        )
        self._matrix(results, s)
        self._table(results, s)
        self._gauges(results, s)
        self._manage_loans()
        self._pdf_export(results, s)

    def _landing(self):
        st.markdown("""
        <div style="max-width:960px;margin:0 auto;padding:2rem 1rem">
          <div style="background:linear-gradient(135deg,#1e1b4b,#4338ca);border-radius:20px;
               padding:3rem 2.5rem;text-align:center;
               box-shadow:0 8px 40px rgba(67,56,202,.25);margin-bottom:2rem">
            <div style="font-size:3.5rem;margin-bottom:.75rem">🏦</div>
            <div style="font-size:2.2rem;font-weight:800;color:#fff;margin-bottom:.5rem">
              LTV Analysis Engine
            </div>
            <div style="font-size:1rem;color:#c7d2fe;max-width:560px;margin:0 auto 1.5rem">
              Institutional-grade LTV analysis with multi-collateral waterfall allocation,
              dedicated assignment, and one-click PDF reporting.
            </div>
            <div style="display:flex;justify-content:center;gap:.6rem;flex-wrap:wrap">
              <span style="background:rgba(255,255,255,.15);color:#e0e7ff;
                border:1px solid rgba(255,255,255,.2);border-radius:99px;
                padding:.3rem .85rem;font-size:.75rem;font-weight:600">✅ Multi-Collateral</span>
              <span style="background:rgba(255,255,255,.15);color:#e0e7ff;
                border:1px solid rgba(255,255,255,.2);border-radius:99px;
                padding:.3rem .85rem;font-size:.75rem;font-weight:600">🌊 Waterfall Pool</span>
              <span style="background:rgba(255,255,255,.15);color:#e0e7ff;
                border:1px solid rgba(255,255,255,.2);border-radius:99px;
                padding:.3rem .85rem;font-size:.75rem;font-weight:600">🔒 Dedicated Assignment</span>
              <span style="background:rgba(255,255,255,.15);color:#e0e7ff;
                border:1px solid rgba(255,255,255,.2);border-radius:99px;
                padding:.3rem .85rem;font-size:.75rem;font-weight:600">📄 PDF Export</span>
            </div>
          </div>
          <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:14px;
               padding:1.25rem 1.5rem;text-align:center">
            <div style="font-size:1rem;font-weight:700;color:#14532d;margin-bottom:.3rem">
              👈 Ready to start?
            </div>
            <div style="font-size:.83rem;color:#166534">
              Use the sidebar — add your first property in <b>Step 1</b>,
              then add a loan in <b>Step 2</b>.
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    def _kpi_row(self, s: dict):
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(
                _kpi(
                    "Total Exposure",
                    f"Rs.{s['total_exposure']:,.0f}",
                    f"{len(self.sg('loans', []))} facilities",
                ),
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                _kpi(
                    "Total FMV Pool",
                    f"Rs.{s['total_fmv']:,.0f}",
                    f"{len(self.sg('fmv', []))} properties",
                    "dp-pos",
                ),
                unsafe_allow_html=True,
            )
        with k3:
            g   = _gc(s["wtd_ltv"])
            pct = min(s["wtd_ltv"], 100)
            st.markdown(
                f"<div class='mc'>"
                f"<div class='ml'>Weighted Avg LTV%</div>"
                f"<div class='mv'>{s['wtd_ltv']:.2f}%</div>"
                f"<div class='gw'>"
                f"<div class='{g}' style='width:{pct:.1f}%'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with k4:
            g   = _gc(s["aggregate_ltv"])
            pct = min(s["aggregate_ltv"], 100)
            st.markdown(
                f"<div class='ac'>"
                f"<div class='al'>Aggregate LTV%</div>"
                f"<div class='av'>{s['aggregate_ltv']:.2f}%</div>"
                f"<div style='font-size:.8rem;color:#c7d2fe'>"
                f"Rs.{s['total_secured_principal']:,.0f} / Rs.{s['total_fmv']:,.0f}"
                f"</div>"
                f"<div class='gw' style='margin-top:.5rem'>"
                f"<div class='{g}' style='width:{pct:.1f}%'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    def _matrix(self, results: list, s: dict):
        st.markdown("### 🗂️ Collateral Assignment Matrix")
        loans = self.sg("loans", [])
        fmv   = self.sg("fmv", [])
        cu    = s["collateral_usage"]
        ai    = s["assigned_collateral_ids"]
        pi    = s["pool_collateral_ids"]
        lids  = [l["_loan_id"] for l in loans]
        rows  = []
        for src in fmv:
            sid  = src.get("id", "?")
            row  = {
                "Property": (
                    f"{src.get('Plot','?')} (Rs.{src.get('Amount', 0):,.0f})"
                ),
                "Type": "Assigned" if sid in ai else "Pool",
            }
            users = cu.get(sid, [])
            for lid in lids:
                loan = next((l for l in loans if l["_loan_id"] == lid), None)
                col  = f"L{lid}"
                if not loan:
                    row[col] = "—"
                    continue
                if sid in loan.get("assigned_collateral_ids", []):
                    row[col] = "⚡ Shared" if len(users) > 1 else "✅ Assigned"
                elif sid in pi and loan.get("collateral_mode", "pool") == "pool":
                    row[col] = "🌊 Pool"
                else:
                    row[col] = "—"
            rows.append(row)
        if rows:
            df = pd.DataFrame(rows)
            nc = {}
            for lid in lids:
                loan = next((l for l in loans if l["_loan_id"] == lid), None)
                if loan:
                    nc[f"L{lid}"] = (
                        f"{loan['Loan Type'][:14]} "
                        f"(Rs.{loan['Principal'] / 1e5:.1f}L)"
                    )
            st.dataframe(
                df.rename(columns=nc),
                hide_index=True,
                use_container_width=True,
            )
            st.markdown(
                "<div style='font-size:.82rem;color:#64748b;margin-top:.25rem'>"
                "✅ <b>Assigned</b> = dedicated · "
                "⚡ <b>Shared</b> = FMV split proportionally · "
                "🌊 <b>Pool</b> = waterfall</div>",
                unsafe_allow_html=True,
            )

    def _table(self, results: list, s: dict):
        st.markdown("### 📋 Portfolio LTV Breakdown")

        def dsort(r):
            m = r.get("Max LTV%")
            return (
                (2, 0) if m is None
                else (0 if m <= 50 else 1, -r.get("Principal", 0))
            )

        rows = []
        for r in sorted(results, key=dsort):
            u   = r["Is_Unsecured"]
            m   = r.get("Max LTV%")
            ltv = r.get("LTV%")
            cns = r.get("Collateral_Names", [])
            rows.append({
                "Facility":     r["Loan Type"],
                "Priority":     (
                    "Unsecured" if u
                    else ("High(50%)" if (m or 99) <= 50 else "Normal(70%)")
                ),
                "Mode":         {
                    "pool":     "🌊 Pool",
                    "assigned": "🔒 Assigned",
                }.get(r.get("Collateral_Mode", "pool"), "🌊 Pool"),
                "Collateral":   (
                    ", ".join(cns) if cns else ("Pool" if not u else "—")
                ),
                "Principal":    f"Rs.{r['Principal']:,.0f}",
                "Assigned FMV": "N/A" if u else f"Rs.{r['Assigned FMV']:,.0f}",
                "Pool FMV":     "N/A" if u else f"Rs.{r['Pool FMV']:,.0f}",
                "Total FMV":    "N/A" if u else f"Rs.{r['Total FMV']:,.0f}",
                "LTV%":         (
                    "N/A" if (u or ltv is None) else f"{ltv:.2f}%"
                ),
                "Max LTV":      (
                    "N/A" if (u or m is None) else f"{m:.0f}%"
                ),
                "Status":       "✅ PASS" if r["Pass_Status"] else "❌ FAIL",
            })
        rows.append({
            "Facility":     "── AGGREGATE ──",
            "Priority":     "—",
            "Mode":         "—",
            "Collateral":   "All",
            "Principal":    f"Rs.{s['total_secured_principal']:,.0f}",
            "Assigned FMV": "—",
            "Pool FMV":     "—",
            "Total FMV":    f"Rs.{s['total_fmv']:,.0f}",
            "LTV%":         f"{s['aggregate_ltv']:.2f}%",
            "Max LTV":      "—",
            "Status":       (
                "✅ PASS" if s["aggregate_ltv"] <= 70 else "❌ FAIL"
            ),
        })
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, use_container_width=True
        )

    def _gauges(self, results: list, s: dict):
        st.markdown("### 📊 LTV Visual Summary")
        sec = [r for r in results if not r["Is_Unsecured"]]
        if not sec:
            st.info("No secured facilities.")
            return

        # FIX: always reserve a slot for the aggregate card so it never
        # collides with a facility card (old code used len(sec) % ncols which
        # could be 0 and would overwrite the first column).
        total_cards = len(sec) + 1          # facilities + 1 aggregate
        ncols       = min(total_cards, 4)
        cols        = st.columns(ncols)

        for i, row in enumerate(sec):
            ltv = row["LTV%"] or 0.0
            mx  = row["Max LTV%"] or 100.0
            pom = min((ltv / mx) * 100, 100)
            fc  = "go" if ltv <= mx * 0.8 else ("gx" if ltv <= mx else "gf")
            sc  = "#059669" if row["Pass_Status"] else "#dc2626"
            pl  = "HIGH PRIORITY" if mx <= 50 else "NORMAL"
            pc  = "#7c3aed" if mx <= 50 else "#0891b2"
            mb  = {
                "pool":     "🌊 Pool",
                "assigned": "🔒 Assigned",
            }.get(row.get("Collateral_Mode", "pool"), "🌊 Pool")
            cns = row.get("Collateral_Names", [])
            ct  = (
                ", ".join(cns[:2]) + ("..." if len(cns) > 2 else "")
                if cns
                else "Pool"
            )
            with cols[i % ncols]:
                st.markdown(
                    f"""
                    <div style='background:#fff;border:1px solid #ddd6fe;
                         border-radius:12px;padding:1rem;margin-bottom:.75rem'>
                      <div style='display:flex;justify-content:space-between;
                           margin-bottom:.2rem'>
                        <div style='font-size:.68rem;font-weight:700;
                             color:{pc};text-transform:uppercase'>{pl}</div>
                        <div style='font-size:.68rem;font-weight:600;
                             color:#64748b'>{mb}</div>
                      </div>
                      <div style='font-size:.82rem;font-weight:700;
                           color:#1e1b4b;margin-bottom:.1rem'>
                        {row['Loan Type']}
                      </div>
                      <div style='font-size:.68rem;color:#94a3b8;
                           margin-bottom:.25rem'>🏠 {ct}</div>
                      <div style='font-size:1.5rem;font-weight:700;
                           color:{sc};font-family:DM Mono,monospace'>
                        {ltv:.2f}%
                      </div>
                      <div style='font-size:.72rem;color:#64748b'>
                        Max: {mx:.0f}% · Total FMV: Rs.{row['Total FMV']:,.0f}
                      </div>
                      <div class='gw' style='margin-top:.5rem'>
                        <div class='{fc}' style='width:{pom:.1f}%'></div>
                      </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Aggregate card — always placed in the next available column slot
        al = s["aggregate_ltv"]
        g  = _gc(al)
        ac = "#059669" if al <= 70 else "#dc2626"
        with cols[len(sec) % ncols]:
            st.markdown(
                f"""
                <div style='background:linear-gradient(135deg,#1e1b4b,#312e81);
                     border:1px solid #4338ca;border-radius:12px;
                     padding:1rem;margin-bottom:.75rem'>
                  <div style='font-size:.7rem;font-weight:700;color:#a5b4fc;
                       text-transform:uppercase;margin-bottom:.2rem'>AGGREGATE</div>
                  <div style='font-size:.82rem;font-weight:700;
                       color:#e0e7ff;margin-bottom:.25rem'>
                    All Secured / Total FMV
                  </div>
                  <div style='font-size:1.5rem;font-weight:700;
                       color:{ac};font-family:DM Mono,monospace'>
                    {al:.2f}%
                  </div>
                  <div style='font-size:.74rem;color:#c7d2fe'>
                    Rs.{s['total_secured_principal']:,.0f} /
                    Rs.{s['total_fmv']:,.0f}
                  </div>
                  <div class='gw' style='margin-top:.5rem'>
                    <div class='{g}' style='width:{min(al, 100):.1f}%'></div>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    def _manage_loans(self):
        with st.expander(
            "⚙️ Manage Portfolio — Remove Loans", expanded=False
        ):
            loans = self.sg("loans", [])
            if not loans:
                st.info("No loans added yet.")
                return
            for loan in loans:
                c1, c2, c3 = st.columns([3, 2, 1])
                icon = {"pool": "🌊", "assigned": "🔒"}.get(
                    loan.get("collateral_mode", "pool"), "🌊"
                )
                with c1:
                    st.markdown(
                        f"**{icon} {loan['Loan Type']}**  "
                        f"Rs.{loan['Principal']:,.0f}"
                    )
                with c2:
                    cns = self._coll_names(
                        loan.get("assigned_collateral_ids", [])
                    )
                    st.markdown(
                        f"<span style='font-size:.8rem;color:#64748b'>"
                        f"{'  |  '.join(cns) if cns else 'Pool'}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    if st.button(
                        "Remove", key=self.sk(f"rm_{loan['_loan_id']}")
                    ):
                        self.ss(
                            "loans",
                            [
                                l for l in loans
                                if l["_loan_id"] != loan["_loan_id"]
                            ],
                        )
                        st.rerun()

    def _pdf_export(self, results: list, s: dict):
        with st.expander("📄 Generate PDF Report", expanded=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                name = st.text_input(
                    "Client / Portfolio Name",
                    placeholder="e.g. Ramesh Sharma - Q2 Review",
                    label_visibility="collapsed",
                    key=self.sk("rname"),
                )
            with c2:
                if st.button(
                    "Generate PDF", type="primary", key=self.sk("genpdf")
                ):
                    if not name.strip():
                        st.error("Enter a client name.")
                    else:
                        with st.spinner("Generating..."):
                            try:
                                pdf_bytes = self._gen_pdf(
                                    name.strip(), results, s
                                )
                                fn = (
                                    f"LTV_{name.strip().replace(' ', '_')}_"
                                    f"{datetime.now().strftime('%Y%m%d')}.pdf"
                                )
                                self.ss("pdf", pdf_bytes)
                                self.ss("pdf_name", fn)
                                st.rerun()
                            except Exception as e:
                                st.error(f"PDF generation failed: {e}")
            if self.sg("pdf"):
                st.markdown("---")
                st.success("✅ Report ready.")
                st.download_button(
                    "⬇️ Download PDF",
                    data=self.sg("pdf"),
                    file_name=self.sg("pdf_name"),
                    mime="application/pdf",
                    type="secondary",
                )


# ══════════════════════════════════════════════════════════════════
# DTI MODULE
# ══════════════════════════════════════════════════════════════════

class _DTIPdf(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.set_text_color(15, 23, 42)
        self.cell(0, 10, "DTI ANALYSIS REPORT", 0, 1, "L")
        self.set_draw_color(59, 130, 246)
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
                f"Page {self.page_no()} | DTI Engine | "
                f"{datetime.now().strftime('%B %d, %Y')}"
            ),
            0, 0, "C",
        )


class DTIModule(BaseModule):
    name = "DTI Analysis"
    icon = "📊"
    key  = "dti"

    _LOAN_CONFIG = {
        "Personal Term Loan (PTL)": 2.0,
        "Personal OD":              2.0,
        "Share Loan":               2.0,
        "Mortgage Loan":            2.0,
        "Auto Loan":                2.0,
        "Home Loan":                1.428,
        "First Time Home Buyer":    1.25,
        "Education Loan":           2.0,
        "Professional OD":          2.0,
        "Professional T/L":         2.0,
    }
    _DEFAULT_TENURE = {
        "Personal OD":           1,
        "Home Loan":             15,
        "First Time Home Buyer": 20,
        "Share Loan":            1,
        "Professional OD":       1,
        "Professional T/L":      5,
    }

    # ── Lifecycle ──────────────────────────────────────────────
    def init_state(self):
        self.sd("loans",         [])
        self.sd("income_src",    [])
        self.sd("scenarios",     [])
        self.sd("lctr",          0)
        self.sd("gross_income",  150000.0)
        self.sd("inc_mode",      "Single Total")
        self.sd("enable_stress", False)
        self.sd("stress_rate",   0.0)
        self.sd("stress_inc",    0.0)
        self.sd("scenario_name", "Baseline (No Stress)")
        self.sd("mode_label",    "Baseline")
        self.sd("stressed_srcs", [])

    def reset_state(self):
        for k, v in [
            ("loans",     []),
            ("income_src", []),
            ("scenarios", []),
            ("lctr",      0),
            ("pdf",       None),
            ("pdf_name",  None),
        ]:
            self.ss(k, v)
        st.rerun()

    # ── Engine ─────────────────────────────────────────────────
    @staticmethod
    def _obligation(
        loan_type: str, principal: float, rate: float, tenure: int
    ) -> float:
        """Calculate monthly obligation (EMI or OD interest)."""
        if principal <= 0 or rate <= 0:
            return 0.0
        rm = (rate / 100.0) / 12.0
        if "OD" in loan_type or "Overdraft" in loan_type:
            # Overdraft: interest-only payment on full limit
            return principal * rm
        if tenure <= 0:
            return 0.0
        n = tenure * 12
        try:
            return (principal * rm * (1 + rm) ** n) / ((1 + rm) ** n - 1)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    @staticmethod
    def _waterfall(df: pd.DataFrame, income: float) -> pd.DataFrame:
        """
        Priority waterfall: highest Required Multiplier loans are funded first
        (i.e. tightest ratio gets first claim on income).
        """
        df  = df.sort_values(
            "Required Multiplier", ascending=False
        ).reset_index(drop=True)
        rem = income
        pf, ac, sn = [], [], []
        for idx, row in df.iterrows():
            obl = row["Obligation"]
            req = row["Required Multiplier"]
            sn.append(rem)
            needed = obl * req          # income needed to satisfy this facility
            if obl <= 0:
                # Zero-obligation loan always passes
                ac.append(float("inf"))
                pf.append(True)
            elif rem >= needed:
                ac.append(req)
                pf.append(True)
                rem -= needed
            else:
                # Partial coverage
                actual = rem / obl if obl > 0 else 0.0
                ac.append(actual)
                pf.append(actual >= req)
                rem = 0.0
        df["Pass_Status"]              = pf
        df["Actual Coverage"]          = ac
        df["Available_Income_Snapshot"] = sn
        return df

    # ── PDF ────────────────────────────────────────────────────
    def _gen_pdf(
        self,
        client:    str,
        income:    float,
        df_res:    pd.DataFrame,
        is_pass:   bool,
        exposure:  float,
        shortfall: float,
        mode:      str,
        s_name:    str,
        s_rate:    float,
        s_inc:     float,
        agg_dti:   float,
    ) -> bytes:
        pdf = _DTIPdf()
        pdf.add_page()

        def kv(lbl, val):
            pdf.set_font("Arial", "", 10)
            pdf.cell(45, 6, safe_str(str(lbl)), 0, 0)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, safe_str(str(val)), 0, 1)

        # Executive summary
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, "EXECUTIVE SUMMARY", 0, 1)
        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        kv("Client Name:",        client)
        kv("Analysis Date:",      datetime.now().strftime("%B %d, %Y"))
        kv("Monthly Income:",     f"Rs. {income:,.2f}")
        kv("Total Exposure:",     f"Rs. {exposure:,.2f}")
        kv("Aggregate Coverage:", f"{agg_dti:.2f}x")
        dm = (
            "NORMAL - STRESS N/A"
            if ("BASELINE" in mode.upper() or s_name == "Baseline (No Stress)")
            else mode.upper()
        )
        kv("Analysis Mode:", dm)
        if shortfall > 0:
            pdf.set_text_color(239, 68, 68)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(45, 6, "Income Shortfall:", 0, 0)
            pdf.cell(0, 6, f"Rs.{shortfall:,.2f} (CRITICAL)", 0, 1)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        if is_pass:
            pdf.set_text_color(16, 185, 129)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(
            0, 7,
            safe_str(
                f"Result: "
                f"{'APPROVED - Within Risk Tolerance' if is_pass else 'DECLINED - Exceeds Risk Limits'}"
            ),
            0, 1,
        )
        pdf.set_text_color(0, 0, 0)

        # Allocation table
        pdf.ln(6)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, "PRIORITY ALLOCATION BREAKDOWN", 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        cw = [45, 25, 25, 25, 30, 20, 20]
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(241, 245, 249)
        for hdr, w in zip(
            ["Facility", "Principal", "Payment", "Rem. Inc.",
             "Actual Cov.", "Required", "Status"],
            cw,
        ):
            pdf.cell(w, 7, hdr, 1, 0, "C", True)
        pdf.ln()
        pdf.set_font("Arial", "", 8)
        for idx, row in df_res.iterrows():
            fill = idx % 2 == 0
            if fill:
                pdf.set_fill_color(248, 250, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            cells = [
                (str(row["Loan Type"]),                        cw[0], "L"),
                (f"{row['Amount']:,.0f}",                      cw[1], "R"),
                (f"{row['Obligation']:,.0f}",                  cw[2], "R"),
                (f"{row['Available_Income_Snapshot']:,.0f}",   cw[3], "R"),
                (f"{row['Actual Coverage']:.2f}x",             cw[4], "C"),
                (f"{row['Required Multiplier']:.2f}x",         cw[5], "C"),
            ]
            for val, w, aln in cells:
                pdf.cell(w, 7, safe_str(str(val)), 1, 0, aln, fill)
            st_txt = "PASS" if row["Pass_Status"] else "FAIL"
            if st_txt == "PASS":
                pdf.set_text_color(16, 185, 129)
            else:
                pdf.set_text_color(239, 68, 68)
            pdf.cell(cw[6], 7, st_txt, 1, 1, "C", fill)
            pdf.set_text_color(0, 0, 0)

        # FIX: handle both str and bytes return from fpdf.output()
        out = pdf.output(dest="S")
        return out.encode("latin-1") if isinstance(out, str) else bytes(out)

    # ── Sidebar ────────────────────────────────────────────────
    def render_sidebar(self):
        st.markdown("### 💰 Income Configuration")
        inc_mode = st.radio(
            "Income Entry Method",
            ["Single Total", "Multiple Sources"],
            horizontal=True,
            key=self.sk("inc_mode"),
        )
        self.ss("inc_mode", inc_mode)
        income_src = self.sg("income_src", [])
        gross      = 0.0

        if inc_mode == "Single Total":
            gross = st.number_input(
                "Monthly Gross Income (Rs.)",
                value=150000.0,
                step=5000.0,
                key=self.sk("gross"),
            )
        else:
            c1, c2 = st.columns([1.5, 1])
            src = c1.text_input("Income Source", key=self.sk("isrc"))
            amt = c2.number_input(
                "Amount (Rs.)", min_value=0.0, key=self.sk("iamt")
            )
            if st.button(
                "➕ Add Source", type="primary", key=self.sk("addinc")
            ):
                if not src.strip():
                    st.error("❌ Enter a source name")
                elif amt <= 0:
                    st.error("❌ Amount must be > 0")
                else:
                    income_src.append({"Source": src.strip(), "Amount": amt})
                    self.ss("income_src", income_src)
                    st.success(f"✅ Added: {src.strip()}")
                    st.rerun()
            if income_src:
                st.dataframe(pd.DataFrame(income_src), hide_index=True)
                if st.button(
                    "Clear All Sources", type="primary", key=self.sk("clrinc")
                ):
                    self.ss("income_src", [])
                    st.rerun()
                gross = sum(x["Amount"] for x in income_src)
        self.ss("gross_income", gross)

        st.markdown("---")
        st.markdown("### 📊 Stress Test Configuration")
        enable = st.toggle(
            "Enable Stress Testing", value=False, key=self.sk("stog")
        )
        self.ss("enable_stress", enable)
        s_rate, s_inc = 0.0, 0.0
        s_name, m_lbl = "Baseline (No Stress)", "Baseline"
        str_srcs = []

        if enable:
            if inc_mode == "Multiple Sources" and income_src:
                all_srcs = [x["Source"] for x in income_src]
                str_srcs = st.multiselect(
                    "Income Sources to Stress",
                    all_srcs,
                    default=all_srcs,
                    key=self.sk("strssrcs"),
                )

            st.markdown("#### Custom Scenarios")
            scenarios = self.sg("scenarios", [])
            with st.form(self.sk("scen_form")):
                st.markdown("➕ **Create New Scenario**")
                f1, f2 = st.columns(2)
                c_name = f1.text_input(
                    "Scenario Name", placeholder="e.g. Rate Shock"
                )
                c_rate = f2.number_input(
                    "Rate Shock (+%)", 0.0, 50.0, 2.0, step=0.5
                )
                c_inc  = st.number_input(
                    "Income Reduction (-%)", 0.0, 100.0, 10.0, step=5.0
                )
                if st.form_submit_button("Save Scenario", type="primary"):
                    if c_name:
                        scenarios.append({
                            "Name":   c_name,
                            "Rate":   c_rate,
                            "Income": c_inc,
                        })
                        self.ss("scenarios", scenarios)
                        st.success(f"✅ Saved: {c_name}")
                    else:
                        st.error("Please enter a name")

            if scenarios:
                active_name = st.selectbox(
                    "Active Scenario",
                    [s["Name"] for s in scenarios],
                    key=self.sk("actscen"),
                )
                act = next(
                    (s for s in scenarios if s["Name"] == active_name), None
                )
                if act:
                    s_rate = act["Rate"]
                    s_inc  = act["Income"]
                    s_name = active_name
                    m_lbl  = "Custom Stress"
                if st.button(
                    "🗑️ Clear Scenarios", type="primary", key=self.sk("clrscen")
                ):
                    self.ss("scenarios", [])
                    st.rerun()
            else:
                st.warning("No custom scenarios yet.")
                s_name = "None"

        self.ss("stress_rate",   s_rate)
        self.ss("stress_inc",    s_inc)
        self.ss("scenario_name", s_name)
        self.ss("mode_label",    m_lbl)
        self.ss("stressed_srcs", str_srcs)

        st.markdown("---")
        if st.button(
            "🔄 Reset DTI Data", type="primary", key=self.sk("reset")
        ):
            self.reset_state()

    # ── Main ───────────────────────────────────────────────────
    def render_main(self):
        st.title(self.label)
        st.markdown(
            "Advanced income assessment and scenario analysis for loan portfolios"
        )

        # ── Facility input block
        with st.container():
            st.markdown(
                "<div class='is'><h5>➕ Add New Facility</h5>",
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
            l_type = c1.selectbox(
                "Facility Type",
                list(self._LOAN_CONFIG.keys()),
                key=self.sk("ftype"),
            )
            l_amt  = c2.number_input(
                "Principal (Rs.)", step=10000.0, min_value=0.0,
                key=self.sk("famt"),
            )
            l_rate = c3.number_input(
                "Rate (%)", value=12.0, step=0.25, key=self.sk("frate")
            )
            l_ten  = c4.number_input(
                "Tenure (Yrs)",
                value=self._DEFAULT_TENURE.get(l_type, 5),
                min_value=1,
                key=self.sk("ften"),
            )
            co, cb = st.columns([3, 1])
            use_man = co.checkbox(
                "Use Fixed Monthly Payment (Override EMI)",
                key=self.sk("useman"),
            )
            # FIX: always define man_emi so the variable is never unbound
            man_emi = 0.0
            if use_man:
                man_emi = st.number_input(
                    "Fixed Monthly Payment (Rs.)",
                    min_value=0.0,
                    step=1000.0,
                    key=self.sk("manemi"),
                )
            if cb.button(
                "Add to Portfolio", type="primary", key=self.sk("addfac")
            ):
                errs = []
                if l_amt  <= 0:
                    errs.append("❌ Principal must be > 0")
                if l_rate <= 0:
                    errs.append("❌ Rate must be > 0")
                if l_ten  <= 0:
                    errs.append("❌ Tenure must be ≥ 1")
                if use_man and man_emi <= 0:
                    errs.append("❌ Fixed payment must be > 0")
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    loans = self.sg("loans", [])
                    lid   = self.sg("lctr", 0)
                    self.ss("lctr", lid + 1)
                    std   = self._obligation(l_type, l_amt, l_rate, l_ten)
                    loans.append({
                        "Loan Type":          l_type,
                        "Amount":             l_amt,
                        "Base Rate":          l_rate,
                        "Tenure":             l_ten,
                        "Base_Obligation":    man_emi if use_man else std,
                        "Required Multiplier": self._LOAN_CONFIG[l_type],
                        "Is_Manual":          use_man,
                        "_loan_id":           lid,
                    })
                    self.ss("loans", loans)
                    st.success(f"✅ Added {l_type}")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        loans = self.sg("loans", [])
        if not loans:
            st.markdown("""
            <div style='text-align:center;padding:4rem 2rem;
                 background:linear-gradient(135deg,#fff,#f8fafc);
                 border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.06)'>
              <h3 style='color:#475569;margin-bottom:1rem'>
                👋 Welcome to DTI Analysis Engine
              </h3>
              <p style='color:#64748b;font-size:1.1rem'>
                Configure income in the sidebar, then add loan facilities above.
              </p>
            </div>""", unsafe_allow_html=True)
            return

        # ── Read sidebar-computed values
        gross    = self.sg("gross_income", 0.0)
        enable   = self.sg("enable_stress", False)
        s_rate   = self.sg("stress_rate", 0.0)
        s_inc    = self.sg("stress_inc", 0.0)
        s_name   = self.sg("scenario_name", "Baseline (No Stress)")
        m_lbl    = self.sg("mode_label", "Baseline")
        str_srcs = self.sg("stressed_srcs", [])
        inc_mode = self.sg("inc_mode", "Single Total")
        inc_src  = self.sg("income_src", [])

        if gross <= 0:
            st.error(
                "⚠️ Configure Monthly Gross Income in the sidebar."
            )
            return

        # ── Effective income after stress
        eff = gross
        if enable:
            if inc_mode == "Multiple Sources" and str_srcs:
                var = sum(
                    x["Amount"] for x in inc_src
                    if x["Source"] in str_srcs
                )
                eff = (gross - var) + var * (1.0 - s_inc / 100.0)
            else:
                eff = gross * (1.0 - s_inc / 100.0)

        def get_obl(row, sr: float):
            """Return (obligation, effective_rate) for a loan row."""
            if row["Is_Manual"]:
                return row["Base_Obligation"], row["Base Rate"]
            nr  = row["Base Rate"] + sr
            obl = self._obligation(row["Loan Type"], row["Amount"], nr, row["Tenure"])
            return obl, nr

        df = pd.DataFrame(loans)
        df[["Obligation", "Effective_Rate"]] = df.apply(
            lambda r: pd.Series(get_obl(r, s_rate)), axis=1
        )
        df_res = self._waterfall(df.copy(), eff)

        tot_obl   = df_res["Obligation"].sum()
        agg_dti   = eff / tot_obl if tot_obl > 0 else 0.0
        ok        = bool(df_res["Pass_Status"].all())
        req_ideal = sum(
            r["Obligation"] * r["Required Multiplier"]
            for _, r in df_res.iterrows()
        )
        shortfall = max(0.0, req_ideal - eff) if not ok else 0.0

        # Scenario badge
        if enable:
            scope = (
                "On Selected Sources"
                if (inc_mode == "Multiple Sources" and str_srcs)
                else "Global"
            )
            st.markdown(
                f"<div style='background:#dbeafe;border-left:4px solid #3b82f6;"
                f"padding:1.25rem 1.5rem;border-radius:12px;margin-bottom:1.5rem'>"
                f"<b>🎯 Active Scenario: {s_name}</b> &nbsp;·&nbsp; "
                f"Rate: +{s_rate:.2f}% &nbsp;·&nbsp; "
                f"Income: -{s_inc:.2f}% ({scope})</div>",
                unsafe_allow_html=True,
            )

        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(
                _kpi("Total Exposure", f"Rs.{df['Amount'].sum():,.0f}"),
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                _kpi("Monthly Obligation", f"Rs.{tot_obl:,.0f}"),
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                _kpi("Aggregate Coverage", f"{agg_dti:.2f}x"),
                unsafe_allow_html=True,
            )
        with k4:
            sc = "dp-neg" if shortfall > 0 else "dp-pos"
            st.markdown(
                _kpi(
                    "Income Shortfall",
                    f"Rs.{shortfall:,.0f}",
                    "Critical Deficit" if shortfall > 0 else "Adequate",
                    sc,
                ),
                unsafe_allow_html=True,
            )

        _status_banner(
            ok,
            "✅ REQUEST APPROVED — Within Stipulated DTI Requirement",
            "⚠️ PORTFOLIO DECLINED — Exceeds Stipulated DTI Requirement",
        )

        def render_table(d: pd.DataFrame, caption: str):
            st.markdown(f"##### {caption}")
            disp = d.copy()
            disp["Status"] = disp["Pass_Status"].apply(
                lambda x: "✅ PASS" if x else "❌ FAIL"
            )
            for col, fmt in [
                ("Amount",                   "Rs.{:,.0f}"),
                ("Obligation",               "Rs.{:,.0f}"),
                ("Available_Income_Snapshot", "Rs.{:,.0f}"),
            ]:
                disp[col] = disp[col].apply(lambda x, f=fmt: f.format(x))
            disp["Actual Coverage"] = disp["Actual Coverage"].apply(
                lambda x: f"{x:.2f}x" if x != float("inf") else "∞"
            )
            disp["Effective_Rate"] = disp["Effective_Rate"].apply(
                lambda x: f"{x:.2f}%"
            )
            st.dataframe(
                disp[[
                    "Loan Type", "Amount", "Effective_Rate", "Obligation",
                    "Available_Income_Snapshot", "Actual Coverage", "Status",
                ]],
                hide_index=True,
                use_container_width=True,
            )

        # ── Breakdown
        st.markdown("### 📋 Portfolio Breakdown")
        scenarios = self.sg("scenarios", [])
        if enable and scenarios:
            st.info("Showing breakdowns for all defined scenarios.")
            for scen in scenarios:
                if inc_mode == "Multiple Sources" and str_srcs:
                    var = sum(
                        x["Amount"] for x in inc_src
                        if x["Source"] in str_srcs
                    )
                    si  = (gross - var) + var * (1.0 - scen["Income"] / 100.0)
                else:
                    si  = gross * (1.0 - scen["Income"] / 100.0)
                tmp = pd.DataFrame(loans)
                tmp[["Obligation", "Effective_Rate"]] = tmp.apply(
                    lambda r: pd.Series(get_obl(r, scen["Rate"])), axis=1
                )
                sr = self._waterfall(tmp, si)
                so = sr["Obligation"].sum()
                sa = si / so if so > 0 else 0.0
                render_table(sr, f"Scenario: {scen['Name']} (Coverage: {sa:.2f}x)")
                st.markdown("---")
        else:
            render_table(df_res, f"Scenario: {s_name}")

        # ── PDF Export
        with st.expander("📄 Generate Report", expanded=True):
            st.markdown(
                "Export a detailed PDF with executive summary and scenario analysis."
            )
            c1, c2 = st.columns([3, 1])
            with c1:
                rname = st.text_input(
                    "Client/Portfolio Name",
                    placeholder="e.g. John Doe - Q1 Review",
                    label_visibility="collapsed",
                    key=self.sk("rname"),
                )
            with c2:
                if st.button(
                    "🚀 Generate PDF", type="primary", key=self.sk("genpdf")
                ):
                    if not rname.strip():
                        st.error("⚠️ Enter a client name.")
                    else:
                        with st.spinner("Generating..."):
                            try:
                                pdf_bytes = self._gen_pdf(
                                    rname.strip(), gross, df_res, ok,
                                    df["Amount"].sum(), shortfall,
                                    m_lbl, s_name, s_rate, s_inc, agg_dti,
                                )
                                fn = (
                                    f"DTI_{rname.strip().replace(' ', '_')}_"
                                    f"{datetime.now().strftime('%Y%m%d')}.pdf"
                                )
                                self.ss("pdf", pdf_bytes)
                                self.ss("pdf_name", fn)
                                st.rerun()
                            except Exception as e:
                                st.error(f"PDF generation failed: {e}")
            if self.sg("pdf"):
                st.markdown("---")
                st.success("✅ Report generated successfully.")
                st.download_button(
                    "⬇️ Download PDF",
                    data=self.sg("pdf"),
                    file_name=self.sg("pdf_name"),
                    mime="application/pdf",
                    type="secondary",
                )


# ══════════════════════════════════════════════════════════════════
# MODULE REGISTRY
# ══════════════════════════════════════════════════════════════════
#
#   To add a new module:
#     1. Create a class extending BaseModule (anywhere above)
#     2. Append an instance below — sidebar navigation auto-updates
#
MODULES: list[BaseModule] = [
    LTVModule(),
    DTIModule(),
    # MyNewModule(),   ← add here
]


# ══════════════════════════════════════════════════════════════════
# APP SHELL
# ══════════════════════════════════════════════════════════════════

def main():
    st.markdown(_STYLES, unsafe_allow_html=True)

    # Auth gate
    st.session_state.setdefault("authenticated", False)
    if not st.session_state["authenticated"]:
        _show_login()
        st.stop()

    # Initialise every module's state (idempotent — safe to call every run)
    for mod in MODULES:
        mod.init_state()

    # Sidebar shell
    with st.sidebar:
        st.markdown("## 🏦 Loan Analysis Engine")
        user = st.session_state.get("auth_user", "")
        st.markdown(
            f"<div style='background:rgba(255,255,255,.1);border-radius:8px;"
            f"padding:.45rem .85rem;font-size:.8rem;color:#c7d2fe;margin-bottom:.3rem'>"
            f"👤 Signed in as <b>{user}</b></div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sign Out", type="primary", key="_signout"):
            st.session_state.update(
                authenticated=False, auth_user="", _lerr=""
            )
            st.rerun()
        st.markdown("---")

        # Module selector — auto-built from MODULES list
        st.session_state.setdefault("_active_mod", 0)
        idx = st.radio(
            "Select Module",
            range(len(MODULES)),
            format_func=lambda i: MODULES[i].label,
            index=st.session_state["_active_mod"],
            horizontal=True,
            key="_mod_radio",
        )
        st.session_state["_active_mod"] = idx
        st.markdown("---")
        MODULES[idx].render_sidebar()

    # Main content
    MODULES[idx].render_main()


main()
