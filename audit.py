import streamlit as st
from datetime import datetime, timedelta
from typing import List
import pandas as pd
import pdfplumber
import tempfile
import os
from fpdf import FPDF

# Page configuration (must be first)
st.set_page_config(
    page_title="Professional Audit Reporter", 
    page_icon="📊", 
    layout="wide"
)

# Custom CSS for modern blue theme
st.markdown("""
<style>
    /* Main page styling */
    .main {
        background-color: #e6f2ff;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #1a237e !important;
        background-image: linear-gradient(180deg, #1a237e, #303f9f);
    }
    
    /* Title styling */
    h1, h2, h3, h4, h5, h6 {
        color: #1a237e !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar titles */
    .sidebar .sidebar-content h1,
    .sidebar .sidebar-content h2,
    .sidebar .sidebar-content h3 {
        color: white !important;
    }
    
    /* Widget styling */
    .stTextInput>div>div>input, 
    .stNumberInput>div>div>input, 
    .stDateInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>select {
        background-color: white !important;
        border: 1px solid #1a237e;
        border-radius: 4px;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #1a237e !important;
        color: white !important;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #303f9f !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    
    /* Download button */
    .stDownloadButton>button {
        background-color: #1a237e !important;
        color: white !important;
        border: none;
        border-radius: 4px;
    }
    
    /* Radio buttons */
    .stRadio>div>label>div:first-child {
        background-color: white !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border: 1px solid #1a237e;
        border-radius: 4px;
    }
    
    /* Expander styling */
    .stExpander {
        border: 1px solid #1a237e;
        border-radius: 4px;
    }
    
    /* Divider line */
    .stMarkdown hr {
        border: 1px solid #1a237e;
        opacity: 0.3;
    }
    
    /* Card-like containers */
    .stAlert, .stWarning, .stError, .stSuccess {
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Spinner color */
    .stSpinner>div>div {
        border-color: #1a237e transparent transparent transparent !important;
    }
</style>
""", unsafe_allow_html=True)

class Document:
    def __init__(self, id: str, date: str, vendor: str, amount: float, gst: float, type: str):
        self.id = id
        self.date = date
        self.vendor = vendor
        self.amount = amount
        self.gst = gst
        self.type = type

def extract_data_from_pdf(pdf_file):
    """Extract data from uploaded PDF invoices"""
    documents = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            vendor = "Unknown"
            date = datetime.now().strftime("%Y-%m-%d")
            amount = 0.0
            gst = 0.0
            doc_id = "PDF-" + str(hash(text) % 1000000)
            
            for line in lines:
                if "Vendor:" in line:
                    vendor = line.replace("Vendor:", "").strip()
                elif "Date:" in line:
                    date = line.replace("Date:", "").strip()
                elif "Total:" in line:
                    amount = float(line.replace("Total:", "").replace("₹", "").replace(",", "").strip())
                elif "GST:" in line:
                    gst = float(line.replace("GST:", "").replace("₹", "").replace(",", "").strip())
            
            doc_type = "expense" if "Invoice" in text else "income"
            documents.append(Document(doc_id, date, vendor, amount, gst, doc_type))
    return documents

def extract_data_from_csv(csv_file):
    """Extract data from uploaded CSV file"""
    df = pd.read_csv(csv_file)
    documents = []
    for _, row in df.iterrows():
        try:
            doc = Document(
                id=str(row.get('id', row.get('invoice_no', f"CSV-{_}"))),
                date=str(row.get('date', datetime.now().strftime("%Y-%m-%d"))),
                vendor=str(row.get('vendor', 'Unknown')),
                amount=float(row.get('amount', 0)),
                gst=float(row.get('gst', 0)),
                type=str(row.get('type', 'expense')).lower()
            )
            documents.append(doc)
        except Exception as e:
            st.warning(f"Skipping row {_}: {e}")
    return documents

def create_pdf(report_text, business_name, start_date, end_date):
    """Create a PDF version of the report with proper encoding"""
    # Clean text for PDF compatibility
    def clean_text(text):
        # Replace emojis and special characters
        replacements = {
            '📊': '[REPORT]', '📅': '[DATE]', '📌': '[SUMMARY]',
            '📈': '[ANALYSIS]', '🧾': '[GST]', '🤖': '[AI]',
            '✅': '[CHECK]', '₹': 'Rs.', '‘': "'", '’': "'",
            '“': '"', '”': '"', '–': '-', '—': '-', '…': '...'
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=clean_text(f"{business_name} - Audit Report"), ln=1, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=clean_text(f"Period: {start_date} to {end_date}"), ln=1, align='C')
    pdf.ln(10)
    
    # Process each section
    sections = report_text.split('## ')
    for section in sections[1:]:
        title = clean_text(section.split('\n')[0])
        content = '\n'.join([clean_text(line) for line in section.split('\n')[1:]])
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=title, ln=1)
        pdf.set_font("Arial", '', 12)
        
        for line in content.split('\n'):
            if line.strip():
                pdf.multi_cell(0, 8, txt=line.strip())
        pdf.ln(5)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name
    pdf.output(pdf_path)
    return pdf_path

def generate_audit_report(business_name, start_date, end_date, documents, risk_flags):
    """Generate comprehensive audit report with text icons for PDF"""
    # Filter documents by date range
    filtered_docs = []
    for doc in documents:
        try:
            doc_date = datetime.strptime(doc.date, "%Y-%m-%d").date()
            if start_date <= doc_date <= end_date:
                filtered_docs.append(doc)
        except:
            continue
    
    # Calculate financials
    df = pd.DataFrame([vars(d) for d in filtered_docs])
    total_invoices = len(filtered_docs)
    total_income = df[df['type'] == 'income']['amount'].sum()
    total_expense = df[df['type'] == 'expense']['amount'].sum()
    net_balance = total_income - total_expense
    expense_ratio = (total_expense / total_income) * 100 if total_income > 0 else 0
    profit_margin = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
    duration_days = (end_date - start_date).days + 1
    
    # 1. Executive Summary (using text icons)
    report = f"# {business_name} - Audit Report\n"
    report += f"## Period: {start_date} to {end_date} ({duration_days} days)\n\n"
    report += "## Executive Summary\n\n"
    report += f"- **Financial Overview**: Net balance of Rs.{net_balance:,.2f} "
    report += f"(Income: Rs.{total_income:,.2f}, Expenses: Rs.{total_expense:,.2f})\n"
    report += f"- **Profit Margin**: {profit_margin:.1f}%\n"
    report += f"- **Expense Ratio**: {expense_ratio:.1f}% of income\n"
    report += f"- **Transactions Processed**: {total_invoices}\n\n"
    
    # 2. Cash Flow Analysis
    report += "## Cash Flow Analysis\n\n"
    
    if not df.empty:
        # Income breakdown
        income_df = df[df['type'] == 'income']
        if not income_df.empty:
            report += "### Income Sources\n"
            top_income = income_df.groupby('vendor')['amount'].sum().nlargest(3)
            for vendor, amount in top_income.items():
                report += f"- {vendor}: Rs.{amount:,.2f}\n"
        
        # Expense breakdown
        expense_df = df[df['type'] == 'expense']
        if not expense_df.empty:
            report += "\n### Major Expenses\n"
            top_expenses = expense_df.groupby('vendor')['amount'].sum().nlargest(3)
            for vendor, amount in top_expenses.items():
                report += f"- {vendor}: Rs.{amount:,.2f}\n"
    
    # 3. GST Compliance
    report += "\n## GST Compliance\n\n"
    gst_docs = [doc for doc in filtered_docs if doc.gst > 0]
    if gst_docs:
        total_gst = sum(doc.gst for doc in gst_docs)
        report += f"- **Total GST Processed**: Rs.{total_gst:,.2f}\n"
        
        # Check for GST issues
        gst_issues = []
        for doc in gst_docs:
            if not any(x in doc.id.upper() for x in ['GST', 'INV', 'BILL']):
                gst_issues.append(f"Invalid document ID: {doc.id}")
            if doc.gst > doc.amount * 0.3:
                gst_issues.append(f"Unusual GST amount: Rs.{doc.gst} on Rs.{doc.amount}")
        
        if gst_issues:
            report += "\n### GST Issues\n"
            for issue in gst_issues[:3]:
                report += f"- {issue}\n"
    else:
        report += "- No GST-related transactions found\n"
    
    # 4. AI Insights
    report += "\n## AI Insights\n\n"
    if not df.empty:
        vendor_counts = df['vendor'].value_counts()
        if len(vendor_counts) > 0:
            main_vendor = vendor_counts.idxmax()
            report += f"- **Vendor Concentration**: {main_vendor} appears {vendor_counts.max()} times\n"
        
        if expense_ratio > 70:
            report += f"- **Cost Alert**: High expense ratio ({expense_ratio:.1f}%)\n"
    
    # 5. Recommendations
    report += "\n## Recommendations\n\n"
    report += "### Immediate Actions\n"
    if gst_docs:
        report += "- Reconcile GST input credits\n"
    if risk_flags:
        report += "- Address compliance flags\n"
    
    report += "\n### Strategic Actions\n"
    if profit_margin < 15:
        report += "- Review pricing strategy\n"
    if len(df) > 50:
        report += "- Consider accounting software for better tracking\n"
    
    report += f"\n*Report generated on {datetime.now().strftime('%d %b %Y %H:%M')}*"
    
    return report

def main():
    """Main function that runs the Streamlit app"""
    # Sidebar configuration
    with st.sidebar:
        st.title("Audit Report Configuration")
        business_name = st.text_input("Company Name", "Acme Enterprises")
        
        st.subheader("Report Duration")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                    value=datetime.now() - timedelta(days=30),
                                    min_value=datetime(2000,1,1))
        with col2:
            end_date = st.date_input("End Date", 
                                   value=datetime.now(),
                                   min_value=datetime(2000,1,1))
        
        if start_date > end_date:
            st.error("End date must be after start date")
            st.stop()
        
        st.subheader("Data Input Method")
        input_method = st.radio("Select input method:", 
                              ["Upload Documents", "Manual Entry"], 
                              index=0)
    
    # Main content area
    st.title("Professional Audit Report Generator")
    st.markdown("---")
    
    documents = []
    risk_flags = ["Verify all documents for accuracy"]
    
    if input_method == "Upload Documents":
        st.header("Upload Financial Documents")
        uploaded_files = st.file_uploader(
            "Upload PDF invoices or CSV files",
            type=["pdf", "csv"],
            accept_multiple_files=True,
            help="Upload your financial documents for automated processing"
        )
        
        if uploaded_files:
            with st.expander("Uploaded Documents Preview", expanded=True):
                all_docs = []
                for uploaded_file in uploaded_files:
                    try:
                        if uploaded_file.name.lower().endswith('.pdf'):
                            docs = extract_data_from_pdf(uploaded_file)
                            all_docs.extend(docs)
                        elif uploaded_file.name.lower().endswith('.csv'):
                            docs = extract_data_from_csv(uploaded_file)
                            all_docs.extend(docs)
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                
                if all_docs:
                    documents = all_docs
                    df = pd.DataFrame([vars(d) for d in all_docs])
                    st.dataframe(df)
    
    else:  # Manual Entry
        st.header("Manual Data Entry")
        
        with st.expander("Add Transactions", expanded=True):
            sample_data = [
                ["INV-101", "2023-06-05", "Client A", 150000, 27000, "income"],
                ["GSTIN-AB123", "2023-06-08", "Supplier X", 50000, 9000, "expense"],
                ["INV-102", "2023-06-12", "Client B", 200000, 36000, "income"]
            ]
            
            edited_df = st.data_editor(
                pd.DataFrame(
                    sample_data,
                    columns=["ID", "Date", "Vendor", "Amount", "GST", "Type"]
                ),
                num_rows="dynamic",
                use_container_width=True
            )
            
            # Convert to Document objects
            for _, row in edited_df.iterrows():
                try:
                    doc = Document(
                        id=str(row['ID']),
                        date=str(row['Date']),
                        vendor=str(row['Vendor']),
                        amount=float(row['Amount']),
                        gst=float(row['GST']),
                        type=str(row['Type']).lower()
                    )
                    documents.append(doc)
                except Exception as e:
                    st.warning(f"Skipping invalid row: {e}")
        
        st.subheader("Compliance Flags")
        risk_flags = st.text_area(
            "Enter any known compliance issues (one per line)", 
            "Verify GSTIN details\nCheck for duplicate payments",
            help="List any specific compliance concerns to highlight in the report"
        )
        risk_flags = [flag.strip() for flag in risk_flags.split("\n") if flag.strip()]
    
    # Generate report section
    st.markdown("---")
    if st.button("✨ Generate Professional Audit Report", use_container_width=True):
        if not documents:
            st.warning("No transaction data available. Please upload documents or enter data manually.")
            st.stop()
        
        with st.spinner("Generating comprehensive audit report..."):
            report = generate_audit_report(
                business_name,
                start_date,
                end_date,
                documents,
                risk_flags
            )
            
            # Display report
            st.markdown("---")
            st.markdown(report, unsafe_allow_html=True)
            
            # Create and offer PDF download
            pdf_path = create_pdf(report, business_name, start_date, end_date)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=f,
                    file_name=f"{business_name}_Audit_Report_{start_date}_to_{end_date}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            os.unlink(pdf_path)

if __name__ == "__main__":
    main()