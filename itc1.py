import streamlit as st
from mysql.connector import Error
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

class GSTDatabase:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        try:
            # Try Streamlit secrets first (for production)
            try:
                config = {
                    "host": st.secrets["DB_HOST"],
                    "user": st.secrets["DB_USER"],
                    "password": st.secrets["DB_PASSWORD"],
                    "database": st.secrets["DB_NAME"]
                }
            except:
                # Fall back to .env (for local development)
                load_dotenv()
                config = {
                    "host": os.getenv("DB_HOST"),
                    "user": os.getenv("DB_USER"),
                    "password": os.getenv("DB_PASSWORD"),
                    "database": os.getenv("DB_NAME")
                }

            self.connection = mysql.connector.connect(
                **config,
                port=3306,
                auth_plugin='mysql_native_password',
                connect_timeout=5
            )
            self._ensure_columns_exist()
            return self.connection
        except Error as e:
            st.error("Database connection failed. Please check your settings.")
            st.stop()
    
    def _ensure_columns_exist(self):
        """Ensure required columns exist in the table"""
        try:
            cursor = self.connection.cursor()
            
            # Check if columns exist
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'gst_transactions' 
                AND TABLE_SCHEMA = DATABASE()
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            
            # Add missing columns
            if 'is_filed' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE gst_transactions 
                    ADD COLUMN is_filed BOOLEAN DEFAULT FALSE
                """)
            
            if 'filing_date' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE gst_transactions 
                    ADD COLUMN filing_date DATE NULL
                """)
                
            self.connection.commit()
        except Error as e:
            st.error("Error configuring database table structure")
            raise

    def add_transaction(self, transaction_data):
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO gst_transactions 
            (transaction_date, supplier_name, customer_name, 
             purchase_amount, sale_amount, gst_paid, gst_charged, 
             gst_rate, due_date, is_filed, filing_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                transaction_data['date'],
                transaction_data.get('supplier', ''),
                transaction_data.get('customer', ''),
                transaction_data['purchase'],
                transaction_data['sale'],
                transaction_data['gst_paid'],
                transaction_data['gst_charged'],
                transaction_data['gst_rate'],
                transaction_data['due_date'],
                transaction_data.get('is_filed', False),
                transaction_data.get('filing_date')
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            st.error("Failed to save transaction")
            return None

    # ... [keep all other methods exactly the same, no changes needed below] ...
    # The rest of your methods (update_filing_status, get_transactions, get_summary) 
    # can remain exactly as they were in your original code

# [Rest of your Streamlit app code remains exactly the same]
# The main() function and all other code below can stay identical
    def _ensure_columns_exist(self):
        """Ensure required columns exist in the table"""
        try:
            cursor = self.connection.cursor()
            
            # Check if columns exist
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'gst_transactions' 
                AND TABLE_SCHEMA = 'fineaseai'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            
            # Add missing columns
            if 'is_filed' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE gst_transactions 
                    ADD COLUMN is_filed BOOLEAN DEFAULT FALSE
                """)
            
            if 'filing_date' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE gst_transactions 
                    ADD COLUMN filing_date DATE NULL
                """)
                
            self.connection.commit()
        except Error as e:
            st.error(f"Error ensuring table structure: {e}")
            raise

    # Rest of your database methods remain the same...
    def add_transaction(self, transaction_data):
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO gst_transactions 
            (transaction_date, supplier_name, customer_name, 
             purchase_amount, sale_amount, gst_paid, gst_charged, 
             gst_rate, due_date, is_filed, filing_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                transaction_data['date'],
                transaction_data.get('supplier', ''),
                transaction_data.get('customer', ''),
                transaction_data['purchase'],
                transaction_data['sale'],
                transaction_data['gst_paid'],
                transaction_data['gst_charged'],
                transaction_data['gst_rate'],
                transaction_data['due_date'],
                transaction_data.get('is_filed', False),
                transaction_data.get('filing_date')
            ))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            st.error(f"Failed to add GST transaction: {e}")
            return None

    def update_filing_status(self, transaction_ids, is_filed, filing_date=None):
        try:
            cursor = self.connection.cursor()
            if filing_date:
                query = """
                UPDATE gst_transactions 
                SET is_filed = %s, filing_date = %s
                WHERE id IN ({})
                """.format(','.join(['%s'] * len(transaction_ids)))
                params = [is_filed, filing_date] + transaction_ids
            else:
                query = """
                UPDATE gst_transactions 
                SET is_filed = %s
                WHERE id IN ({})
                """.format(','.join(['%s'] * len(transaction_ids)))
                params = [is_filed] + transaction_ids
            
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
        except Error as e:
            st.error(f"Failed to update filing status: {e}")
            return 0

# Rest of your Streamlit app remains the same...
    def get_transactions(self, period=None, filed_status=None):
        try:
            query = """
            SELECT 
                id,
                DATE_FORMAT(transaction_date, '%d-%b-%Y') AS date,
                supplier_name as supplier,
                customer_name as customer,
                purchase_amount AS purchase,
                sale_amount AS sale,
                gst_paid,
                gst_charged,
                gst_rate,
                DATE_FORMAT(due_date, '%d-%b-%Y') AS due_date,
                net_liability,
                is_filed
            FROM gst_transactions
            WHERE 1=1
            """
            params = []
            
            if period:
                query += " AND transaction_date BETWEEN %s AND %s"
                params.extend([period['start'], period['end']])
            
            if filed_status is not None:
                query += " AND is_filed = %s"
                params.append(filed_status)
            
            query += " ORDER BY transaction_date DESC"
            
            return pd.read_sql(query, self.connection, params=params)
        except Error as e:
            st.error(f"Failed to fetch GST transactions: {e}")
            return pd.DataFrame()
    
    def get_summary(self, period=None, filed_status=None):
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT 
                SUM(gst_paid) AS total_itc,
                SUM(gst_charged) AS total_liability,
                SUM(net_liability) AS net_amount,
                COUNT(*) AS transaction_count
            FROM gst_transactions
            WHERE 1=1
            """
            params = []
            
            if period:
                query += " AND transaction_date BETWEEN %s AND %s"
                params.extend([period['start'], period['end']])
            
            if filed_status is not None:
                query += " AND is_filed = %s"
                params.append(filed_status)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return {
                'total_itc': result[0] or 0,
                'total_liability': result[1] or 0,
                'net': result[2] or 0,
                'count': result[3] or 0
            }
        except Error as e:
            st.error(f"Failed to calculate GST summary: {e}")
            return {'total_itc': 0, 'total_liability': 0, 'net': 0, 'count': 0}

# Main App with Enhanced Filing Management
def main():
    st.set_page_config(page_title="GST Pro", page_icon="📊", layout="wide")
    
    # Custom CSS
    st.markdown("""
    <style>
        .header { font-size: 1.8rem !important; font-weight: 700 !important; }
        .subheader { font-size: 1.2rem !important; color: #555 !important; }
        .filed-true { background-color: #e8f5e9 !important; }
        .filed-false { background-color: #ffebee !important; }
        .stDataFrame [data-testid="stDataFrame"] { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="header">🧾 GST Pro</p>', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Complete GST Management with Filing Status</p>', unsafe_allow_html=True)
    
    # Initialize database connection
    gst_db = GSTDatabase()
    connection = gst_db.connect()
    if not connection:
        st.error("Cannot connect to database. Please check your connection settings.")
        return
    
    # Navigation
    tab1, tab2, tab3 = st.tabs(["➕ New Transaction", "📊 Dashboard", "📝 Filing Management"])
    
    with tab1:
        with st.form("transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Purchase Details")
                purchase_date = st.date_input("Date*", datetime.now())
                supplier_name = st.text_input("Supplier Name")
                purchase_amount = st.number_input("Purchase Amount (₹)*", 
                                               min_value=0.0, step=100.0)
                gst_paid = st.number_input("GST Paid (₹)*", 
                                         min_value=0.0, step=1.0)
            
            with col2:
                st.subheader("Sale Details")
                customer_name = st.text_input("Customer Name")
                sale_amount = st.number_input("Sale Amount (₹)*", 
                                            min_value=0.0, step=100.0)
                gst_rate = st.selectbox("GST Rate (%)*", 
                                      [0, 5, 12, 18, 28], index=3)
                due_date = st.date_input("Filing Due Date*", 
                                       datetime.now() + timedelta(days=30))
                is_filed = st.checkbox("Mark as filed", value=False)
            
            if st.form_submit_button("💾 Save Transaction"):
                if not all([purchase_date, purchase_amount, gst_paid, sale_amount, due_date]):
                    st.error("Please fill all required fields (marked with *)")
                else:
                    gst_on_sale = (sale_amount * gst_rate) / 100
                    
                    transaction_data = {
                        'date': purchase_date.strftime('%Y-%m-%d'),
                        'supplier': supplier_name,
                        'customer': customer_name,
                        'purchase': purchase_amount,
                        'sale': sale_amount,
                        'gst_paid': gst_paid,
                        'gst_charged': gst_on_sale,
                        'gst_rate': gst_rate,
                        'due_date': due_date.strftime('%Y-%m-%d'),
                        'is_filed': is_filed
                    }
                    
                    if gst_db.add_transaction(transaction_data):
                        st.success("Transaction saved successfully!")
                        st.rerun()
    
    with tab2:
        st.header("GST Dashboard")
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                      datetime.now() - timedelta(days=30), key="dash_start")
        with col2:
            end_date = st.date_input("End Date", datetime.now(), key="dash_end")
        
        # Filing status filter
        filing_status = st.radio("Show transactions:", 
                                ["All", "Pending Filing", "Filed"], 
                                horizontal=True, key="dash_status")
        
        period = {'start': start_date, 'end': end_date}
        filed_filter = None if filing_status == "All" else filing_status == "Filed"
        
        # Get data
        df = gst_db.get_transactions(period, filed_filter)
        summary = gst_db.get_summary(period, filed_filter)
        
        if not df.empty:
            # Summary Cards
            st.subheader("Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total ITC", f"₹{summary['total_itc']:,.2f}", 
                       delta="Claimable", help="Input Tax Credit Available")
            col2.metric("Total Liability", f"₹{summary['total_liability']:,.2f}", 
                       delta="Payable", help="GST to be paid to government")
            col3.metric("Net Amount", f"₹{summary['net']:,.2f}", 
                       delta_color="inverse",
                       delta=f"{'Pay' if summary['net'] > 0 else 'Refund'} ₹{abs(summary['net']):,.2f}")
            col4.metric("Transactions", summary['count'])
            
            # Transactions Table with filing status
            st.subheader("Transaction Details")
            
            # Convert DataFrame to editable format
            edited_df = st.data_editor(
                df,
                column_config={
                    "is_filed": st.column_config.CheckboxColumn(
                        "Filed?",
                        help="Mark transactions as filed",
                        default=False
                    )
                },
                disabled=["id", "date", "supplier", "customer", "purchase", 
                         "sale", "gst_paid", "gst_charged", "gst_rate", 
                         "due_date", "net_liability"],
                hide_index=True,
                use_container_width=True
            )
            
            # Detect changes in filing status
            if not df.equals(edited_df):
                changed_rows = edited_df[edited_df['is_filed'] != df['is_filed']]
                if not changed_rows.empty:
                    transaction_ids = changed_rows['id'].tolist()
                    new_status = changed_rows['is_filed'].iloc[0]
                    
                    if gst_db.update_filing_status(transaction_ids, new_status):
                        st.success(f"Updated filing status for {len(transaction_ids)} transaction(s)!")
                        st.rerun()
        else:
            st.warning("No transactions found for the selected filters")
    
    with tab3:
        st.header("📝 Filing Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Bulk Filing Actions")
            
            # Get pending transactions
            pending_df = gst_db.get_transactions(filed_status=False)
            pending_summary = gst_db.get_summary(filed_status=False)
            
            if not pending_df.empty:
                st.markdown(f"**You have {len(pending_df)} pending transactions**")
                st.metric("Pending ITC", f"₹{pending_summary['total_itc']:,.2f}")
                st.metric("Pending Liability", f"₹{pending_summary['total_liability']:,.2f}")
                
                if st.button("✅ Mark All as Filed", type="primary"):
                    transaction_ids = pending_df['id'].tolist()
                    if gst_db.update_filing_status(transaction_ids, True):
                        st.success(f"Marked {len(transaction_ids)} transactions as filed!")
                        st.rerun()
            else:
                st.success("All transactions are filed!")
        
        with col2:
            st.subheader("Filing Reports")
            
            # Filed transactions report
            filed_df = gst_db.get_transactions(filed_status=True)
            if not filed_df.empty:
                st.download_button(
                    label="📄 Download Filed Transactions (CSV)",
                    data=filed_df.to_csv(index=False).encode('utf-8'),
                    file_name="filed_transactions.csv",
                    mime="text/csv"
                )
                
                # Monthly filing summary
                filed_df['month'] = pd.to_datetime(filed_df['date']).dt.to_period('M')
                monthly_summary = filed_df.groupby('month').agg({
                    'gst_paid': 'sum',
                    'gst_charged': 'sum',
                    'id': 'count'
                }).rename(columns={'id': 'count'})
                
                st.write("**Monthly Filing Summary**")
                st.dataframe(monthly_summary, use_container_width=True)
            else:
                st.info("No filed transactions yet")
    
    connection.close()

if __name__ == "__main__":
    main()