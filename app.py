import streamlit as st
import fitz
import pandas as pd
import re
from database import save_transactions, load_all_transactions, get_months
from categoriser import categorise_all, recategorise_all
from database import get_db, Transaction

st.set_page_config(page_title="Budget Bot", layout="wide")
st.title("Budget Bot")

# Shared styling: every card container uses key="card_<page>_<section>" so
# this one rule can style them all at once, without touching background/text
# colors (those come from primaryColor + Streamlit's native light/dark
# resolution, set in .streamlit/config.toml, so the built-in theme toggle
# keeps working). Also carries the enlarged-metric rule previously
# duplicated per-page on Net Worth.
st.markdown(
    """
    <style>
    div[class*="st-key-card_"] {
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    @media (prefers-color-scheme: dark) {
        div[class*="st-key-card_"] {
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
        }
    }
    .st-key-nw_asset_metric [data-testid="stMetricValue"],
    .st-key-nw_total_metric [data-testid="stMetricValue"] {
        font-size: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def is_date(text):
    return bool(re.match(r'\d{2} \w{3} \d{4}', text))

def is_amount(text):
    return bool(re.match(r'-?£[\d,]+\.\d{2}', text))

def is_balance(text):
    return bool(re.match(r'£[\d,]+\.\d{2}', text))

def parse_transactions(lines):
    transactions = []
    i = 0
    
    while i < len(lines) and lines[i] != 'Balance':
        i += 1
    i += 1

    while i < len(lines):
        if is_date(lines[i]):
            date = lines[i]
            i += 1
            
            if i < len(lines):
                description = lines[i]
                i += 1
            
            while i < len(lines) and not is_amount(lines[i]) and not is_date(lines[i]):
                i += 1
            
            if i < len(lines) and is_amount(lines[i]):
                amount = lines[i]
                i += 1
                
                if i < len(lines) and is_balance(lines[i]):
                    i += 1
                
                if description not in ['Opening balance', 'Closing balance']:
                    transactions.append({
                        'Date': date,
                        'Description': description,
                        'Amount': amount
                    })
        else:
            i += 1
    
    return transactions

# --- Sidebar ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Net Worth", "Personal Budget", "Household Budget", "Upload Statement", "View Transactions", "Manage Categories"])

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
    st.header("Dashboard")

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

        # Separate money out (negative) from money in (positive)
        spending = df[df['Amount'] < 0].copy()
        spending['Amount'] = spending['Amount'].abs()

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

            with col2:
                st.metric("Total Spent (6 months)", f"£{spending['Amount'].sum():,.2f}")

            with col3:
                st.metric("Monthly Average", f"£{spending['Amount'].sum() / 6:,.2f}")

            with col4:
                savings_info = calculate_savings_rate(all_transactions)
                if savings_info['typical_monthly_income']:
                    st.metric(
                        "Savings Rate",
                        f"{format_gbp(savings_info['avg_savings'], decimals=0)}/mo",
                        delta=f"{savings_info['savings_rate']:.0f}% of salary"
                    )
                else:
                    st.metric("Savings Rate", "N/A")

        # --- Category pie + Top merchants ---
        col_pie, col_merchants = st.columns(2)

        with col_pie, st.container(border=True, key="card_dashboard_pie"):
            st.subheader("Spending by Category")
            category_totals = spending.groupby('Category')['Amount'].sum().sort_values(ascending=False)

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

        with col_merchants, st.container(border=True, key="card_dashboard_merchants"):
            st.subheader("Top 10 Merchants")
            merchant_totals = spending.groupby('Description').agg(
                Category=('Category', 'first'),
                Total=('Amount', 'sum'),
                Transactions=('Amount', 'count')
            ).sort_values('Total', ascending=False).head(10).reset_index()
            merchant_totals.columns = ['Merchant', 'Category', 'Total', 'Transactions']
            merchant_totals['Total'] = merchant_totals['Total'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(merchant_totals, use_container_width=True, hide_index=True)

        # --- Month by Month Trend ---
        with st.container(border=True, key="card_dashboard_trend"):
            st.subheader("Monthly Spending & Savings Trend")
            st.caption(
                "Money moving into savings/investment pots (SIPP, ISA, Fun Money, etc.) is saved, "
                "not spent - it's shown as its own line rather than inflating Spending. The Savings "
                "line nets out withdrawals, so it can dip below zero in a month where more came out "
                "of a pot than went in."
            )

            # "Spending" excludes Savings & Investments entirely (that's the
            # whole point of the split) and stays gross/unmodified, matching
            # the Dashboard's other spending views. "Savings & Investments"
            # reuses the same netted-by-month figures as the Savings Rate KPI
            # (savings_info, computed above) rather than recalculating them.
            spend_no_savings = spending[spending['Category'] != 'Savings & Investments']
            monthly_spend = spend_no_savings.groupby('Month')['Amount'].sum()
            savings_by_month = savings_info['savings_by_month']

            months = sorted(set(monthly_spend.index) | set(savings_by_month.keys()), key=month_sort_key)
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
    st.header("Upload Statement")

    with st.container(border=True, key="card_upload_statement"):
        st.write("Upload a bank statement PDF to add it to Budget Bot.")

        uploaded_file = st.file_uploader("Upload your bank statement", type="pdf")

        if uploaded_file is not None:
            pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")

            lines = []
            for page_num in pdf:
                for line in page_num.get_text().split('\n'):
                    line = line.strip()
                    if line:
                        lines.append(line)

            transactions = parse_transactions(lines)

            if transactions:
                st.success(f"Found {len(transactions)} transactions in this statement")

                if st.button("Save to Budget Bot"):
                    saved, skipped = save_transactions(transactions)
                    st.success(f"Saved {saved} new transactions. Skipped {skipped} duplicates.")
            else:
                st.warning("No transactions found")

# --- Net Worth Page ---
elif page == "Net Worth":
    st.header("Net Worth")

    from networth import (
        get_all_asset_history, get_asset_names, import_from_worthit,
        update_asset_value, delete_asset,
        get_total_net_worth_series, project_net_worth
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

    if not records:
        st.info("No net worth data yet. Import your Worth It export above.")

    elif st.session_state.nw_selected_asset:
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

            fig_total = px.line(
                daily_total, x='Date', y='Total',
                labels={'Total': 'Total Assets (£)', 'Date': ''},
            )
            fig_total.update_traces(line_color='#1D9E75', line_width=2, name='Actual', showlegend=True)
            fig_total.update_layout(
                yaxis_tickprefix='£',
                yaxis_tickformat=',.0f',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=0, b=0)
            )

            # --- Projected trend line ---
            # Anchored on the TRUE latest total from full history (via
            # project_net_worth), never on the filtered daily_total above - the
            # growth rate and starting point must not depend on which time
            # filter the user has selected on this page.
            projection = project_net_worth(years=PROJECTION_YEARS)

            if projection['ok']:
                anchor_ts = pd.Timestamp(projection['anchor_date'])
                rate = projection['rate']
                future_dates = [anchor_ts + pd.DateOffset(years=yr) for yr in range(PROJECTION_YEARS + 1)]
                future_values = [projection['anchor_value'] * (1 + rate) ** yr for yr in range(PROJECTION_YEARS + 1)]

                fig_total.add_trace(go.Scatter(
                    x=future_dates, y=future_values,
                    mode='lines',
                    line=dict(color='#1D9E75', width=2, dash='dash'),
                    opacity=0.5,
                    name=f'Projected ({rate*100:.1f}%/yr)'
                ))

            st.plotly_chart(fig_total, use_container_width=True)

            if projection['ok']:
                st.caption(
                    f"Dashed line: a rough {PROJECTION_YEARS}-year projection based on your full asset "
                    f"history (independent of the filter buttons above), assuming your historical blended "
                    f"growth rate of {projection['rate']*100:.1f}%/year continues. This rate reflects both "
                    f"market performance and your own contributions over time - it is not a pure investment "
                    f"return, and it is not a guarantee of future results."
                )
            else:
                st.caption("Not enough net worth history yet to show a projection.")

        # --- Asset list ---
        with st.container(border=True, key="card_nw_assetlist"):
            st.subheader("Assets")
            st.caption("Click an asset to see its full history")

            asset_summary = df.sort_values('Date').groupby('Asset').agg(
                Value=('Value', 'last'),
                Tag=('Tag', 'last')
            ).reset_index().sort_values('Value', ascending=False)

            header = st.columns([4, 2, 2])
            header[0].caption("ASSET")
            header[1].caption("CATEGORY")
            header[2].caption("VALUE")

            for _, row in asset_summary.iterrows():
                cols = st.columns([4, 2, 2])
                with cols[0]:
                    if st.button(row['Asset'], key=f"nw_asset_{row['Asset']}", use_container_width=True):
                        st.session_state.nw_selected_asset = row['Asset']
                        st.rerun()
                with cols[1]:
                    st.write(row['Tag'])
                with cols[2]:
                    st.write(f"£{row['Value']:,.0f}")

        # Add or remove an asset
        with st.expander("Add or Remove an Asset"):
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
    st.header("Personal Budget")

    from budget import (
        get_personal_items, replace_personal_section, get_personal_total_expenses,
        get_personal_total_income, set_personal_total_income
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
        total_income = get_personal_total_income()
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

    with st.container(border=True, key="card_personal_summary"):
        st.subheader("Money Left Over")
        total_expenses = get_personal_total_expenses()
        income_minus_expenses = total_income - total_expenses
        money_per_week = income_minus_expenses / 4

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total expenses", f"£{total_expenses:,.2f}")
        with col2:
            st.metric("Income minus expenses", f"£{income_minus_expenses:,.2f}")
        with col3:
            st.metric("Money per week", f"£{money_per_week:,.2f}")

# --- Household Budget Page ---
elif page == "Household Budget":
    st.header("Household Budget")

    from budget import (
        get_household_items, replace_household_items, get_household_total,
        get_household_split_percent, set_household_split_percent
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
        split_pct = st.number_input(
            "Jonny's share (%)", min_value=0.0, max_value=100.0, step=1.0,
            value=get_household_split_percent(), key="household_split_input"
        )
        if st.button("Save Split %", key="save_split_pct"):
            set_household_split_percent(split_pct)
            st.success("Saved")
            st.rerun()

        jonny_share = total * (split_pct / 100)
        steph_share = total * (1 - split_pct / 100)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Jonny", f"£{jonny_share:,.2f}")
        with col2:
            st.metric("Steph", f"£{steph_share:,.2f}")

# --- View Transactions Page ---
elif page == "View Transactions":
    st.header("All Transactions")
    
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
    st.header("Manage Categories")
    st.write("Review and correct how each merchant has been categorised.")

    from database import get_db, Transaction
    from categoriser import CATEGORIES

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

    with st.container(border=True, key="card_manage_merchant_table"):
        db = get_db()
        merchants = db.query(
            Transaction.description,
            Transaction.category
        ).distinct(Transaction.description).all()
        db.close()

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

        if st.button("Update category"):
            db = get_db()
            transactions_to_update = db.query(Transaction).filter_by(
                description=selected_merchant
            ).all()
            for t in transactions_to_update:
                t.category = new_category
            db.commit()
            db.close()
            st.success(f"Updated all '{selected_merchant}' transactions to '{new_category}'")