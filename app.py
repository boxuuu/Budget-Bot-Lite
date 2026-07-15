import streamlit as st
import fitz
import pandas as pd
import re
from database import save_transactions, load_all_transactions, get_months
from categoriser import categorise_all, recategorise_all
from database import get_db, Transaction

st.set_page_config(page_title="Budget Bot", layout="wide")
st.title("Budget Bot")

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
page = st.sidebar.radio("Go to", ["Dashboard", "Net Worth", "Chat", "Upload Statement", "View Transactions", "Manage Categories"])

# --- Dashboard Page ---
if page == "Dashboard":
    st.header("Dashboard")

    all_transactions = load_all_transactions()

    if not all_transactions:
        st.info("No transactions yet - upload a statement first")
    else:
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

        # --- Summary Metrics ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spent (6 months)", f"£{spending['Amount'].sum():,.2f}")
        with col2:
            st.metric("Monthly Average", f"£{spending['Amount'].sum() / 6:,.2f}")
        with col3:
            st.metric("Total Transactions", len(spending))

        st.divider()

        # --- Spending by Category ---
        st.subheader("Spending by Category")
        category_totals = spending.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        st.bar_chart(category_totals)

        st.divider()

        # --- Month by Month Trend ---
        st.subheader("Monthly Spending Trend")
        
        # Sort months chronologically
        month_order = ['Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026']
        monthly_totals = spending.groupby('Month')['Amount'].sum()
        monthly_totals = monthly_totals.reindex([m for m in month_order if m in monthly_totals.index])
        st.line_chart(monthly_totals)

        st.divider()

        # --- Top 10 Biggest Transactions ---
        st.subheader("Top 10 Biggest Transactions")
        top10 = spending.nlargest(10, 'Amount')[['Date', 'Description', 'Category', 'Amount']]
        top10['Amount'] = top10['Amount'].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(top10, use_container_width=True)

if page == "Upload Statement":
    st.header("Upload Statement")
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
        update_asset_value, delete_asset
    )
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
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
        st.divider()

        st.subheader(asset)

        latest_val = asset_df.iloc[-1]['Value'] if not asset_df.empty else 0
        first_val = asset_df.iloc[0]['Value'] if not asset_df.empty else 0
        pct_change = ((latest_val - first_val) / first_val * 100) if first_val else 0

        st.markdown(
            """
            <style>
            .st-key-nw_asset_metric [data-testid="stMetricValue"] { font-size: 3rem; }
            </style>
            """,
            unsafe_allow_html=True
        )
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

        st.divider()
        st.subheader("All Updates")

        history_df = asset_df.sort_values('Date', ascending=False).copy()
        history_df['Date'] = history_df['Date'].dt.strftime('%d %b %Y, %H:%M')
        history_df['Value'] = history_df['Value'].apply(lambda v: f"£{v:,.2f}")
        history_df.columns = ['Recorded', 'Value']
        st.dataframe(history_df, use_container_width=True, hide_index=True)

        st.divider()

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
        st.divider()

        # --- Total net worth ---
        # Get total per date by forward-filling each asset's latest known value,
        # so a day only one asset was updated still counts every other asset's last value
        df['DateOnly'] = df['Date'].dt.date
        asset_pivot = df.sort_values('Date').pivot_table(
            index='DateOnly', columns='Asset', values='Value', aggfunc='last'
        ).ffill()
        daily_total = asset_pivot.sum(axis=1).reset_index()
        daily_total.columns = ['Date', 'Total']

        # Current total and its change over the selected filter period
        latest_total = daily_total.iloc[-1]['Total'] if not daily_total.empty else 0
        first_total = daily_total.iloc[0]['Total'] if not daily_total.empty else 0
        pct_change = ((latest_total - first_total) / first_total * 100) if first_total else 0

        st.markdown(
            """
            <style>
            .st-key-nw_total_metric [data-testid="stMetricValue"] { font-size: 3rem; }
            </style>
            """,
            unsafe_allow_html=True
        )
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
        fig_total.update_traces(line_color='#1D9E75', line_width=2)
        fig_total.update_layout(
            yaxis_tickprefix='£',
            yaxis_tickformat=',.0f',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig_total, use_container_width=True)

        st.divider()

        # --- Asset list ---
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

# --- Chat Page ---
elif page == "Chat":
    st.header("Chat with Budget Bot")
    st.write("Ask questions about your spending, tell me to fix a category, or update an account balance.")

    from chat import chat_with_budget_bot, update_category
    from networth import update_asset_value

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if st.session_state.pending_action:
        action = st.session_state.pending_action
        with st.chat_message("assistant"):
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


# --- View Transactions Page ---
elif page == "View Transactions":
    st.header("All Transactions")
    
    all_transactions = load_all_transactions()
    
    if all_transactions:
        df = pd.DataFrame([{
            'Date': t.date,
            'Description': t.description,
            'Amount': t.amount,
            'Category': t.category,
            'Month': t.month
        } for t in all_transactions])
        
        # Filter by month
        months = sorted(df['Month'].unique().tolist())
        selected_month = st.selectbox("Filter by month", ["All months"] + months)
        
        if selected_month != "All months":
            df = df[df['Month'] == selected_month]

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

        st.dataframe(df, use_container_width=True)
        st.caption(f"Showing {len(df)} transactions")
    else:
        st.info("No transactions yet - upload a statement first")

        # --- Upload Page ---
elif page == "Upload Statement":
    st.header("Upload Statement")
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

# --- Manage Categories Page ---
elif page == "Manage Categories":
    st.header("Manage Categories")
    st.write("Review and correct how each merchant has been categorised.")

    from database import get_db, Transaction
    from categoriser import CATEGORIES

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

    st.divider()
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