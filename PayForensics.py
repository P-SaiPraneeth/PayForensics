import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PayForensics AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parent
DATA = BASE / "payforensics_output"


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    files = {
        "tx": "analytics_transactions.csv",
        "users": "user_risk.csv",
        "merchants": "merchant_risk.csv",
        "chargebacks": "chargebacks_clean.csv",
        "rings": "fraud_rings.csv",
        "members": "ring_members.csv",
        "daily": "daily_metrics.csv",
        "kyc": "kyc_master.csv",
        "summary": "summary.csv"
    }

    data = {}

    for key, filename in files.items():

        path = DATA / filename

        try:
            data[key] = pd.read_csv(path)
        except FileNotFoundError:
            st.error(f"Missing file: {path}")
            st.stop()

    return data


d = load_data()

tx = d["tx"]
users = d["users"]
merchants = d["merchants"]
chargebacks = d["chargebacks"]
rings = d["rings"]
members = d["members"]
daily = d["daily"]
kyc = d["kyc"]
summary = d["summary"]


# ============================================================
# BASIC CLEANING
# ============================================================

for frame in [
    tx,
    users,
    merchants,
    chargebacks,
    rings,
    members,
    daily,
    kyc,
    summary
]:

    for col in frame.columns:

        if frame[col].dtype == "object":
            frame[col] = frame[col].fillna("UNKNOWN")


# ============================================================
# SESSION STATE
# ============================================================

if "investigation_type" not in st.session_state:
    st.session_state.investigation_type = None

if "investigation_id" not in st.session_state:
    st.session_state.investigation_id = None


def investigate(entity_type, entity_id):

    st.session_state.investigation_type = entity_type
    st.session_state.investigation_id = entity_id


def clear_investigation():

    st.session_state.investigation_type = None
    st.session_state.investigation_id = None


# ============================================================
# FILTER DEFAULTS + RESET
# ============================================================

# These are the normal/default values used by the global filters.
# Keeping explicit widget keys lets the Reset button restore every
# filter instead of only closing the investigation.

if "timestamp_clean" in tx.columns:
    _filter_dates = pd.to_datetime(
        tx["timestamp_clean"],
        errors="coerce"
    )
    _min_date = _filter_dates.min()
    _max_date = _filter_dates.max()
else:
    _min_date = None
    _max_date = None

if (
    pd.notna(_min_date)
    if _min_date is not None
    else False
) and (
    pd.notna(_max_date)
    if _max_date is not None
    else False
):
    DEFAULT_DATE_RANGE = (
        _min_date.date(),
        _max_date.date()
    )
else:
    DEFAULT_DATE_RANGE = None


DEFAULT_CATEGORIES = (
    sorted(
        tx["merchant_category_clean"]
        .dropna()
        .astype(str)
        .unique()
    )
    if "merchant_category_clean" in tx.columns
    else []
)


DEFAULT_RISK = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL"
]


DEFAULT_STATUS = (
    sorted(
        tx["status_clean"]
        .dropna()
        .astype(str)
        .unique()
    )
    if "status_clean" in tx.columns
    else []
)


if "amount_clean" in tx.columns and len(tx):
    _amount_min = float(tx["amount_clean"].min())
    _amount_max = float(tx["amount_clean"].max())
    DEFAULT_AMOUNT_RANGE = (_amount_min, _amount_max)
else:
    DEFAULT_AMOUNT_RANGE = (0.0, 0.0)


def reset_all_filters():
    """Restore every global filter to its original/default state."""

    if DEFAULT_DATE_RANGE is not None:
        st.session_state["date_filter"] = DEFAULT_DATE_RANGE

    if "merchant_category_clean" in tx.columns:
        st.session_state["category_filter"] = DEFAULT_CATEGORIES.copy()

    if "transaction_risk_level" in tx.columns:
        st.session_state["risk_filter"] = DEFAULT_RISK.copy()

    if "status_clean" in tx.columns:
        st.session_state["status_filter"] = DEFAULT_STATUS.copy()

    if "amount_clean" in tx.columns:
        st.session_state["amount_filter"] = DEFAULT_AMOUNT_RANGE

    clear_investigation()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def money(x):

    if pd.isna(x):
        return "₹0"

    x = float(x)

    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"

    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.2f} L"

    if abs(x) >= 1e3:
        return f"₹{x / 1e3:.2f} K"

    return f"₹{x:,.0f}"


def pct(x):

    if pd.isna(x):
        return "0.00%"

    return f"{float(x) * 100:.2f}%"


def risk_badge(level):

    level = str(level).upper()

    if level == "CRITICAL":
        return "🔴 CRITICAL"

    if level == "HIGH":
        return "🟠 HIGH"

    if level == "MEDIUM":
        return "🟡 MEDIUM"

    return "🟢 LOW"


# ============================================================
# HEADER
# ============================================================

st.title("🛡️ PayForensics AI")

st.caption(
    "AI-Powered Financial Crime Intelligence • "
    "Transaction • Merchant • User • KYC • Fraud Ring Analysis"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🛡️ PayForensics")

    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "📊 Executive Overview",
            "💳 Transactions",
            "🏪 Merchant Intelligence",
            "👤 User & KYC Risk",
            "💰 Chargebacks",
            "🕸️ Fraud Rings",
            "🔎 AI Investigator"
        ]
    )

    st.markdown("---")

    st.markdown("### 🎛️ Global Filters")


# ============================================================
# GLOBAL FILTERS
# ============================================================

filtered_tx = tx.copy()


# DATE FILTER

if "timestamp_clean" in filtered_tx.columns:

    filtered_tx["timestamp_clean"] = pd.to_datetime(
        filtered_tx["timestamp_clean"],
        errors="coerce"
    )

    if DEFAULT_DATE_RANGE is not None:

        with st.sidebar:

            date_range = st.date_input(
                "📅 Transaction Date",
                value=DEFAULT_DATE_RANGE,
                key="date_filter"
            )

        if len(date_range) == 2:

            start_date, end_date = date_range

            filtered_tx = filtered_tx[
                (filtered_tx["timestamp_clean"].dt.date >= start_date)
                &
                (filtered_tx["timestamp_clean"].dt.date <= end_date)
            ]


# CATEGORY FILTER

if "merchant_category_clean" in tx.columns:

    with st.sidebar:

        selected_categories = st.multiselect(
            "🏪 Merchant Category",
            DEFAULT_CATEGORIES,
            default=DEFAULT_CATEGORIES,
            key="category_filter"
        )

    if selected_categories:

        filtered_tx = filtered_tx[
            filtered_tx["merchant_category_clean"]
            .astype(str)
            .isin(selected_categories)
        ]


# RISK FILTER

if "transaction_risk_level" in tx.columns:

    with st.sidebar:

        selected_risk = st.multiselect(
            "⚠️ Transaction Risk",
            DEFAULT_RISK,
            default=DEFAULT_RISK,
            key="risk_filter"
        )

    if selected_risk:

        filtered_tx = filtered_tx[
            filtered_tx["transaction_risk_level"]
            .astype(str)
            .isin(selected_risk)
        ]


# STATUS FILTER

if "status_clean" in tx.columns:

    with st.sidebar:

        selected_status = st.multiselect(
            "📌 Transaction Status",
            DEFAULT_STATUS,
            default=DEFAULT_STATUS,
            key="status_filter"
        )

    if selected_status:

        filtered_tx = filtered_tx[
            filtered_tx["status_clean"]
            .astype(str)
            .isin(selected_status)
        ]


# AMOUNT FILTER

if "amount_clean" in tx.columns:

    with st.sidebar:

        amount_range = st.slider(
            "💰 Transaction Amount",
            min_value=DEFAULT_AMOUNT_RANGE[0],
            max_value=DEFAULT_AMOUNT_RANGE[1],
            value=DEFAULT_AMOUNT_RANGE,
            key="amount_filter"
        )

    filtered_tx = filtered_tx[
        filtered_tx["amount_clean"].between(
            amount_range[0],
            amount_range[1]
        )
    ]


# ============================================================
# SIDEBAR STATUS / RESET
# ============================================================

with st.sidebar:

    st.markdown("---")

    st.metric(
        "Filtered Transactions",
        f"{len(filtered_tx):,}"
    )

    st.metric(
        "Chargebacks",
        f"{int(filtered_tx['chargeback_count'].sum()):,}"
        if "chargeback_count" in filtered_tx.columns
        else "0"
    )

    st.metric(
        "Fraud Rings",
        f"{len(rings):,}"
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.button(
        "🔄 Reset Investigation",
        key="reset_investigation_button",
        use_container_width=True,
        on_click=reset_all_filters
    )


# ============================================================
# INVESTIGATION PANEL
# ============================================================

if st.session_state.investigation_type:

    entity_type = st.session_state.investigation_type
    entity_id = st.session_state.investigation_id

    st.markdown("---")

    st.subheader("🔎 Active Investigation")

    if st.button("✖ Close Investigation"):

        clear_investigation()
        st.rerun()


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "📊 Executive Overview":

    st.header("Executive Overview")

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    total_tx = (
        filtered_tx["txn_id_clean"].nunique()
        if "txn_id_clean" in filtered_tx.columns
        else len(filtered_tx)
    )

    total_amount = (
        filtered_tx["amount_clean"].sum()
        if "amount_clean" in filtered_tx.columns
        else 0
    )

    chargebacks_count = (
        filtered_tx["chargeback_count"].sum()
        if "chargeback_count" in filtered_tx.columns
        else 0
    )

    disputed_amount = (
        filtered_tx["disputed_amount"].sum()
        if "disputed_amount" in filtered_tx.columns
        else 0
    )

    high_risk = (
        filtered_tx["transaction_risk_level"]
        .isin(["HIGH", "CRITICAL"])
        .sum()
        if "transaction_risk_level" in filtered_tx.columns
        else 0
    )

    critical_risk = (
        filtered_tx["transaction_risk_level"]
        .eq("CRITICAL")
        .sum()
        if "transaction_risk_level" in filtered_tx.columns
        else 0
    )

    failed_rate = (
        (filtered_tx["status_clean"] == "FAILED").mean()
        if "status_clean" in filtered_tx.columns
        else 0
    )


    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric(
        "💳 Transactions",
        f"{total_tx:,}"
    )

    c2.metric(
        "💰 Transaction Value",
        money(total_amount)
    )

    c3.metric(
        "↩️ Chargebacks",
        f"{int(chargebacks_count):,}"
    )

    c4.metric(
        "⚠️ Disputed Amount",
        money(disputed_amount)
    )

    c5.metric(
        "🚨 High/Critical",
        f"{int(high_risk):,}"
    )

    c6.metric(
        "❌ Failed Rate",
        pct(failed_rate)
    )


    # --------------------------------------------------------
    # ALERT BANNER
    # --------------------------------------------------------

    if critical_risk > 0:

        st.error(
            f"🚨 {critical_risk:,} CRITICAL-RISK transactions "
            f"require investigation."
        )

    else:

        st.success(
            "✅ No critical-risk transactions detected "
            "under the current filters."
        )


    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    left, right = st.columns(2)


    with left:

        chart = filtered_tx.copy()

        chart["date"] = (
            chart["timestamp_clean"]
            .dt.date
        )

        trend = (
            chart
            .groupby("date", as_index=False)
            ["amount_clean"]
            .sum()
        )

        fig = px.line(
            trend,
            x="date",
            y="amount_clean",
            markers=True,
            title="Transaction Value Trend"
        )

        fig.update_layout(
            hovermode="x unified"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    with right:

        risk = (
            filtered_tx[
                "transaction_risk_level"
            ]
            .value_counts()
            .reindex(
                [
                    "LOW",
                    "MEDIUM",
                    "HIGH",
                    "CRITICAL"
                ],
                fill_value=0
            )
            .reset_index()
        )

        risk.columns = [
            "risk_level",
            "count"
        ]

        fig = px.bar(
            risk,
            x="risk_level",
            y="count",
            title="Transaction Risk Distribution",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # --------------------------------------------------------
    # TOP INVESTIGATION TARGETS
    # --------------------------------------------------------

    st.subheader("🚨 Top Investigation Targets")

    if "transaction_risk_score" in filtered_tx.columns:

        targets = (
            filtered_tx
            .sort_values(
                "transaction_risk_score",
                ascending=False
            )
            .head(10)
        )

        for _, row in targets.iterrows():

            cols = st.columns(
                [2, 1, 2, 2, 1]
            )

            txn_id = row.get(
                "txn_id_clean",
                "UNKNOWN"
            )

            cols[0].write(
                f"**{txn_id}**"
            )

            cols[1].write(
                risk_badge(
                    row.get(
                        "transaction_risk_level",
                        "UNKNOWN"
                    )
                )
            )

            cols[2].write(
                money(
                    row.get(
                        "amount_clean",
                        0
                    )
                )
            )

            cols[3].write(
                f"Score: **{row.get('transaction_risk_score', 0):.1f}**"
            )

            if cols[4].button(
                "Investigate",
                key=f"investigate_{txn_id}"
            ):

                investigate(
                    "transaction",
                    txn_id
                )

                st.rerun()


# ============================================================
# TRANSACTIONS
# ============================================================

elif page == "💳 Transactions":

    st.header("💳 Transaction Intelligence")

    st.info(
        "Select a transaction below to open a detailed investigation."
    )


    if "transaction_risk_score" in filtered_tx.columns:

        display_cols = [
            c for c in [
                "txn_id_clean",
                "timestamp_clean",
                "user_id_core",
                "merchant_id_core",
                "amount_clean",
                "status_clean",
                "transaction_risk_score",
                "transaction_risk_level",
                "chargeback_count",
                "disputed_amount"
            ]
            if c in filtered_tx.columns
        ]


        table = (
            filtered_tx
            .sort_values(
                "transaction_risk_score",
                ascending=False
            )
            .head(500)
        )


        st.dataframe(
            table[display_cols],
            use_container_width=True,
            hide_index=True
        )


        st.markdown("### 🔎 Select Transaction")

        txn_options = (
            table["txn_id_clean"]
            .astype(str)
            .tolist()
        )

        selected_txn = st.selectbox(
            "Transaction",
            txn_options
        )


        if st.button(
            "🔎 Investigate Transaction"
        ):

            investigate(
                "transaction",
                selected_txn
            )

            st.rerun()


    # --------------------------------------------------------
    # DAILY ACTIVITY
    # --------------------------------------------------------

    if len(filtered_tx):

        temp = filtered_tx.copy()

        temp["date"] = (
            temp["timestamp_clean"]
            .dt.date
        )

        daily_tx = (
            temp
            .groupby("date")
            .agg(
                transaction_count=(
                    "txn_id_clean",
                    "nunique"
                ),
                transaction_amount=(
                    "amount_clean",
                    "sum"
                ),
                failed_count=(
                    "status_clean",
                    lambda x:
                    (x == "FAILED").sum()
                )
            )
            .reset_index()
        )


        st.subheader("📈 Transaction Activity")

        tab1, tab2, tab3 = st.tabs(
            [
                "Volume",
                "Value",
                "Failures"
            ]
        )


        with tab1:

            fig = px.line(
                daily_tx,
                x="date",
                y="transaction_count",
                markers=True,
                title="Daily Transaction Volume"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with tab2:

            fig = px.area(
                daily_tx,
                x="date",
                y="transaction_amount",
                title="Daily Transaction Value"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with tab3:

            fig = px.bar(
                daily_tx,
                x="date",
                y="failed_count",
                title="Failed Transactions"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# TRANSACTION INVESTIGATION
# ============================================================

if (
    st.session_state.investigation_type
    == "transaction"
):

    txn_id = st.session_state.investigation_id

    result = tx[
        tx["txn_id_clean"]
        .astype(str)
        == str(txn_id)
    ]


    if len(result):

        row = result.iloc[0]

        st.markdown("---")

        st.header(
            f"🔎 Transaction Investigation — {txn_id}"
        )


        # ----------------------------------------------------
        # TRANSACTION KPIs
        # ----------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Transaction Amount",
            money(row.get("amount_clean", 0))
        )

        c2.metric(
            "Risk Score",
            f"{float(row.get('transaction_risk_score', 0)):.1f}/100"
        )

        c3.metric(
            "Risk Level",
            str(
                row.get(
                    "transaction_risk_level",
                    "UNKNOWN"
                )
            )
        )

        c4.metric(
            "Status",
            str(
                row.get(
                    "status_clean",
                    "UNKNOWN"
                )
            )
        )


        # ----------------------------------------------------
        # WHY FLAGGED
        # ----------------------------------------------------

        st.subheader("🚨 Why Was This Transaction Flagged?")

        reason = row.get(
            "risk_reasons",
            None
        )

        if pd.notna(reason):

            st.warning(
                str(reason)
            )

        else:

            st.info(
                "No detailed risk explanation is available "
                "for this transaction."
            )


        # ----------------------------------------------------
        # DETAILS
        # ----------------------------------------------------

        with st.expander(
            "📋 View Complete Transaction Details"
        ):

            st.dataframe(
                pd.DataFrame([row]),
                use_container_width=True
            )


        # ----------------------------------------------------
        # RELATED USER
        # ----------------------------------------------------

        user_id = row.get(
            "user_id_core",
            None
        )

        merchant_id = row.get(
            "merchant_id_core",
            None
        )


        st.subheader("🔗 Connected Entities")

        c1, c2 = st.columns(2)


        with c1:

            st.markdown("### 👤 User")

            st.write(user_id)

            if st.button(
                "Investigate User",
                key=f"user_{txn_id}"
            ):

                investigate(
                    "user",
                    user_id
                )

                st.rerun()


        with c2:

            st.markdown("### 🏪 Merchant")

            st.write(merchant_id)

            if st.button(
                "Investigate Merchant",
                key=f"merchant_{txn_id}"
            ):

                investigate(
                    "merchant",
                    merchant_id
                )

                st.rerun()


# ============================================================
# MERCHANT INTELLIGENCE
# ============================================================

elif page == "🏪 Merchant Intelligence":

    st.header("🏪 Merchant Risk Intelligence")


    merchant_sorted = (
        merchants
        .sort_values(
            "risk_score",
            ascending=False
        )
        .copy()
    )


    display_cols = [
        c for c in [
            "merchant_id_core",
            "merchant_name",
            "merchant_category_clean",
            "transaction_count",
            "total_amount",
            "chargeback_count",
            "chargeback_ratio",
            "failed_rate",
            "risk_score",
            "risk_level"
        ]
        if c in merchant_sorted.columns
    ]


    st.dataframe(
        merchant_sorted[
            display_cols
        ].head(100),
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # MERCHANT SELECTION
    # --------------------------------------------------------

    st.subheader("🔎 Investigate Merchant")

    merchant_ids = (
        merchant_sorted[
            "merchant_id_core"
        ]
        .astype(str)
        .tolist()
    )


    selected_merchant = st.selectbox(
        "Select Merchant",
        merchant_ids
    )


    if st.button(
        "🔎 Open Merchant Investigation"
    ):

        investigate(
            "merchant",
            selected_merchant
        )

        st.rerun()


    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    c1, c2 = st.columns(2)


    with c1:

        fig = px.bar(
            merchant_sorted.head(15),
            x="merchant_name"
            if "merchant_name"
            in merchant_sorted.columns
            else "merchant_id_core",
            y="risk_score",
            title="Top Merchant Risk Scores",
            text_auto=".1f"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    with c2:

        if "merchant_category_clean" in merchants.columns:

            cat = (
                merchants
                .groupby(
                    "merchant_category_clean",
                    dropna=False
                )
                .agg(
                    transaction_count=(
                        "transaction_count",
                        "sum"
                    ),
                    disputed_amount=(
                        "disputed_amount",
                        "sum"
                    )
                    if "disputed_amount"
                    in merchants.columns
                    else (
                        "total_amount",
                        "sum"
                    )
                )
                .reset_index()
            )

            fig = px.bar(
                cat.sort_values(
                    "disputed_amount",
                    ascending=False
                ),
                x="merchant_category_clean",
                y="disputed_amount",
                title="Disputed Amount by Category"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# MERCHANT INVESTIGATION
# ============================================================

if (
    st.session_state.investigation_type
    == "merchant"
):

    merchant_id = (
        st.session_state.investigation_id
    )


    result = merchants[
        merchants["merchant_id_core"]
        .astype(str)
        == str(merchant_id)
    ]


    if len(result):

        merchant = result.iloc[0]

        st.markdown("---")

        st.header(
            f"🔎 Merchant Investigation — "
            f"{merchant.get('merchant_name', merchant_id)}"
        )


        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Risk Score",
            f"{float(merchant.get('risk_score', 0)):.1f}"
        )

        c2.metric(
            "Transactions",
            f"{int(merchant.get('transaction_count', 0)):,}"
        )

        c3.metric(
            "Chargeback Ratio",
            pct(
                merchant.get(
                    "chargeback_ratio",
                    0
                )
            )
        )

        c4.metric(
            "Failed Rate",
            pct(
                merchant.get(
                    "failed_rate",
                    0
                )
            )
        )


        st.subheader("🚨 Merchant Risk Factors")

        st.warning(
            merchant.get(
                "risk_reasons",
                "No risk explanation available."
            )
        )


        with st.expander(
            "📋 Complete Merchant Profile"
        ):

            st.dataframe(
                pd.DataFrame([merchant]),
                use_container_width=True
            )


        # ----------------------------------------------------
        # RELATED TRANSACTIONS
        # ----------------------------------------------------

        if "merchant_id_core" in tx.columns:

            related = tx[
                tx["merchant_id_core"]
                .astype(str)
                == str(merchant_id)
            ]

            st.subheader(
                f"💳 Related Transactions ({len(related):,})"
            )

            if "transaction_risk_score" in related.columns:

                related = related.sort_values(
                    "transaction_risk_score",
                    ascending=False
                )

            st.dataframe(
                related.head(100),
                use_container_width=True
            )


# ============================================================
# USER & KYC
# ============================================================

elif page == "👤 User & KYC Risk":

    st.header("👤 User & KYC Risk")


    risk_cols = [
        c for c in [
            "user_id_core",
            "transaction_count",
            "total_amount",
            "chargeback_count",
            "disputed_amount",
            "chargeback_ratio",
            "failed_rate",
            "identity_conflict_score",
            "kyc_status_clean",
            "risk_segment_clean",
            "risk_score",
            "risk_level",
            "risk_reasons"
        ]
        if c in users.columns
    ]


    sorted_users = (
        users
        .sort_values(
            "risk_score",
            ascending=False
        )
    )


    st.dataframe(
        sorted_users[
            risk_cols
        ].head(100),
        use_container_width=True,
        hide_index=True
    )


    st.subheader("🔎 Investigate User")


    user_ids = (
        sorted_users[
            "user_id_core"
        ]
        .astype(str)
        .tolist()
    )


    selected_user = st.selectbox(
        "Select User",
        user_ids
    )


    if st.button(
        "🔎 Open User Investigation"
    ):

        investigate(
            "user",
            selected_user
        )

        st.rerun()


    if "kyc_status_clean" in users.columns:

        kyc_dist = (
            users["kyc_status_clean"]
            .value_counts()
            .reset_index()
        )

        kyc_dist.columns = [
            "status",
            "count"
        ]

        fig = px.pie(
            kyc_dist,
            names="status",
            values="count",
            hole=0.45,
            title="KYC Status Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# USER INVESTIGATION
# ============================================================

if (
    st.session_state.investigation_type
    == "user"
):

    user_id = (
        st.session_state.investigation_id
    )


    result = users[
        users["user_id_core"]
        .astype(str)
        == str(user_id)
    ]


    if len(result):

        user = result.iloc[0]

        st.markdown("---")

        st.header(
            f"🔎 User Investigation — {user_id}"
        )


        c1, c2, c3, c4 = st.columns(4)


        c1.metric(
            "Risk Score",
            f"{float(user.get('risk_score', 0)):.1f}"
        )

        c2.metric(
            "Risk Level",
            str(
                user.get(
                    "risk_level",
                    "UNKNOWN"
                )
            )
        )

        c3.metric(
            "Transactions",
            f"{int(user.get('transaction_count', 0)):,}"
        )

        c4.metric(
            "Chargeback Ratio",
            pct(
                user.get(
                    "chargeback_ratio",
                    0
                )
            )
        )


        st.subheader(
            "🚨 Why Is This User Risky?"
        )

        st.warning(
            user.get(
                "risk_reasons",
                "No explanation available."
            )
        )


        with st.expander(
            "📋 Complete User Profile"
        ):

            st.dataframe(
                pd.DataFrame([user]),
                use_container_width=True
            )


        # RELATED TRANSACTIONS

        if "user_id_core" in tx.columns:

            related = tx[
                tx["user_id_core"]
                .astype(str)
                == str(user_id)
            ]

            st.subheader(
                f"💳 User Transaction History ({len(related):,})"
            )

            st.dataframe(
                related.sort_values(
                    "timestamp_clean",
                    ascending=False
                ).head(100),
                use_container_width=True
            )


# ============================================================
# CHARGEBACKS
# ============================================================

elif page == "💰 Chargebacks":

    st.header("💰 Chargeback Intelligence")


    cb_amount = 0

    if "disputed_amount_calc" in chargebacks.columns:

        cb_amount = (
            chargebacks[
                "disputed_amount_calc"
            ].sum()
        )

    elif "disputed_amount_clean" in chargebacks.columns:

        cb_amount = (
            chargebacks[
                "disputed_amount_clean"
            ].sum()
        )


    delayed = 0

    if "delayed_dispute_7d_flag" in chargebacks.columns:

        delayed = int(
            chargebacks[
                "delayed_dispute_7d_flag"
            ].sum()
        )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Chargeback Records",
        f"{len(chargebacks):,}"
    )

    c2.metric(
        "Disputed Amount",
        money(cb_amount)
    )

    c3.metric(
        "Delayed > 7 Days",
        f"{delayed:,}"
    )


    if "reason_code_clean" in chargebacks.columns:

        reason = (
            chargebacks[
                "reason_code_clean"
            ]
            .value_counts()
            .reset_index()
        )

        reason.columns = [
            "reason",
            "count"
        ]


        fig = px.bar(
            reason,
            x="reason",
            y="count",
            title="Chargeback Reason Distribution",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    with st.expander(
        "📋 View Chargeback Records"
    ):

        st.dataframe(
            chargebacks.head(500),
            use_container_width=True
        )


# ============================================================
# FRAUD RINGS
# ============================================================

elif page == "🕸️ Fraud Rings":

    st.header("🕸️ Suspicious Fraud Rings")

    st.caption(
        "A ring represents suspicious connected activity "
        "supported by risk and/or dispute evidence. "
        "It is not proof of criminal conduct."
    )


    if len(rings) == 0:

        st.info(
            "No suspicious rings were detected."
        )

    else:

        ring_sorted = (
            rings
            .sort_values(
                "risk_score",
                ascending=False
            )
        )


        st.dataframe(
            ring_sorted.head(100),
            use_container_width=True
        )


        ring_ids = (
            ring_sorted["ring_id"]
            .astype(str)
            .tolist()
        )


        selected_ring = st.selectbox(
            "🕸️ Select Ring",
            ring_ids
        )


        if st.button(
            "🔎 Investigate Ring"
        ):

            investigate(
                "ring",
                selected_ring
            )

            st.rerun()


# ============================================================
# RING INVESTIGATION
# ============================================================

if (
    st.session_state.investigation_type
    == "ring"
):

    ring_id = (
        st.session_state.investigation_id
    )


    result = rings[
        rings["ring_id"]
        .astype(str)
        == str(ring_id)
    ]


    if len(result):

        ring = result.iloc[0]

        st.markdown("---")

        st.header(
            f"🕸️ Fraud Ring Investigation — {ring_id}"
        )


        c1, c2, c3, c4 = st.columns(4)


        c1.metric(
            "Risk Score",
            f"{float(ring.get('risk_score', 0)):.1f}"
        )

        c2.metric(
            "Users",
            int(ring.get("user_count", 0))
        )

        c3.metric(
            "Merchants",
            int(ring.get("merchant_count", 0))
        )

        c4.metric(
            "Chargebacks",
            int(ring.get("chargeback_count", 0))
        )


        st.subheader("🚨 Evidence")

        st.warning(
            ring.get(
                "risk_reasons",
                "No evidence description available."
            )
        )


        ring_members = members[
            members["ring_id"]
            .astype(str)
            == str(ring_id)
        ]


        st.subheader(
            f"👥 Ring Members ({len(ring_members):,})"
        )


        st.dataframe(
            ring_members,
            use_container_width=True
        )


# ============================================================
# AI INVESTIGATOR
# ============================================================

elif page == "🔎 AI Investigator":

    st.header("🤖 AI Investigator")

    st.caption(
        "Ask natural-language questions about PayForensics data. "
        "This assistant is restricted to analysis of this project only."
    )

    # --------------------------------------------------------
    # GEMINI CONFIGURATION
    # --------------------------------------------------------

    # ========================================================
    # PUT YOUR GEMINI API KEY HERE
    # ========================================================
    # Example:
    # GEMINI_API_KEY = "AIzaSy................................"
    #
    # Leave the placeholder below until you paste your own key.
    # The environment-variable / Streamlit-secrets fallback is kept
    # so the same code can also be deployed securely later.
    GEMINI_API_KEY = "AQ.Ab8RN6L1Z9Myq00Khj6L4S9SVsGApGmrLA1dbo1elAKb_oiF6w"

    api_key = GEMINI_API_KEY.strip()

    # Optional fallback for deployments using secrets/environment variables.
    if not api_key or api_key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key or api_key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        try:
            api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        except Exception:
            api_key = ""

    # Free-tier friendly model for this analytics chatbot.
    model_name = os.getenv(
        "PAYFORENSICS_GEMINI_MODEL",
        "gemini-3.1-flash-lite"
    )

    # --------------------------------------------------------
    # DATASET CATALOG
    # --------------------------------------------------------

    datasets = {
        # Transactions respect the dashboard's active global filters.
        "transactions": filtered_tx,
        "users": users,
        "merchants": merchants,
        "chargebacks": chargebacks,
        "fraud_rings": rings,
        "ring_members": members,
        "daily_metrics": daily,
        "kyc": kyc,
        "summary": summary,
    }

    dataset_descriptions = {
        "transactions": "Transaction-level activity, amounts, status, risk, users, merchants and chargebacks.",
        "users": "User-level risk, KYC/risk segments, transaction totals, failed rates and chargebacks.",
        "merchants": "Merchant-level transaction totals, chargebacks, disputed amounts, risk and categories.",
        "chargebacks": "Chargeback/dispute records and reason codes.",
        "fraud_rings": "Detected suspicious connected fraud-ring summaries and risk evidence.",
        "ring_members": "Users/merchants associated with detected fraud rings.",
        "daily_metrics": "Daily transaction and fraud-related aggregate metrics.",
        "kyc": "KYC master records and KYC-related attributes.",
        "summary": "Project-level summary metrics.",
    }

    # --------------------------------------------------------
    # SAFE DATASET SCHEMA FOR THE MODEL
    # --------------------------------------------------------

    def build_dataset_schema():

        schema = {}

        for name, frame in datasets.items():

            columns = {}

            for col in frame.columns:

                dtype = str(frame[col].dtype)
                info = {"dtype": dtype}

                # Give the model a few categorical examples so it can
                # understand values without receiving the whole dataset.
                if frame[col].dtype == "object":
                    vals = (
                        frame[col]
                        .dropna()
                        .astype(str)
                        .drop_duplicates()
                        .head(8)
                        .tolist()
                    )
                    info["examples"] = vals

                columns[col] = info

            schema[name] = {
                "description": dataset_descriptions.get(name, ""),
                "rows": int(len(frame)),
                "columns": columns,
            }

        return schema


    # --------------------------------------------------------
    # SAFE ANALYTICS PLAN
    # --------------------------------------------------------

    PLAN_SCHEMA = {
        "type": "object",
        "properties": {
            "in_scope": {"type": "boolean"},
            "reason": {"type": "string"},
            "dataset": {
                "type": "string",
                "enum": [
                    "transactions",
                    "users",
                    "merchants",
                    "chargebacks",
                    "fraud_rings",
                    "ring_members",
                    "daily_metrics",
                    "kyc",
                    "summary"
                ]
            },
            "operation": {
                "type": "string",
                "enum": [
                    "count",
                    "sum",
                    "mean",
                    "min",
                    "max",
                    "top_n",
                    "bottom_n",
                    "distribution",
                    "grouped_summary",
                    "trend",
                    "lookup"
                ]
            },
            "metric": {"type": "string"},
            "group_by": {"type": "string"},
            "time_column": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "sort_direction": {
                "type": "string",
                "enum": ["asc", "desc"]
            },
            "filters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {
                            "type": "string",
                            "enum": [
                                "eq",
                                "neq",
                                "gt",
                                "gte",
                                "lt",
                                "lte",
                                "contains",
                                "in"
                            ]
                        },
                        "value": {"type": "string"}
                    },
                    "required": ["field", "operator", "value"]
                }
            },
            "columns": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": [
            "in_scope",
            "reason",
            "dataset",
            "operation",
            "metric",
            "group_by",
            "time_column",
            "limit",
            "sort_direction",
            "filters",
            "columns"
        ]
    }


    def get_gemini_client():
        if genai is None:
            return None

        if not api_key:
            return None

        return genai.Client(api_key=api_key)


    def make_plan(question):
        """Ask the model to translate the question into a SAFE analytics plan."""

        client = get_gemini_client()

        if client is None:
            return None, (
                "Gemini is not configured. Install the Google GenAI SDK and set "
                "GEMINI_API_KEY before using the chatbot."
            )

        schema = build_dataset_schema()

        system_prompt = """
You are the PayForensics Analytics Planner.

Your ONLY job is to analyze the PayForensics project datasets described in the
provided schema. You MUST NOT answer general questions, casual conversation,
programming questions, coding questions, personal questions, current events,
medical/legal/financial advice, or anything unrelated to analysis of these
PayForensics datasets.

If the user asks anything outside this project-data-analysis scope, set
in_scope=false. Do not try to answer the unrelated question.

For an in-scope question, create a SAFE analytics plan using ONLY the listed
 datasets, columns and operations. Never invent a column. Never request code
execution. Never request web search. Never request external data.

The application will execute your plan locally with pandas. You are NOT
allowed to write Python code or SQL.

For optional fields metric, group_by, and time_column, return an empty string "" when the field is not needed. Never return null for these fields.

Interpret natural language flexibly. Examples:
- "highest chargeback ratio merchant" -> merchants/top_n/chargeback_ratio
- "how many critical transactions" -> transactions/count filtered by
  transaction_risk_level = CRITICAL
- "average transaction amount" -> transactions/mean/amount_clean
- "which category has the most disputed amount" -> merchants/grouped_summary,
  group_by merchant_category_clean, metric disputed_amount, descending
- "show failed transactions above 10000" -> transactions/lookup with filters
- "find transactions for these statuses" -> use the `in` filter with a
  comma-separated value such as "FAILED,PENDING"
- "daily transaction volume" -> daily_metrics/trend using date and
  transaction_count when available

Use the dataset that best directly answers the question.
"""

        user_prompt = (
            "PAYFORENSICS DATASET SCHEMA:\n"
            + json.dumps(schema, default=str)
            + "\n\nUSER QUESTION:\n"
            + question
        )

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=system_prompt + "\n\n" + user_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PLAN_SCHEMA,
                    temperature=0
                )
            )

            plan = json.loads(response.text)
            return plan, None

        except Exception as exc:
            return None, f"AI planning error: {exc}"


    # --------------------------------------------------------
    # LOCAL SAFE PLAN VALIDATION
    # --------------------------------------------------------

    ALLOWED_DATASETS = set(datasets.keys())

    ALLOWED_OPERATIONS = {
        "count",
        "sum",
        "mean",
        "min",
        "max",
        "top_n",
        "bottom_n",
        "distribution",
        "grouped_summary",
        "trend",
        "lookup"
    }

    ALLOWED_OPERATORS = {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
        "in"
    }


    def validate_plan(plan):

        if not isinstance(plan, dict):
            return False, "Invalid analytics plan."

        if not plan.get("in_scope", False):
            return False, plan.get(
                "reason",
                "I can only answer questions about PayForensics project data analysis."
            )

        dataset_name = plan.get("dataset")
        operation = plan.get("operation")

        if dataset_name not in ALLOWED_DATASETS:
            return False, "That dataset is not available in PayForensics."

        if operation not in ALLOWED_OPERATIONS:
            return False, "That analysis operation is not supported."

        frame = datasets[dataset_name]
        available = set(frame.columns)

        metric = plan.get("metric")
        group_by = plan.get("group_by")
        time_column = plan.get("time_column")
        columns = plan.get("columns", [])

        for field in [metric, group_by, time_column]:
            if field and field not in available:
                return False, f"Column '{field}' is not available in {dataset_name}."

        for field in columns:
            if field not in available:
                return False, f"Column '{field}' is not available in {dataset_name}."

        for filt in plan.get("filters", []):
            field = filt.get("field")
            operator = filt.get("operator")

            if field not in available:
                return False, f"Filter column '{field}' is not available in {dataset_name}."

            if operator not in ALLOWED_OPERATORS:
                return False, "Unsupported filter operator."

        if operation in {"sum", "mean", "min", "max", "top_n", "bottom_n", "grouped_summary"}:
            if not metric:
                return False, "This analysis requires a metric column."

        if operation == "grouped_summary" and not group_by:
            return False, "This analysis requires a grouping column."

        if operation == "trend" and not time_column:
            return False, "This trend analysis requires a time column."

        return True, ""


    # --------------------------------------------------------
    # LOCAL PANDAS EXECUTION
    # --------------------------------------------------------

    def apply_filters(frame, filters):

        result = frame.copy()

        for filt in filters:

            field = filt["field"]
            op = filt["operator"]
            value = filt["value"]

            series = result[field]

            if op in {"gt", "gte", "lt", "lte"}:
                numeric_series = pd.to_numeric(series, errors="coerce")
                try:
                    value = float(value)
                except Exception:
                    pass
                series_for_compare = numeric_series
            else:
                series_for_compare = series

            if op == "eq":
                result = result[series_for_compare.astype(str).str.upper() == str(value).upper()]

            elif op == "neq":
                result = result[series_for_compare.astype(str).str.upper() != str(value).upper()]

            elif op == "gt":
                result = result[series_for_compare > value]

            elif op == "gte":
                result = result[series_for_compare >= value]

            elif op == "lt":
                result = result[series_for_compare < value]

            elif op == "lte":
                result = result[series_for_compare <= value]

            elif op == "contains":
                result = result[
                    result[field]
                    .astype(str)
                    .str.contains(str(value), case=False, na=False)
                ]

            elif op == "in":
                values = [v.strip() for v in str(value).split(",") if v.strip()]
                result = result[
                    result[field].astype(str).str.upper().isin(
                        [str(v).upper() for v in values]
                    )
                ]

        return result


    def execute_plan(plan):

        frame = datasets[plan["dataset"]].copy()
        frame = apply_filters(frame, plan.get("filters", []))

        operation = plan["operation"]
        metric = plan.get("metric")
        group_by = plan.get("group_by")
        time_column = plan.get("time_column")
        limit = max(1, min(int(plan.get("limit", 10)), 50))
        direction = plan.get("sort_direction", "desc")

        if operation == "count":
            return {
                "type": "metric",
                "dataset": plan["dataset"],
                "rows_after_filters": len(frame),
                "value": int(len(frame)),
                "label": "Count"
            }

        if operation in {"sum", "mean", "min", "max"}:

            numeric = pd.to_numeric(frame[metric], errors="coerce")

            if operation == "sum":
                value = numeric.sum()
            elif operation == "mean":
                value = numeric.mean()
            elif operation == "min":
                value = numeric.min()
            else:
                value = numeric.max()

            return {
                "type": "metric",
                "dataset": plan["dataset"],
                "rows_after_filters": len(frame),
                "metric": metric,
                "operation": operation,
                "value": None if pd.isna(value) else float(value),
                "label": f"{operation.title()} of {metric}"
            }

        if operation in {"top_n", "bottom_n"}:

            result = frame.copy()
            result[metric] = pd.to_numeric(
                result[metric],
                errors="coerce"
            )

            result = result.sort_values(
                metric,
                ascending=(operation == "bottom_n")
            ).head(limit)

            return {
                "type": "table",
                "dataset": plan["dataset"],
                "operation": operation,
                "metric": metric,
                "rows_after_filters": len(frame),
                "data": result[plan.get("columns") or list(result.columns)].to_dict(orient="records")
            }

        if operation == "distribution":

            result = (
                frame[metric]
                .astype(str)
                .value_counts(dropna=False)
                .head(limit)
                .rename_axis(metric)
                .reset_index(name="count")
            )

            return {
                "type": "table",
                "dataset": plan["dataset"],
                "operation": operation,
                "rows_after_filters": len(frame),
                "data": result.to_dict(orient="records")
            }

        if operation == "grouped_summary":

            work = frame.copy()
            work[metric] = pd.to_numeric(
                work[metric],
                errors="coerce"
            )

            result = (
                work
                .groupby(group_by, dropna=False)[metric]
                .agg(["count", "sum", "mean"])
                .reset_index()
                .sort_values(
                    "sum",
                    ascending=(direction == "asc")
                )
                .head(limit)
            )

            return {
                "type": "table",
                "dataset": plan["dataset"],
                "operation": operation,
                "group_by": group_by,
                "metric": metric,
                "rows_after_filters": len(frame),
                "data": result.to_dict(orient="records")
            }

        if operation == "trend":

            work = frame.copy()
            work[time_column] = pd.to_datetime(
                work[time_column],
                errors="coerce"
            )

            if metric:
                work[metric] = pd.to_numeric(
                    work[metric],
                    errors="coerce"
                )

                result = (
                    work
                    .dropna(subset=[time_column])
                    .groupby(
                        work[time_column].dt.date
                    )[metric]
                    .sum()
                    .reset_index()
                )

                result.columns = ["date", metric]

            else:
                result = (
                    work
                    .dropna(subset=[time_column])
                    .groupby(
                        work[time_column].dt.date
                    )
                    .size()
                    .reset_index(name="count")
                )
                result.columns = ["date", "count"]

            return {
                "type": "trend",
                "dataset": plan["dataset"],
                "metric": metric,
                "data": result.tail(100).to_dict(orient="records")
            }

        # lookup
        if operation == "lookup":

            selected_columns = plan.get("columns") or list(frame.columns)
            selected_columns = [
                c for c in selected_columns
                if c in frame.columns
            ]

            result = frame[selected_columns].head(limit)

            return {
                "type": "table",
                "dataset": plan["dataset"],
                "operation": operation,
                "rows_after_filters": len(frame),
                "data": result.to_dict(orient="records")
            }

        raise ValueError("Unsupported analytics operation.")


    # --------------------------------------------------------
    # NATURAL-LANGUAGE ANSWER
    # --------------------------------------------------------

    def explain_result(question, plan, result):

        client = get_gemini_client()

        if client is None:
            return None

        prompt = f"""
You are the PayForensics Analytics Assistant.

You may ONLY explain the result of an analysis performed on PayForensics project
 data. Do not introduce outside facts, web information, assumptions or advice.

Answer the user's question using ONLY the supplied analysis result.
Be concise but useful. Mention important numbers and what they mean in the
context of this dataset. If the result is empty, say that no matching data was
found. Do not claim causation unless the result directly establishes it.

USER QUESTION:
{question}

ANALYSIS PLAN:
{json.dumps(plan, default=str)}

LOCAL ANALYSIS RESULT:
{json.dumps(result, default=str)}
"""

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2
                )
            )
            return response.text.strip()
        except Exception:
            return None


    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

    if "payforensics_chat" not in st.session_state:
        st.session_state.payforensics_chat = []


    # --------------------------------------------------------
    # QUICK QUESTIONS
    # --------------------------------------------------------

    st.subheader("⚡ Quick Investigation Questions")

    q1, q2, q3 = st.columns(3)

    if "ai_query" not in st.session_state:
        st.session_state.ai_query = ""

    with q1:
        if st.button(
            "🏪 Highest Chargeback Merchant",
            use_container_width=True,
            key="quick_chargeback_merchant"
        ):
            st.session_state.ai_query = "Which merchant has the highest chargeback ratio?"
            st.rerun()

    with q2:
        if st.button(
            "💰 Highest Disputed Merchant",
            use_container_width=True,
            key="quick_disputed_merchant"
        ):
            st.session_state.ai_query = "Which merchant has the highest disputed amount?"
            st.rerun()

    with q3:
        if st.button(
            "👤 Highest Disputed User",
            use_container_width=True,
            key="quick_disputed_user"
        ):
            st.session_state.ai_query = "Which user has the highest disputed amount?"
            st.rerun()


    # --------------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------------

    query = st.text_input(
        "Ask about the PayForensics data",
        key="ai_query",
        placeholder=(
            "Example: Which merchant has the highest chargeback ratio?"
        )
    )


    if query.strip():

        if not api_key:

            st.warning(
                "🔑 The PayForensics chatbot needs a Gemini API key. "
                "Set GEMINI_API_KEY as an environment variable or in "
                "Streamlit secrets."
            )

        elif genai is None:

            st.error(
                "The Google GenAI Python SDK is not installed. Run: "
                "pip install -U google-genai"
            )

        else:

            with st.spinner("Analyzing PayForensics data..."):

                plan, plan_error = make_plan(query.strip())

            if plan_error:

                st.error(plan_error)

            else:

                valid, validation_error = validate_plan(plan)

                if not valid:

                    st.info(
                        "🛡️ I can only answer data-analysis questions about "
                        "the PayForensics project.\n\n"
                        + validation_error
                    )

                else:

                    try:

                        result = execute_plan(plan)

                        # Save the conversation only in this Streamlit session.
                        st.session_state.payforensics_chat.append({
                            "question": query.strip(),
                            "plan": plan,
                            "result": result
                        })

                        explanation = explain_result(
                            query.strip(),
                            plan,
                            result
                        )

                        if explanation:
                            st.success(explanation)
                        else:
                            st.success(
                                "Analysis completed. See the result below."
                            )

                        # ------------------------------------------------
                        # RESULT DISPLAY
                        # ------------------------------------------------

                        if result["type"] == "metric":

                            value = result.get("value")
                            metric = result.get("metric")

                            if metric and any(
                                word in str(metric).lower()
                                for word in ["amount", "value", "total", "score"]
                            ):
                                display_value = money(value or 0)
                            else:
                                display_value = (
                                    f"{value:,.4f}"
                                    if isinstance(value, float)
                                    else f"{value:,}"
                                )

                            st.metric(
                                result.get("label", "Result"),
                                display_value
                            )

                        elif result["type"] in {"table", "trend"}:

                            result_df = pd.DataFrame(
                                result.get("data", [])
                            )

                            if len(result_df):
                                st.dataframe(
                                    result_df,
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.info("No matching records were found.")

                            if result["type"] == "trend" and len(result_df) >= 2:

                                date_col = "date"
                                value_cols = [
                                    c for c in result_df.columns
                                    if c != date_col
                                ]

                                if value_cols:
                                    chart_col = value_cols[0]
                                    fig = px.line(
                                        result_df,
                                        x=date_col,
                                        y=chart_col,
                                        markers=True,
                                        title="PayForensics Trend"
                                    )
                                    st.plotly_chart(
                                        fig,
                                        use_container_width=True
                                    )

                    except Exception as exc:

                        st.error(
                            f"I couldn't execute that analysis safely: {exc}"
                        )


    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

    if st.session_state.payforensics_chat:

        with st.expander("🧾 Recent PayForensics Questions"):

            for item in reversed(
                st.session_state.payforensics_chat[-5:]
            ):
                st.markdown(
                    f"**You:** {item['question']}"
                )


    st.caption(
        "🔒 Scope locked: this assistant analyzes only the loaded PayForensics "
        "datasets. It does not provide general-purpose chat, web search, "
        "coding help, or unrelated answers."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "PayForensics AI • Datathon Decision-Support Prototype"
)