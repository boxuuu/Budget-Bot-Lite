import streamlit as st
import pandas as pd
from database import save_transactions, load_all_transactions, get_months
from categoriser import categorise_all, recategorise_all
from database import get_db, Transaction

st.set_page_config(page_title="Budget Bot", layout="wide")
st.title(":material/savings: Budget Bot")

# Shared styling: every card container uses key="card_<page>_<section>" so
# this one rule can style them all at once, without touching background/text
# colors (those come from primaryColor + Streamlit's native light/dark
# resolution, set in .streamlit/config.toml, so the built-in theme toggle
# keeps working). Also carries the enlarged-metric rule previously
# duplicated per-page on Net Worth.
st.markdown(
    """
    <style>
    /* Forest green palette - deliberately darker/more muted than the bright
       teal-green (#1D9E75, primaryColor) already used everywhere for DATA
       (chart lines, positive deltas, KPI arrows) - kept as a separate chrome
       color for structure/navigation so the two greens read as distinct,
       not a clash. */
    :root {
        --forest-deep: #1b3a2b;
        --forest-mid: #3a7a5a;
        --forest-soft: #e7efe9;
        --forest-page-bg: #f2f7f4;
    }

    /* Typography: swap Streamlit's default for a native system stack -
       crisper on macOS, and every fallback here is already installed on
       Windows/Linux too, so nothing needs to be loaded over the network. */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    /* Main page background: a faint sage tint instead of stark white, so it
       reads as part of the same forest-green palette as the sidebar rather
       than a plain default canvas. Light mode only - dark mode already uses
       Streamlit's own dark background, which isn't "stark" in the same way. */
    @media (prefers-color-scheme: light) {
        .stApp {
            background-color: var(--forest-page-bg);
        }
        [data-testid="stHeader"] {
            background-color: var(--forest-page-bg);
        }
    }
    h1, h2, h3, h4 {
        font-weight: 650;
        letter-spacing: -0.01em;
    }

    div[class*="st-key-card_"] {
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        border-radius: 0.9rem;
        border: 1px solid rgba(45, 106, 79, 0.14);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    @media (prefers-color-scheme: dark) {
        div[class*="st-key-card_"] {
            border-color: rgba(45, 106, 79, 0.3);
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
        }
    }
    .st-key-nw_asset_metric [data-testid="stMetricValue"],
    .st-key-nw_total_metric [data-testid="stMetricValue"] {
        font-size: 3rem;
    }

    /* Buttons: rounded corners + a small hover lift instead of Streamlit's
       flat default, applied everywhere (Personal/Household Budget grids,
       Recurring Charges actions, Net Worth asset rows, etc.) - hover shadow
       tinted forest green rather than plain grey/black. */
    .stButton > button, .stDownloadButton > button {
        border-radius: 0.6rem;
        transition: transform 0.1s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(45, 106, 79, 0.25);
    }

    /* Sidebar: dark forest-green chrome instead of Streamlit's default flat
       grey panel - fixed regardless of the light/dark/system toggle (which
       only ever affects the main content area; config.toml sets no
       background colors), the same way a permanent dark nav rail works in
       most real apps (VS Code, Slack, Notion). Text/icons forced to a soft
       off-white for contrast, since Streamlit's own sidebar text color is
       tuned for the light grey panel, not a dark one. */
    [data-testid="stSidebar"] {
        background-color: var(--forest-deep);
    }
    [data-testid="stSidebar"] * {
        color: var(--forest-soft) !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(231, 239, 233, 0.15);
    }
    [data-testid="stSidebar"] [data-baseweb="textarea"],
    [data-testid="stSidebar"] [data-baseweb="base-input"] {
        background-color: rgba(231, 239, 233, 0.07);
    }

    /* Sidebar nav: the page picker is a plain st.radio under the hood, so
       style it to read as a real nav list - a solid forest-green pill for
       the active page (:has(input:checked), safe in all current browsers)
       and a subtle light hover tint on the rest. */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
        border-radius: 0.6rem;
        padding: 0.4rem 0.6rem;
        margin-bottom: 0.15rem;
        transition: background-color 0.15s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background-color: rgba(231, 239, 233, 0.08);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: var(--forest-mid);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Sidebar ---
st.sidebar.title("Navigation")

PAGE_ICONS = {
    "Dashboard": "space_dashboard",
    "Net Worth": "trending_up",
    "Personal Budget": "account_balance_wallet",
    "Household Budget": "home",
    "Goals": "flag",
    "Upload Statement": "upload_file",
    "View Transactions": "receipt_long",
    "Manage Categories": "sell",
}
# format_func only changes the displayed label (icon + name) - the returned
# `page` value stays a plain page name, so every `elif page == "...":` check
# below is untouched.
page = st.sidebar.radio(
    "Go to", list(PAGE_ICONS.keys()),
    format_func=lambda p: f":material/{PAGE_ICONS[p]}: {p}"
)

st.sidebar.divider()

# --- Persistent Chat (always visible, independent of which page is selected) ---
with st.sidebar:
    st.subheader("Chat with Budget Bot")

    from chat import chat_with_budget_bot, update_category
    from networth import update_asset_value

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None

    chat_history = st.container(height=400)
    with chat_history:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        if st.session_state.pending_action:
            action = st.session_state.pending_action
            with st.chat_message("assistant"), st.container(border=True, key="chatcard_pending_action"):
                st.write(action["display"])
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm", key="confirm_pending_action", use_container_width=True):
                        if action["type"] == "update_networth":
                            update_asset_value(action["asset_name"], action["value"])
                            result_text = f"Updated {action['asset_name']} to £{action['value']:,.2f}."
                        else:
                            count = update_category(action["merchant_name"], action["new_category"])
                            result_text = f"Updated {count} transaction(s) to {action['new_category']}."
                        st.session_state.messages.append({"role": "assistant", "content": result_text})
                        st.session_state.pending_action = None
                        st.rerun()
                with cancel_col:
                    if st.button("Cancel", key="cancel_pending_action", use_container_width=True):
                        st.session_state.messages.append({"role": "assistant", "content": "Okay, no changes made."})
                        st.session_state.pending_action = None
                        st.rerun()

    if prompt := st.chat_input("Ask Budget Bot something..."):
        if st.session_state.pending_action:
            st.session_state.pending_action = None

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with chat_history:
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    result = chat_with_budget_bot(
                        st.session_state.messages[:-1],
                        prompt
                    )
                    st.write(result["text"])

        if result["pending_action"]:
            st.session_state.pending_action = result["pending_action"]
            st.rerun()
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["text"]
            })

# --- Dashboard Page ---
if page == "Dashboard":
    st.header(":material/space_dashboard: Dashboard")

    all_transactions = load_all_transactions()

    if not all_transactions:
        st.info("No transactions yet - upload a statement first")
    else:
        import plotly.express as px
        from datetime import datetime, timedelta
        from analytics import month_sort_key, calculate_savings_rate, format_gbp
        from networth import get_total_net_worth_series

        df = pd.DataFrame([{
            'Date': t.date,
            'Description': t.description,
            'Amount': t.amount,
            'Category': t.category,
            'Month': t.month
        } for t in all_transactions])
        df['DateParsed'] = pd.to_datetime(df['Date'], format='%d %b %Y')

        # Separate money out (negative) from money in (positive)
        spending = df[df['Amount'] < 0].copy()
        spending['Amount'] = spending['Amount'].abs()

        # Same time-range filter options as the Net Worth page, reused here
        # for the pie chart and trend chart (each has its own independent
        # selection via a distinct key_prefix) rather than one filter for
        # the whole Dashboard, since "spending by category this month" and
        # "the 6-month trend" are both reasonable things to want at once.
        now = datetime.utcnow()
        time_filters = {
            'All': None,
            '1 Year': now - timedelta(days=365),
            'YTD': datetime(now.year, 1, 1),
            '6 Months': now - timedelta(days=182),
            '1 Month': now - timedelta(days=30)
        }

        # Short button text so "6 Months" doesn't word-wrap mid-word in the
        # half-width pie chart card - the full name still shows in the
        # "Showing: ..." caption below the buttons.
        short_labels = {'All': 'All', '1 Year': '1yr', 'YTD': 'YTD', '6 Months': '6mo', '1 Month': '1mo'}

        def render_time_filter(key_prefix):
            cols = st.columns(5)
            state_key = f"{key_prefix}_filter"
            if state_key not in st.session_state:
                st.session_state[state_key] = 'All'
            for col, label in zip(cols, time_filters.keys()):
                with col:
                    if st.button(short_labels[label], key=f"{key_prefix}_filter_btn_{label}"):
                        st.session_state[state_key] = label
            selected = st.session_state[state_key]
            st.caption(f"Showing: {selected}")
            return time_filters[selected]

        # --- KPI row ---
        with st.container(border=True, key="card_dashboard_kpis"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                nw_series = get_total_net_worth_series()
                if not nw_series.empty:
                    current_net_worth = nw_series.iloc[-1]['Total']
                    six_months_ago = datetime.utcnow().date() - timedelta(days=182)
                    past = nw_series[nw_series['Date'] <= six_months_ago]
                    baseline = past.iloc[-1]['Total'] if not past.empty else nw_series.iloc[0]['Total']
                    nw_pct_change = ((current_net_worth - baseline) / baseline * 100) if baseline else 0
                    st.metric("Net Worth", f"£{current_net_worth:,.0f}", delta=f"{nw_pct_change:+.1f}% (6mo)")
                else:
                    st.metric("Net Worth", "No data yet")

            # Both KPIs below are genuinely scoped to the trailing 6 months
            # (by DateParsed, same 182-day cutoff as the "6 Months" filter
            # elsewhere on this page) - previously "Total Spent (6 months)"
            # actually summed ALL-time spending regardless of the label, and
            # "Monthly Average" divided that all-time total by a hardcoded 6,
            # wildly inflating the figure once more than 6 months of data
            # existed. Divides by the ACTUAL number of distinct months
            # present in the window, not a fixed 6, so it stays correct even
            # with less than 6 months of data.
            six_months_cutoff = now - timedelta(days=182)
            recent_spending = spending[spending['DateParsed'] >= six_months_cutoff]
            recent_months_count = recent_spending['Month'].nunique()

            with col2:
                st.metric("Total Spent (6 months)", f"£{recent_spending['Amount'].sum():,.2f}")

            with col3:
                # Discretionary only, same definition as the Goals page's
                # Spend Ceiling (goals.NON_DISCRETIONARY_CATEGORIES) -
                # excludes Savings & Investments (pot transfers, not
                # spending) and fixed costs (Rent & Housing, Bills &
                # Utilities, Insurance & Finance, Phone & Internet), so a
                # big one-off house-move charge or a savings push doesn't
                # dominate the figure. "Total Spent" above stays gross/
                # unmodified by design (per Known Issues) - this KPI is
                # deliberately the more "actionable" number instead.
                from goals import NON_DISCRETIONARY_CATEGORIES
                excluded_categories = ['Savings & Investments'] + NON_DISCRETIONARY_CATEGORIES
                discretionary_spending = recent_spending[~recent_spending['Category'].isin(excluded_categories)]
                monthly_avg = discretionary_spending['Amount'].sum() / recent_months_count if recent_months_count else 0
                st.metric(
                    "Monthly Average", f"£{monthly_avg:,.2f}",
                    help="Discretionary spend only - excludes Savings & Investments and fixed costs "
                         "(Rent & Housing, Bills & Utilities, Insurance & Finance, Phone & Internet)."
                )

            with col4:
                savings_info = calculate_savings_rate(all_transactions)
                if savings_info['typical_monthly_income']:
                    st.metric(
                        "Savings Rate",
                        f"{savings_info['savings_rate']:.0f}%",
                        delta=f"{format_gbp(savings_info['avg_savings'], decimals=0)}/mo",
                        help=(
                            "Average monthly saving into your long-term pots (Emergency Fund, "
                            "Wedding, SIPP, ISA, Round up) as a percentage of typical monthly "
                            "salary. A withdrawal from one of those pots reduces the figure - "
                            "money coming back out isn't new saving. Fun Money is excluded "
                            "entirely (both paying in and drawing down), since it behaves as a "
                            "spending buffer rather than genuine savings - without that "
                            "exclusion, its month-to-month churn would swamp real saving "
                            "elsewhere and could even show a negative rate in months you're "
                            "actually saving well."
                        )
                    )
                else:
                    st.metric("Savings Rate", "N/A")

        # --- Category pie + Top merchants ---
        col_pie, col_merchants = st.columns(2)

        with col_pie, st.container(border=True, key="card_dashboard_pie"):
            st.subheader("Spending by Category")
            pie_cutoff = render_time_filter("dashboard_pie")
            pie_spending = spending[spending['DateParsed'] >= pie_cutoff] if pie_cutoff else spending

            if pie_spending.empty:
                st.write("No spending data for this period.")
            else:
                category_totals = pie_spending.groupby('Category')['Amount'].sum().sort_values(ascending=False)

                # Cap the pie at the 6 biggest categories - beyond that it gets too
                # cluttered to read at a glance - and fold the rest into one slice.
                # The literal "Other" category is itself a catch-all, so it's
                # always folded in here too rather than ever shown as a top
                # slice - otherwise "Other" and "Other categories" would show up
                # side by side, which reads as a labeling mistake.
                real_categories = category_totals.drop('Other', errors='ignore')
                top6 = real_categories.head(6)
                other_total = category_totals.sum() - top6.sum()
                pie_data = top6.copy()
                if other_total > 0:
                    pie_data['Other categories'] = other_total
                pie_data = pie_data.reset_index()
                pie_data.columns = ['Category', 'Amount']

                # Validated categorical palette (fixed hue order), muted gray for
                # the folded "Other categories" bucket so it reads as an
                # aggregate rather than a peer category
                palette = ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#eb6834']
                color_map = {cat: palette[i] for i, cat in enumerate(top6.index)}
                color_map['Other categories'] = '#898781'

                fig_pie = px.pie(
                    pie_data, values='Amount', names='Category',
                    color='Category', color_discrete_map=color_map
                )
                fig_pie.update_traces(textinfo='label+percent', textposition='inside')
                fig_pie.update_layout(
                    showlegend=True,
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_pie, st.container(border=True, key="card_dashboard_goals"):
            st.subheader(":material/flag: Goals")

            from goals import get_current_goal, calculate_streak, get_discretionary_monthly_spend

            current_month_label = datetime.now().strftime('%b %Y')
            savings_by_month = {m: v for m, v in calculate_savings_rate(all_transactions)['savings_by_month'].items() if m != current_month_label}
            spend_by_month = {m: v for m, v in get_discretionary_monthly_spend(all_transactions).items() if m != current_month_label}

            savings_goal = get_current_goal('savings')
            spend_goal = get_current_goal('spend')

            if not savings_goal and not spend_goal:
                st.caption("No goals set yet - visit the Goals page to set a savings target or spend ceiling.")
            else:
                streak_col1, streak_col2 = st.columns(2)
                with streak_col1:
                    st.caption("Savings streak")
                    if savings_goal:
                        st.markdown(f":material/local_fire_department: **{calculate_streak('savings', savings_by_month)} months**")
                    else:
                        st.write("Not set")
                with streak_col2:
                    st.caption("Spend streak")
                    if spend_goal:
                        st.markdown(f":material/local_fire_department: **{calculate_streak('spend', spend_by_month)} months**")
                    else:
                        st.write("Not set")

        with col_merchants, st.container(border=True, key="card_dashboard_merchants"):
            st.subheader("Top Merchants")
            merchants_cutoff = render_time_filter("dashboard_merchants")
            merchants_spending = (
                spending[spending['DateParsed'] >= merchants_cutoff] if merchants_cutoff else spending
            )

            # Same Spend/Save split as the trend chart below - a merchant
            # you're paying into a savings pot isn't "spending" in the same
            # sense as a real purchase, so they read better as two separate
            # top-10 lists rather than one list where big pot transfers
            # crowd out real merchants.
            spend_only = merchants_spending[merchants_spending['Category'] != 'Savings & Investments']
            save_only = merchants_spending[merchants_spending['Category'] == 'Savings & Investments']

            def top_merchants_table(subset):
                totals = subset.groupby('Description').agg(
                    Category=('Category', 'first'),
                    Total=('Amount', 'sum'),
                    Transactions=('Amount', 'count')
                ).sort_values('Total', ascending=False).head(10).reset_index()
                totals.columns = ['Merchant', 'Category', 'Total', 'Transactions']
                totals['Total'] = totals['Total'].apply(lambda x: f"£{x:,.2f}")
                return totals

            st.markdown("**Top 10 Spend**")
            if spend_only.empty:
                st.write("No spending data for this period.")
            else:
                st.dataframe(top_merchants_table(spend_only), use_container_width=True, hide_index=True)

            st.markdown("**Top 10 Save**")
            if save_only.empty:
                st.write("No savings data for this period.")
            else:
                st.dataframe(top_merchants_table(save_only), use_container_width=True, hide_index=True)

        # --- Month by Month Trend ---
        with st.container(border=True, key="card_dashboard_trend"):
            st.subheader("Monthly Spending & Savings Trend")
            st.caption(
                "Money moving into savings/investment pots (SIPP, ISA, Emergency Fund, Wedding, "
                "etc.) is saved, not spent - it's shown as its own line rather than inflating "
                "Spending. The Savings line nets out withdrawals, so it can dip below zero in a "
                "month where more came out of a pot than went in. Fun Money is excluded entirely, "
                "since it behaves as a spending buffer rather than genuine savings."
            )
            trend_cutoff = render_time_filter("dashboard_trend")
            trend_spending = spending[spending['DateParsed'] >= trend_cutoff] if trend_cutoff else spending
            trend_transactions = (
                [t for t in all_transactions if datetime.strptime(t.date, '%d %b %Y') >= trend_cutoff]
                if trend_cutoff else all_transactions
            )

            # "Spending" excludes Savings & Investments entirely (that's the
            # whole point of the split) and stays gross/unmodified, matching
            # the Dashboard's other spending views. "Savings & Investments"
            # is recomputed for the selected time range (not reused from the
            # KPI row's savings_info, which always covers all data) via the
            # same netting logic as the Savings Rate KPI.
            spend_no_savings = trend_spending[trend_spending['Category'] != 'Savings & Investments']
            monthly_spend = spend_no_savings.groupby('Month')['Amount'].sum()
            savings_by_month = calculate_savings_rate(trend_transactions)['savings_by_month']

            months = sorted(set(monthly_spend.index) | set(savings_by_month.keys()), key=month_sort_key)

            if not months:
                st.write("No spending data for this period.")
            else:
                trend_df = pd.DataFrame({
                    'Month': months + months,
                    'Line': ['Spending'] * len(months) + ['Savings & Investments'] * len(months),
                    'Amount': [monthly_spend.get(m, 0.0) for m in months] + [savings_by_month.get(m, 0.0) for m in months],
                })

                fig_trend = px.line(
                    trend_df, x='Month', y='Amount', color='Line',
                    labels={'Amount': '', 'Month': ''},
                    color_discrete_map={'Spending': '#1D9E75', 'Savings & Investments': '#2a78d6'},
                    category_orders={'Month': months}
                )
                fig_trend.update_traces(line_width=2, hovertemplate='£%{y:,.0f}<extra></extra>')
                fig_trend.add_hline(y=0, line_width=1, line_color='rgba(128,128,128,0.4)')
                fig_trend.update_layout(
                    yaxis_tickprefix='£',
                    yaxis_tickformat=',.0f',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=10, b=0),
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, title=None)
                )
                st.plotly_chart(fig_trend, use_container_width=True)

# --- Upload Statement Page ---
elif page == "Upload Statement":
    st.header(":material/upload_file: Upload Statement")

    from household_transactions import save_household_transactions
    from csv_import import parse_bank_csv, decode_csv_bytes, CHASE, SANTANDER

    col_personal, col_household = st.columns(2)

    with col_personal, st.container(border=True, key="card_upload_personal"):
        st.subheader("Personal")
        st.caption("Feeds the Dashboard, Personal Budget, and Chat.")

        uploaded_file = st.file_uploader(
            "Upload your Chase transactions CSV export", type="csv", key="upload_personal_csv"
        )

        if uploaded_file is not None:
            content = decode_csv_bytes(uploaded_file.read())
            transactions = parse_bank_csv(content, CHASE)

            if transactions:
                st.success(f"Found {len(transactions)} transactions in this export")

                if st.button("Save to Budget Bot", key="save_personal_statement"):
                    saved, skipped = save_transactions(transactions)
                    st.success(f"Saved {saved} new transactions. Skipped {skipped} duplicates.")
            else:
                st.warning(
                    "No transactions found. Make sure this is the CSV export from Chase's "
                    "\"Download statement\" feature, not a different file."
                )

    with col_household, st.container(border=True, key="card_upload_household"):
        st.subheader("Household")
        st.caption(
            "Kept in a completely separate table - never included in the Dashboard, Personal "
            "Budget, or Chat. Only feeds the Household Budget page's Recurring Charges."
        )

        household_csv = st.file_uploader(
            "Upload your Santander transactions CSV export", type="csv", key="upload_household_csv"
        )

        if household_csv is not None:
            household_content = decode_csv_bytes(household_csv.read())
            parsed_household_transactions = parse_bank_csv(household_content, SANTANDER)

            if parsed_household_transactions:
                st.success(f"Found {len(parsed_household_transactions)} transactions in this export")

                if st.button("Save to Household Budget", key="save_household_statement"):
                    saved, skipped = save_household_transactions(parsed_household_transactions)
                    st.success(f"Saved {saved} new transactions. Skipped {skipped} duplicates.")
            else:
                st.warning(
                    "No transactions found. Make sure this is the CSV export from Santander's "
                    "\"midata\" transactions download, not a different file."
                )

    from household_transactions import get_household_months
    from analytics import get_upload_checklist

    st.subheader("Statements Uploaded")
    st.caption(
        "Jan 2026 to the current month. A month never disappears once it appears here, even if "
        "it's still missing - so a gap stays visible for you to catch up on."
    )

    col_personal_checklist, col_household_checklist = st.columns(2)

    with col_personal_checklist, st.container(border=True, key="card_upload_checklist_personal"):
        st.markdown("**Personal**")
        personal_checklist = get_upload_checklist(get_months())
        for month_label, uploaded in personal_checklist:
            st.checkbox(month_label, value=uploaded, disabled=True, key=f"check_personal_{month_label}")

    with col_household_checklist, st.container(border=True, key="card_upload_checklist_household"):
        st.markdown("**Household**")
        household_checklist = get_upload_checklist(get_household_months())
        for month_label, uploaded in household_checklist:
            st.checkbox(month_label, value=uploaded, disabled=True, key=f"check_household_{month_label}")

# --- Net Worth Page ---
elif page == "Net Worth":
    st.header(":material/trending_up: Net Worth")

    from networth import (
        get_all_asset_history, get_asset_names, import_from_worthit,
        update_asset_value, delete_asset,
        get_total_net_worth_series, get_per_asset_series, project_net_worth
    )
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd

    PROJECTION_YEARS = 5
    from datetime import datetime, timedelta

    if 'nw_selected_asset' not in st.session_state:
        st.session_state.nw_selected_asset = None

    # Import button
    with st.expander("Import from Worth It"):
        uploaded_worth = st.file_uploader("Upload Worth It export (.xlsx)", type="xlsx", key="worthit")
        if uploaded_worth:
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(uploaded_worth.read())
                tmp_path = tmp.name
            imported, skipped = import_from_worthit(tmp_path)
            os.unlink(tmp_path)
            st.success(f"Imported {imported} data points. Skipped archived: {', '.join(skipped) if skipped else 'none'}")

    records = get_all_asset_history()

    if st.session_state.nw_selected_asset:
        # --- Single asset detail view ---
        asset = st.session_state.nw_selected_asset

        if st.button("← Back to Net Worth", key="nw_back_btn"):
            st.session_state.nw_selected_asset = None
            st.rerun()

        asset_df = pd.DataFrame([{
            'Date': r.recorded_at,
            'Value': r.value
        } for r in records if r.asset_name == asset]).sort_values('Date')

        # True latest value, independent of the time filter below - used as the
        # starting point when recording a new value for this asset
        true_latest_val = asset_df.iloc[-1]['Value'] if not asset_df.empty else 0

        # --- Time filter ---
        col1, col2, col3, col4, col5 = st.columns(5)
        now = datetime.utcnow()
        filters = {
            'All': None,
            '1 Year': now - timedelta(days=365),
            'YTD': datetime(now.year, 1, 1),
            '6 Months': now - timedelta(days=182),
            '1 Month': now - timedelta(days=30)
        }

        if 'nw_asset_filter' not in st.session_state:
            st.session_state.nw_asset_filter = 'All'

        for col, label in zip([col1, col2, col3, col4, col5], filters.keys()):
            with col:
                if st.button(label, key=f"asset_filter_{label}"):
                    st.session_state.nw_asset_filter = label

        selected_filter = st.session_state.nw_asset_filter
        cutoff = filters[selected_filter]
        if cutoff:
            asset_df = asset_df[asset_df['Date'] >= cutoff]

        st.caption(f"Showing: {selected_filter}")

        with st.container(border=True, key="card_nw_asset_detail"):
            st.subheader(asset)

            latest_val = asset_df.iloc[-1]['Value'] if not asset_df.empty else 0
            first_val = asset_df.iloc[0]['Value'] if not asset_df.empty else 0
            pct_change = ((latest_val - first_val) / first_val * 100) if first_val else 0

            with st.container(key="nw_asset_metric"):
                st.metric(
                    "Current Value",
                    f"£{latest_val:,.0f}",
                    delta=f"{pct_change:+.1f}% ({selected_filter})"
                )

            fig = px.line(asset_df, x='Date', y='Value')
            fig.update_traces(line_color='#378ADD', line_width=2)
            fig.update_layout(
                yaxis_tickprefix='£',
                yaxis_tickformat=',.0f',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0)
            )
            fig.update_xaxes(title='')
            fig.update_yaxes(title='')
            st.plotly_chart(fig, use_container_width=True)

        with st.container(border=True, key="card_nw_asset_history"):
            st.subheader("All Updates")

            history_df = asset_df.sort_values('Date', ascending=False).copy()
            history_df['Date'] = history_df['Date'].dt.strftime('%d %b %Y, %H:%M')
            history_df['Value'] = history_df['Value'].apply(lambda v: f"£{v:,.2f}")
            history_df.columns = ['Recorded', 'Value']
            st.dataframe(history_df, use_container_width=True, hide_index=True)

        with st.expander("Update or Remove This Asset"):
            st.markdown("**Record a new value**")
            update_cols = st.columns([3, 1])
            with update_cols[0]:
                new_value = st.number_input(
                    "New value (£)", min_value=0.0, step=100.0,
                    value=float(true_latest_val), key="nw_asset_update_value"
                )
            with update_cols[1]:
                st.write("")
                st.write("")
                if st.button("Save", key="nw_asset_update_btn", use_container_width=True):
                    update_asset_value(asset, new_value)
                    st.success("Value recorded")
                    st.rerun()

            st.divider()

            st.markdown("**Remove this asset entirely**")
            st.caption("Deletes all recorded history for this asset - use this once it's been closed or moved elsewhere")
            confirm_delete = st.checkbox(
                "I'm sure I want to delete all history for this asset",
                key="nw_asset_delete_confirm"
            )
            if st.button("Delete Asset", key="nw_asset_delete_btn", disabled=not confirm_delete):
                delete_asset(asset)
                st.session_state.nw_selected_asset = None
                st.success(f"Deleted {asset}")
                st.rerun()

    else:
        if records:
            df = pd.DataFrame([{
                'Date': r.recorded_at,
                'Asset': r.asset_name,
                'Tag': r.tag,
                'Value': r.value
            } for r in records])

            # --- Time filter ---
            col1, col2, col3, col4, col5 = st.columns(5)
            now = datetime.utcnow()
            filters = {
                'All': None,
                '1 Year': now - timedelta(days=365),
                'YTD': datetime(now.year, 1, 1),
                '6 Months': now - timedelta(days=182),
                '1 Month': now - timedelta(days=30)
            }

            if 'nw_filter' not in st.session_state:
                st.session_state.nw_filter = 'All'

            for col, label in zip([col1, col2, col3, col4, col5], filters.keys()):
                with col:
                    if st.button(label, key=f"filter_{label}"):
                        st.session_state.nw_filter = label

            selected_filter = st.session_state.nw_filter
            cutoff = filters[selected_filter]
            if cutoff:
                df = df[df['Date'] >= cutoff]

            st.caption(f"Showing: {selected_filter}")

            # --- Total net worth ---
            with st.container(border=True, key="card_nw_total"):
                # Full, unfiltered daily total (forward-filled) computed once in
                # networth.py; the selected time filter is applied to this result,
                # not to the raw records, so an asset that wasn't updated inside the
                # filter window still counts using its last known value.
                full_daily_total = get_total_net_worth_series()
                daily_total = (
                    full_daily_total[full_daily_total['Date'] >= cutoff.date()]
                    if cutoff else full_daily_total
                )

                # Current total and its change over the selected filter period
                latest_total = daily_total.iloc[-1]['Total'] if not daily_total.empty else 0
                first_total = daily_total.iloc[0]['Total'] if not daily_total.empty else 0
                pct_change = ((latest_total - first_total) / first_total * 100) if first_total else 0

                with st.container(key="nw_total_metric"):
                    st.metric(
                        "Current Total Assets",
                        f"£{latest_total:,.0f}",
                        delta=f"{pct_change:+.1f}% ({selected_filter})"
                    )

                st.subheader("Total Assets Over Time")

                show_per_asset = st.checkbox("Show per-asset breakdown", key="nw_show_per_asset")

                fig_total = px.line(
                    daily_total, x='Date', y='Total',
                    labels={'Total': 'Total Assets (£)', 'Date': ''},
                )
                fig_total.update_traces(line_color='#1D9E75', line_width=2, name='Total', showlegend=show_per_asset)

                if show_per_asset:
                    # Same forward-filled daily pivot the Total line is summed
                    # from, just not summed - one column per asset. Filtered by
                    # the same time-range cutoff as daily_total above, for
                    # consistency with the rest of this chart.
                    full_per_asset = get_per_asset_series()
                    per_asset = (
                        full_per_asset[full_per_asset['Date'] >= cutoff.date()]
                        if cutoff else full_per_asset
                    )
                    asset_columns = [c for c in per_asset.columns if c != 'Date']

                    # Validated categorical palette (fixed hue order, same one
                    # used by the Dashboard's category pie chart) - colors follow
                    # the asset's name alphabetically, not its current rank, so a
                    # given asset keeps the same color across every time filter.
                    # More than 8 assets folds the smallest into "Other" (muted
                    # gray) rather than generating a 9th hue.
                    palette = ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#eb6834', '#4a3aa7', '#e34948']
                    if len(asset_columns) > len(palette):
                        latest = per_asset[asset_columns].iloc[-1].sort_values(ascending=False)
                        top_assets = sorted(latest.index[:len(palette)].tolist())
                        other_assets = [a for a in asset_columns if a not in top_assets]
                        per_asset = per_asset.copy()
                        per_asset['Other'] = per_asset[other_assets].sum(axis=1)
                        asset_columns = top_assets + ['Other']

                    color_map = {name: palette[i] for i, name in enumerate(sorted(a for a in asset_columns if a != 'Other'))}
                    color_map['Other'] = '#898781'

                    for name in asset_columns:
                        fig_total.add_trace(go.Scatter(
                            x=per_asset['Date'], y=per_asset[name],
                            mode='lines', name=name,
                            line=dict(color=color_map[name], width=1.5),
                        ))

                fig_total.update_layout(
                    yaxis_tickprefix='£',
                    yaxis_tickformat=',.0f',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, title=None)
                )

                st.plotly_chart(fig_total, use_container_width=True)

            # --- Net worth projection ---
            # Deliberately a separate chart/card from Total Assets Over Time above,
            # not an overlay on it - the projection is anchored on the TRUE latest
            # total from full history (via project_net_worth) and always runs
            # PROJECTION_YEARS forward regardless of the time filter selected above,
            # so sharing one linear axis with a filtered actual-history line (e.g.
            # "1 Month") squashed the actual line flat. Kept in its own card, on its
            # own axis, so neither view distorts the other.
            with st.container(border=True, key="card_nw_projection"):
                st.subheader("Net Worth Projection")

                full_daily_total = get_total_net_worth_series()
                projection = project_net_worth(years=PROJECTION_YEARS)

                if projection['ok']:
                    fig_proj = px.line(
                        full_daily_total, x='Date', y='Total',
                        labels={'Total': 'Total Assets (£)', 'Date': ''},
                    )
                    fig_proj.update_traces(line_color='#1D9E75', line_width=2, name='Actual', showlegend=True)
                    fig_proj.update_layout(
                        yaxis_tickprefix='£',
                        yaxis_tickformat=',.0f',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=0, b=0)
                    )

                    anchor_ts = pd.Timestamp(projection['anchor_date'])
                    rate = projection['rate']
                    future_dates = [anchor_ts + pd.DateOffset(years=yr) for yr in range(PROJECTION_YEARS + 1)]
                    future_values = [projection['anchor_value'] * (1 + rate) ** yr for yr in range(PROJECTION_YEARS + 1)]

                    fig_proj.add_trace(go.Scatter(
                        x=future_dates, y=future_values,
                        mode='lines',
                        line=dict(color='#1D9E75', width=2, dash='dash'),
                        opacity=0.5,
                        name=f'Projected ({rate*100:.1f}%/yr)'
                    ))

                    st.plotly_chart(fig_proj, use_container_width=True)

                    st.caption(
                        f"Dashed line: a rough {PROJECTION_YEARS}-year projection based on your full asset "
                        f"history, assuming your historical blended growth rate of {projection['rate']*100:.1f}%/year "
                        f"continues. This rate reflects both market performance and your own contributions over "
                        f"time - it is not a pure investment return, and it is not a guarantee of future results."
                    )
                else:
                    st.caption("Not enough net worth history yet to show a projection.")

            # --- Asset list ---
            with st.container(border=True, key="card_nw_assetlist"):
                st.subheader("Assets")
                st.caption("Click an asset to see its full history")

                asset_summary = df.sort_values('Date').groupby('Asset').agg(
                    Value=('Value', 'last'),
                    First=('Value', 'first'),
                    Tag=('Tag', 'last')
                ).reset_index().sort_values('Value', ascending=False)

                header = st.columns([4, 2, 2, 2])
                header[0].caption("ASSET")
                header[1].caption("CATEGORY")
                header[2].caption("VALUE")
                header[3].caption(f"GROWTH ({selected_filter})")

                for _, row in asset_summary.iterrows():
                    cols = st.columns([4, 2, 2, 2])
                    with cols[0]:
                        if st.button(row['Asset'], key=f"nw_asset_{row['Asset']}", use_container_width=True):
                            st.session_state.nw_selected_asset = row['Asset']
                            st.rerun()
                    with cols[1]:
                        st.write(row['Tag'])
                    with cols[2]:
                        st.write(f"£{row['Value']:,.0f}")
                    with cols[3]:
                        # Growth over the same selected time-range filter as the
                        # "Current Total Assets" delta above - the first and last
                        # recorded value for this asset within that window.
                        pct = ((row['Value'] - row['First']) / row['First'] * 100) if row['First'] else 0
                        if pct > 0:
                            st.markdown(f":green[+{pct:.1f}%]")
                        elif pct < 0:
                            st.markdown(f":red[{pct:.1f}%]")
                        else:
                            st.markdown(":gray[0.0%]")
        else:
            st.info("No net worth data yet - add your first asset below, or import a Worth It export above.")

        # Add or remove an asset - always reachable even before any data
        # exists, so a new user isn't stuck needing a Worth It export just
        # to get their first asset in
        with st.expander("Add or Remove an Asset", expanded=not records):
            st.markdown("**Add a new asset**")
            add_cols = st.columns([3, 2, 2, 1])
            with add_cols[0]:
                new_asset_name = st.text_input("Name", key="nw_new_asset_name", placeholder="e.g. Trading 212 ISA")
            with add_cols[1]:
                new_asset_tag = st.text_input("Category", key="nw_new_asset_tag", placeholder="e.g. Savings")
            with add_cols[2]:
                new_asset_value = st.number_input("Value (£)", key="nw_new_asset_value", min_value=0.0, step=100.0)
            with add_cols[3]:
                st.write("")
                st.write("")
                if st.button("Add", key="nw_add_asset_btn", use_container_width=True):
                    if new_asset_name.strip():
                        update_asset_value(new_asset_name.strip(), new_asset_value, new_asset_tag.strip() or 'Other')
                        st.success(f"Added {new_asset_name}")
                        st.rerun()
                    else:
                        st.warning("Enter an asset name")

            st.divider()

            st.markdown("**Remove an asset**")
            existing_asset_names = get_asset_names()
            if existing_asset_names:
                remove_cols = st.columns([4, 1])
                with remove_cols[0]:
                    asset_to_remove = st.selectbox("Asset", existing_asset_names, key="nw_remove_asset_select")
                with remove_cols[1]:
                    st.write("")
                    st.write("")
                    if st.button("Remove", key="nw_remove_asset_btn", use_container_width=True):
                        delete_asset(asset_to_remove)
                        st.success(f"Removed {asset_to_remove}")
                        st.rerun()
            else:
                st.caption("No assets yet")

# --- Personal Budget Page ---
elif page == "Personal Budget":
    st.header(":material/account_balance_wallet: Personal Budget")

    from budget import (
        get_personal_items, replace_personal_section, get_personal_total_expenses,
        get_personal_total_income, set_personal_total_income
    )

    total_income = get_personal_total_income()

    with st.container(border=True, key="card_personal_summary"):
        st.subheader("Overview")
        total_expenses = get_personal_total_expenses()
        income_minus_expenses = total_income - total_expenses
        money_per_week = income_minus_expenses / 4

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total expenses", f"£{total_expenses:,.2f}")
        with col2:
            st.metric("Income minus expenses", f"£{income_minus_expenses:,.2f}")
        with col3:
            st.metric("Money per week", f"£{money_per_week:,.2f}")
        with col4:
            from analytics import calculate_avg_monthly_spend
            from database import load_all_transactions
            actual_spend = calculate_avg_monthly_spend(load_all_transactions())
            gap = actual_spend - total_expenses
            st.metric(
                "Actual monthly spend (recent avg)",
                f"£{actual_spend:,.2f}",
                delta=f"£{gap:,.2f} vs budget",
                delta_color="inverse",
                help="Real average monthly outflow from your transactions, excluding Savings & "
                     "Investments. If this is higher than Total expenses, something you're "
                     "actually paying for isn't reflected in the Money Out list below - see "
                     "Recurring Charges."
            )

    with st.container(border=True, key="card_personal_money_in"):
        st.subheader("Money In")
        st.caption("Reference only - not summed into any total")
        money_in_df = pd.DataFrame(get_personal_items('Money In'))
        if money_in_df.empty:
            money_in_df = pd.DataFrame(columns=['name', 'amount'])
        edited_money_in = st.data_editor(
            money_in_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Name", required=True),
                "amount": st.column_config.NumberColumn("Amount (£)", min_value=0.0, step=1.0, required=True),
            },
            key="personal_money_in_editor"
        )
        if st.button("Save Money In", key="save_personal_money_in"):
            clean_items = edited_money_in.dropna(subset=['name', 'amount']).to_dict('records')
            replace_personal_section('Money In', clean_items)
            st.success("Money In saved")
            st.rerun()

    with st.container(border=True, key="card_personal_income"):
        new_total_income = st.number_input(
            "Total income (Minus sacrifice) (£)", min_value=0.0, step=1.0,
            value=total_income, key="personal_total_income_input"
        )
        if st.button("Save Total Income", key="save_total_income"):
            set_personal_total_income(new_total_income)
            st.success("Saved")
            st.rerun()

    with st.container(border=True, key="card_personal_money_out"):
        st.subheader("Money Out")
        money_out_df = pd.DataFrame(get_personal_items('Money Out'))
        if money_out_df.empty:
            money_out_df = pd.DataFrame(columns=['name', 'amount'])
        edited_money_out = st.data_editor(
            money_out_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Name", required=True),
                "amount": st.column_config.NumberColumn("Amount (£)", min_value=0.0, step=1.0, required=True),
            },
            key="personal_money_out_editor"
        )
        if st.button("Save Money Out", key="save_personal_money_out"):
            clean_items = edited_money_out.dropna(subset=['name', 'amount']).to_dict('records')
            replace_personal_section('Money Out', clean_items)
            st.success("Money Out saved")
            st.rerun()

    with st.container(border=True, key="card_personal_recurring"):
        st.subheader("Recurring Charges (last 3 months)")
        st.caption(
            "Merchants you've paid at least twice in the last 3 months, with their average "
            "amount. This isn't matched against your Money Out list above - compare it yourself. "
            "\"Add to budget\" adds it and marks it reviewed; \"Already in budget\" / \"Not "
            "recurring\" just mark it reviewed. Reviewed items move below for 6 months, then "
            "resurface automatically - nothing gets permanently hidden."
        )

        from analytics import get_recurring_charges
        from database import load_all_transactions
        from categoriser import CATEGORIES
        from budget import get_active_dismissals, dismiss_recurring_charge, undismiss_recurring_charge

        all_recurring = get_recurring_charges(load_all_transactions())
        dismissals = get_active_dismissals()

        recurring_cat_filter = st.selectbox(
            "Filter by category", ["All categories"] + CATEGORIES, key="recurring_category_filter"
        )
        if recurring_cat_filter != "All categories":
            all_recurring = [r for r in all_recurring if r['category'] == recurring_cat_filter]

        to_review = [r for r in all_recurring if r['merchant'] not in dismissals]
        reviewed = [r for r in all_recurring if r['merchant'] in dismissals]

        if not to_review:
            st.write("Nothing to review for this filter.")
        else:
            header = st.columns([2.6, 1.6, 0.9, 1.1, 1.1, 1.6, 1.6])
            for col, label in zip(header, ["**Merchant**", "**Category**", "**Months**", "**Avg**", "", "", ""]):
                col.markdown(label)

            for r in to_review:
                row = st.columns([2.6, 1.6, 0.9, 1.1, 1.1, 1.6, 1.6])
                row[0].write(r['merchant'])
                row[1].write(r['category'])
                row[2].write(f"{r['months_seen']}/3")
                row[3].write(f"£{r['avg_amount']:,.2f}")
                if row[4].button("Add", key=f"add_{r['merchant']}", help="Add to Money Out below"):
                    current_items = get_personal_items('Money Out')
                    current_items.append({'name': r['merchant'], 'amount': round(r['avg_amount'], 2)})
                    replace_personal_section('Money Out', current_items)
                    dismiss_recurring_charge(r['merchant'], 'already_budgeted')
                    st.success(f"Added '{r['merchant']}' to Money Out")
                    st.rerun()
                if row[5].button(
                    "In budget", key=f"inbudget_{r['merchant']}",
                    help="Already covered by an existing (differently named) Money Out row"
                ):
                    dismiss_recurring_charge(r['merchant'], 'already_budgeted')
                    st.rerun()
                if row[6].button(
                    "Not recurring", key=f"notrec_{r['merchant']}",
                    help="Not really a regular bill or subscription"
                ):
                    dismiss_recurring_charge(r['merchant'], 'not_recurring')
                    st.rerun()

        if reviewed:
            with st.expander(f"Reviewed ({len(reviewed)}) - resurfaces automatically after 6 months"):
                for r in reviewed:
                    info = dismissals[r['merchant']]
                    reason_label = "Already in budget" if info['reason'] == 'already_budgeted' else "Not recurring"
                    dismissed_date = info['dismissed_at'].strftime('%d %b %Y')
                    rcol = st.columns([2.6, 1.6, 1.1, 2, 1.6])
                    rcol[0].write(r['merchant'])
                    rcol[1].write(r['category'])
                    rcol[2].write(f"£{r['avg_amount']:,.2f}")
                    rcol[3].write(f"{reason_label} · {dismissed_date}")
                    if rcol[4].button("Un-dismiss", key=f"undismiss_{r['merchant']}"):
                        undismiss_recurring_charge(r['merchant'])
                        st.rerun()

# --- Household Budget Page ---
elif page == "Household Budget":
    st.header(":material/home: Household Budget")

    from budget import (
        get_household_items, replace_household_items, get_household_total,
        get_household_split_percent, set_household_split_percent,
        get_household_person1_name, set_household_person1_name,
        get_household_person2_name, set_household_person2_name
    )

    with st.container(border=True, key="card_household_bills"):
        st.subheader("Household Bills")
        household_df = pd.DataFrame(get_household_items())
        if household_df.empty:
            household_df = pd.DataFrame(columns=['service', 'provider', 'renewal_date', 'amount'])
        edited_household = st.data_editor(
            household_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "service": st.column_config.TextColumn("Service", required=True),
                "provider": st.column_config.TextColumn("Provider"),
                "renewal_date": st.column_config.TextColumn("Renewal / end date"),
                "amount": st.column_config.NumberColumn("New House", min_value=0.0, step=1.0, required=True),
            },
            key="household_editor"
        )
        if st.button("Save Household Bills", key="save_household_bills"):
            clean_df = edited_household.dropna(subset=['service', 'amount']).copy()
            clean_df['provider'] = clean_df['provider'].fillna('')
            clean_df['renewal_date'] = clean_df['renewal_date'].fillna('')
            replace_household_items(clean_df.to_dict('records'))
            st.success("Household bills saved")
            st.rerun()

        total = get_household_total()
        st.metric("Total", f"£{total:,.2f}")

    with st.container(border=True, key="card_household_split"):
        st.subheader("Split")

        name_col1, name_col2 = st.columns(2)
        with name_col1:
            person1_name = st.text_input(
                "Person 1 name", value=get_household_person1_name(), key="household_person1_name_input"
            )
        with name_col2:
            person2_name = st.text_input(
                "Person 2 name", value=get_household_person2_name(), key="household_person2_name_input"
            )

        split_pct = st.number_input(
            f"{person1_name}'s share (%)", min_value=0.0, max_value=100.0, step=1.0,
            value=get_household_split_percent(), key="household_split_input"
        )
        if st.button("Save Split", key="save_split_pct"):
            set_household_person1_name(person1_name)
            set_household_person2_name(person2_name)
            set_household_split_percent(split_pct)
            st.success("Saved")
            st.rerun()

        person1_share = total * (split_pct / 100)
        person2_share = total * (1 - split_pct / 100)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(person1_name, f"£{person1_share:,.2f}")
        with col2:
            st.metric(person2_name, f"£{person2_share:,.2f}")

    from household_transactions import (
        load_all_household_transactions, get_household_transactions_db, HouseholdTransaction,
        get_household_active_dismissals, dismiss_household_recurring_charge,
        undismiss_household_recurring_charge
    )
    from analytics import calculate_avg_monthly_spend, get_recurring_charges
    from categoriser import CATEGORIES

    with st.container(border=True, key="card_household_categorise"):
        st.caption("Upload Santander statements on the Upload Statement page.")
        if st.button("Categorise uncategorised household transactions", key="categorise_household"):
            with st.spinner("Categorising..."):
                hdb = get_household_transactions_db()
                rules, ai = categorise_all(hdb, HouseholdTransaction)
                hdb.close()
                st.success(f"Done. {rules} categorised by rules, {ai} by Ollama")

    household_transactions_data = load_all_household_transactions()

    if household_transactions_data:
        with st.container(border=True, key="card_household_actual_spend"):
            actual_spend = calculate_avg_monthly_spend(household_transactions_data)
            gap = actual_spend - total
            st.metric(
                "Actual monthly spend (recent avg)",
                f"£{actual_spend:,.2f}",
                delta=f"£{gap:,.2f} vs budgeted Total",
                delta_color="inverse",
                help="Real average monthly outflow from uploaded Santander transactions. If "
                     "higher than the budgeted Total above, something you're actually being "
                     "charged for isn't reflected in the Household Bills list - see Recurring "
                     "Charges below."
            )

        with st.container(border=True, key="card_household_recurring"):
            st.subheader("Recurring Charges (last 3 months)")
            st.caption(
                "Merchants charged at least twice in the last 3 months of Santander transactions, "
                "with their average amount. Not matched against the Household Bills list above - "
                "compare it yourself. \"Add to budget\" adds it and marks it reviewed; \"Already "
                "in budget\" / \"Not recurring\" just mark it reviewed. Reviewed items move below "
                "for 6 months, then resurface automatically."
            )

            all_household_recurring = get_recurring_charges(household_transactions_data)
            household_dismissals = get_household_active_dismissals()

            household_cat_filter = st.selectbox(
                "Filter by category", ["All categories"] + CATEGORIES, key="household_recurring_category_filter"
            )
            if household_cat_filter != "All categories":
                all_household_recurring = [r for r in all_household_recurring if r['category'] == household_cat_filter]

            household_to_review = [r for r in all_household_recurring if r['merchant'] not in household_dismissals]
            household_reviewed = [r for r in all_household_recurring if r['merchant'] in household_dismissals]

            if not household_to_review:
                st.write("Nothing to review for this filter.")
            else:
                header = st.columns([2.6, 1.6, 0.9, 1.1, 1.1, 1.6, 1.6])
                for col, label in zip(header, ["**Merchant**", "**Category**", "**Months**", "**Avg**", "", "", ""]):
                    col.markdown(label)

                for r in household_to_review:
                    row = st.columns([2.6, 1.6, 0.9, 1.1, 1.1, 1.6, 1.6])
                    row[0].write(r['merchant'])
                    row[1].write(r['category'])
                    row[2].write(f"{r['months_seen']}/3")
                    row[3].write(f"£{r['avg_amount']:,.2f}")
                    if row[4].button("Add", key=f"hh_add_{r['merchant']}", help="Add to Household Bills above"):
                        current_items = get_household_items()
                        current_items.append({
                            'service': r['merchant'], 'provider': '', 'renewal_date': '',
                            'amount': round(r['avg_amount'], 2)
                        })
                        replace_household_items(current_items)
                        dismiss_household_recurring_charge(r['merchant'], 'already_budgeted')
                        st.success(f"Added '{r['merchant']}' to Household Bills")
                        st.rerun()
                    if row[5].button(
                        "In budget", key=f"hh_inbudget_{r['merchant']}",
                        help="Already covered by an existing (differently named) Household Bills row"
                    ):
                        dismiss_household_recurring_charge(r['merchant'], 'already_budgeted')
                        st.rerun()
                    if row[6].button(
                        "Not recurring", key=f"hh_notrec_{r['merchant']}",
                        help="Not really a regular bill or subscription"
                    ):
                        dismiss_household_recurring_charge(r['merchant'], 'not_recurring')
                        st.rerun()

            if household_reviewed:
                with st.expander(f"Reviewed ({len(household_reviewed)}) - resurfaces automatically after 6 months"):
                    for r in household_reviewed:
                        info = household_dismissals[r['merchant']]
                        reason_label = "Already in budget" if info['reason'] == 'already_budgeted' else "Not recurring"
                        dismissed_date = info['dismissed_at'].strftime('%d %b %Y')
                        rcol = st.columns([2.6, 1.6, 1.1, 2, 1.6])
                        rcol[0].write(r['merchant'])
                        rcol[1].write(r['category'])
                        rcol[2].write(f"£{r['avg_amount']:,.2f}")
                        rcol[3].write(f"{reason_label} · {dismissed_date}")
                        if rcol[4].button("Un-dismiss", key=f"hh_undismiss_{r['merchant']}"):
                            undismiss_household_recurring_charge(r['merchant'])
                            st.rerun()

# --- Goals Page ---
elif page == "Goals":
    st.header(":material/flag: Goals")
    st.caption(
        "Set a savings target and a spending ceiling for yourself. A new target always starts "
        "next month, never the one you're currently in - so there's no way to loosen a target "
        "you're about to miss. Changing a target also resets its streak back to zero, even if "
        "it's a change that only takes effect next month."
    )

    from datetime import datetime
    from goals import (
        get_current_goal, get_all_goals, set_goal, next_effective_month,
        calculate_streak, get_discretionary_monthly_spend, NON_DISCRETIONARY_CATEGORIES
    )
    from analytics import calculate_savings_rate, month_sort_key, format_gbp

    all_transactions = load_all_transactions()
    current_month_label = datetime.now().strftime('%b %Y')
    next_month = next_effective_month()

    savings_rates = calculate_savings_rate(all_transactions)
    savings_by_month_all = savings_rates['savings_by_month']
    spend_by_month_all = get_discretionary_monthly_spend(all_transactions)

    # Complete months only - the current calendar month is still in progress,
    # so it's excluded from streak calculations (shown separately below as
    # "so far this month" instead, which doesn't count toward the streak).
    savings_by_month_complete = {m: v for m, v in savings_by_month_all.items() if m != current_month_label}
    spend_by_month_complete = {m: v for m, v in spend_by_month_all.items() if m != current_month_label}

    def last_n_avg(monthly_dict, n=3):
        recent_months = sorted(monthly_dict.keys(), key=month_sort_key, reverse=True)[:n]
        values = [monthly_dict[m] for m in recent_months]
        return sum(values) / len(values) if values else 0

    goal_col1, goal_col2 = st.columns(2)

    with goal_col1, st.container(border=True, key="card_goal_savings"):
        st.subheader(":material/savings: Savings Goal")

        savings_goal = get_current_goal('savings')
        savings_streak = calculate_streak('savings', savings_by_month_complete)
        savings_active_now = savings_goal is not None and month_sort_key(savings_goal.effective_month) <= month_sort_key(current_month_label)

        if savings_goal:
            status = "Active now" if savings_active_now else f"Starts {savings_goal.effective_month}"
            st.metric(f"Target ({status})", format_gbp(savings_goal.target_amount))
        else:
            st.write("No savings target set yet.")

        st.markdown(f":material/local_fire_department: **{savings_streak}-month streak**")

        if savings_active_now:
            so_far = savings_by_month_all.get(current_month_label, 0)
            st.caption(f"So far this month: {format_gbp(so_far)} (target: {format_gbp(savings_goal.target_amount)} or more)")

        with st.expander("Set a new target"):
            suggested_savings = last_n_avg(savings_by_month_complete)
            st.caption(f"Takes effect from **{next_month}**, not this month. Changing this resets your streak.")
            st.caption(f"Suggested, from your last 3 months' average: {format_gbp(suggested_savings)}")
            new_savings_target = st.number_input(
                "Monthly savings target (£)", min_value=0.0, step=50.0,
                value=float(max(0, round(suggested_savings))), key="goal_input_savings"
            )
            if st.button("Save savings target", key="goal_save_savings"):
                set_goal('savings', new_savings_target, next_month)
                st.success(f"Savings target of {format_gbp(new_savings_target)} set for {next_month}")
                st.rerun()

        savings_history = get_all_goals('savings')
        if savings_history:
            with st.expander("History"):
                hist_df = pd.DataFrame([{
                    'Effective': g.effective_month,
                    'Target': format_gbp(g.target_amount),
                    'Set on': g.created_at.strftime('%d %b %Y')
                } for g in reversed(savings_history)])
                st.dataframe(hist_df, use_container_width=True, hide_index=True)

    with goal_col2, st.container(border=True, key="card_goal_spend"):
        st.subheader(":material/payments: Discretionary Spend Ceiling")
        st.caption(
            "Excludes fixed costs you don't really have month-to-month control over: "
            + ", ".join(NON_DISCRETIONARY_CATEGORIES) + "."
        )

        spend_goal = get_current_goal('spend')
        spend_streak = calculate_streak('spend', spend_by_month_complete)
        spend_active_now = spend_goal is not None and month_sort_key(spend_goal.effective_month) <= month_sort_key(current_month_label)

        if spend_goal:
            status = "Active now" if spend_active_now else f"Starts {spend_goal.effective_month}"
            st.metric(f"Target ({status})", format_gbp(spend_goal.target_amount))
        else:
            st.write("No spend ceiling set yet.")

        st.markdown(f":material/local_fire_department: **{spend_streak}-month streak**")

        if spend_active_now:
            so_far = spend_by_month_all.get(current_month_label, 0)
            st.caption(f"So far this month: {format_gbp(so_far)} (target: {format_gbp(spend_goal.target_amount)} or under)")

        with st.expander("Set a new target"):
            suggested_spend = last_n_avg(spend_by_month_complete)
            st.caption(f"Takes effect from **{next_month}**, not this month. Changing this resets your streak.")
            st.caption(f"Suggested, from your last 3 months' average: {format_gbp(suggested_spend)}")
            new_spend_target = st.number_input(
                "Monthly discretionary spend ceiling (£)", min_value=0.0, step=50.0,
                value=float(max(0, round(suggested_spend))), key="goal_input_spend"
            )
            if st.button("Save spend ceiling", key="goal_save_spend"):
                set_goal('spend', new_spend_target, next_month)
                st.success(f"Discretionary spend ceiling of {format_gbp(new_spend_target)} set for {next_month}")
                st.rerun()

        spend_history = get_all_goals('spend')
        if spend_history:
            with st.expander("History"):
                hist_df = pd.DataFrame([{
                    'Effective': g.effective_month,
                    'Target': format_gbp(g.target_amount),
                    'Set on': g.created_at.strftime('%d %b %Y')
                } for g in reversed(spend_history)])
                st.dataframe(hist_df, use_container_width=True, hide_index=True)

# --- View Transactions Page ---
elif page == "View Transactions":
    st.header(":material/receipt_long: All Transactions")
    
    all_transactions = load_all_transactions()

    if all_transactions:
        from analytics import month_sort_key

        df = pd.DataFrame([{
            'Date': t.date,
            'Description': t.description,
            'Amount': t.amount,
            'Category': t.category,
            'Month': t.month
        } for t in all_transactions])

        with st.container(border=True, key="card_transactions_filters"):
            col1, col2, col3 = st.columns(3)
            with col1:
                months = sorted(df['Month'].unique().tolist(), key=month_sort_key)
                selected_month = st.selectbox("Filter by month", ["All months"] + months)
            with col2:
                merchants = sorted(df['Description'].unique().tolist())
                selected_merchant = st.selectbox("Filter by merchant", ["All merchants"] + merchants)
            with col3:
                categories = sorted(df['Category'].unique().tolist())
                selected_category = st.selectbox("Filter by category", ["All categories"] + categories)

        if selected_month != "All months":
            df = df[df['Month'] == selected_month]
        if selected_merchant != "All merchants":
            df = df[df['Description'] == selected_merchant]
        if selected_category != "All categories":
            df = df[df['Category'] == selected_category]

        with st.container(border=True, key="card_transactions_table"):
            st.dataframe(df, use_container_width=True)
            st.caption(f"Showing {len(df)} transactions")
    else:
        st.info("No transactions yet - upload a statement first")

# --- Manage Categories Page ---
elif page == "Manage Categories":
    st.header(":material/sell: Manage Categories")
    st.write("Review and correct how each merchant has been categorised.")

    from database import get_db, Transaction
    from categoriser import CATEGORIES, save_user_rule

    with st.container(border=True, key="card_manage_categorise_actions"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Categorise uncategorised"):
                with st.spinner("Categorising... this may take a minute"):
                    db = get_db()
                    rules, ai = categorise_all(db, Transaction)
                    db.close()
                    st.success(f"Done. {rules} categorised by rules, {ai} by Ollama")

        with col2:
            if st.button("Re-categorise everything"):
                with st.spinner("Re-categorising all 935 transactions... this may take a few minutes"):
                    db = get_db()
                    rules, ai = recategorise_all(db, Transaction)
                    db.close()
                    st.success(f"Done. {rules} categorised by rules, {ai} by Ollama")

    db = get_db()
    merchants = db.query(
        Transaction.description,
        Transaction.category
    ).distinct(Transaction.description).all()
    db.close()

    if not merchants:
        st.info("No transactions yet - upload a statement first")
    else:
        with st.container(border=True, key="card_manage_merchant_table"):
            merchant_df = pd.DataFrame([{
                'Merchant': m.description,
                'Category': m.category
            } for m in merchants]).sort_values('Merchant')

            st.caption(f"{len(merchant_df)} unique merchants")

            selected_cat = st.selectbox(
                "Filter by category",
                ["All categories"] + CATEGORIES,
                key="filter_category"
            )

            if selected_cat != "All categories":
                merchant_df = merchant_df[merchant_df['Category'] == selected_cat]

            st.dataframe(merchant_df, use_container_width=True)

        with st.container(border=True, key="card_manage_correct_category"):
            st.subheader("Correct a category")

            all_merchants = sorted([m.description for m in merchants])
            selected_merchant = st.selectbox("Select merchant to fix", all_merchants, key="select_merchant")
            new_category = st.selectbox("Assign correct category", CATEGORIES, key="new_category")
            st.caption("Also remembered for this merchant on future statement uploads.")

            if st.button("Update category"):
                db = get_db()
                transactions_to_update = db.query(Transaction).filter_by(
                    description=selected_merchant
                ).all()
                for t in transactions_to_update:
                    t.category = new_category
                db.commit()
                db.close()
                save_user_rule(selected_merchant, new_category)
                st.success(f"Updated all '{selected_merchant}' transactions to '{new_category}'")