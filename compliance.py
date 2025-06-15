import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from urllib.parse import urljoin, urlparse
import feedparser
import google.generativeai as genai
from typing import List, Dict, Any
import mysql.connector
from mysql.connector import Error

# Page configuration
st.set_page_config(
    page_title="AI Compliance Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for appealing design
def add_custom_css():
    st.markdown("""
    <style>
    /* Main background with gradient */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    /* Custom card styling */
    .custom-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin: 10px 0;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
        padding: 30px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #ffffff, #f0f2f6);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #4ecdc4;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Alert boxes */
    .alert-high {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #ff4757;
    }
    
    .alert-medium {
        background: linear-gradient(135deg, #ffa726, #ff9800);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #f57c00;
    }
    
    .alert-low {
        background: linear-gradient(135deg, #4ecdc4, #44a08d);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #26a69a;
    }
    
    /* Loading animation */
    .loading {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255,255,255,.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* Data table styling */
    .dataframe {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Initialize Gemini API (Add your API key)
@st.cache_resource
def init_gemini():
    """Initialize Gemini API for real-time web scraping"""
    try:
        # Replace with your actual Gemini API key
        genai.configure(api_key=st.secrets.get("GEMINI_API_KEY","AIzaSyC9jEg8Icw6kMPs0tdncQKUCGtdeI_xINo")) # Replace or set as environment variable
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        return model
    except Exception as e:
        st.warning(f"Gemini API not configured: {e}")
        return None

# Real-time web scraping functions
class LiveComplianceUpdater:
    def __init__(self):
        self.official_sources = {
            'income_tax': [
                'https://www.incometax.gov.in/iec/foportal/resources/notifications',
                'https://www.incometax.gov.in/iec/foportal/resources/latest-news',
                'https://incometaxindia.gov.in/news/latest-news.htm'
            ],
            'gst': [
                'https://www.cbic.gov.in/resources/notifications',
                'https://www.gst.gov.in/newsandupdates/notifications',
                'https://www.cbic.gov.in/resources/latest-notifications'
            ],
            'mca': [
                'https://www.mca.gov.in/MinistryV2/notifications',
                'https://www.mca.gov.in/MinistryV2/latest-notifications'
            ],
            'rss_feeds': [
                'https://www.incometax.gov.in/iec/foportal/rss-feeds/notifications',
                'https://www.cbic.gov.in/resources/rss-feeds'
            ]
        }
        
        self.news_sources = [
            'https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/1017519.cms',
            'https://www.business-standard.com/rss/category/economy-policy-1020101.rss',
            'https://www.livemint.com/rss/economy'
        ]
    
    def fetch_from_rss_feeds(self) -> List[Dict]:
        """Fetch latest updates from RSS feeds"""
        updates = []
        
        for feed_url in self.news_sources + self.official_sources['rss_feeds']:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:  # Get latest 5 entries
                    if self._is_compliance_related(entry.title + " " + entry.get('summary', '')):
                        updates.append({
                            'title': entry.title,
                            'description': entry.get('summary', '')[:200] + "...",
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'source': feed.feed.get('title', 'RSS Feed'),
                            'url': entry.get('link', ''),
                            'category': self._categorize_update(entry.title + " " + entry.get('summary', ''))
                        })
            except Exception as e:
                continue
        
        return updates
    
    def scrape_official_websites(self) -> List[Dict]:
        """Scrape official government websites for latest notifications"""
        updates = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for category, urls in self.official_sources.items():
            if category == 'rss_feeds':
                continue
                
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for notification links and titles
                        notifications = self._extract_notifications(soup, category)
                        updates.extend(notifications[:3])  # Get latest 3 from each source
                        
                except Exception as e:
                    continue
        
        return updates
    
    def _extract_notifications(self, soup, category) -> List[Dict]:
        """Extract notifications from parsed HTML"""
        notifications = []
        
        # Common selectors for government websites
        selectors = [
            '.notification-item', '.news-item', '.latest-news',
            'li:contains("notification")', 'a[href*="notification"]',
            '.content-title', '.news-title', 'h3', 'h4'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)[:5]
                for element in elements:
                    title = element.get_text().strip()
                    if len(title) > 20 and self._is_compliance_related(title):
                        notifications.append({
                            'title': title,
                            'description': self._extract_description(element),
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'source': f'Official {category.upper()} Portal',
                            'category': self._categorize_update(title),
                            'url': self._extract_link(element)
                        })
                        if len(notifications) >= 3:
                            break
            except:
                continue
                
        return notifications
    
    def _is_compliance_related(self, text: str) -> bool:
        """Check if text is related to tax compliance"""
        keywords = [
            'gst', 'tds', 'income tax', 'itr', 'notification', 'circular',
            'amendment', 'rule', 'rate', 'deadline', 'filing', 'return',
            'compliance', 'audit', 'penalty', 'exemption', 'deduction',
            'corporate tax', 'service tax', 'customs', 'excise'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    
    def _categorize_update(self, text: str) -> str:
        """Categorize update based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['gst', 'goods and services tax']):
            return 'GST'
        elif any(word in text_lower for word in ['tds', 'tax deducted at source']):
            return 'TDS'
        elif any(word in text_lower for word in ['income tax', 'itr', 'personal tax']):
            return 'Income Tax'
        elif any(word in text_lower for word in ['corporate', 'company', 'mca']):
            return 'Corporate Tax'
        else:
            return 'General'
    
    def _extract_description(self, element) -> str:
        """Extract description from element"""
        # Try to find description in nearby elements
        description = ""
        try:
            # Look for description in next sibling or parent
            parent = element.parent
            if parent:
                desc_element = parent.find('p') or parent.find('div', class_='description')
                if desc_element:
                    description = desc_element.get_text().strip()[:200]
        except:
            pass
        
        return description or "Click to read more details..."
    
    def _extract_link(self, element) -> str:
        """Extract link from element"""
        try:
            link = element.find('a')
            if link and link.get('href'):
                return link.get('href')
        except:
            pass
        return ""

# Enhanced Gemini-powered content analysis
def analyze_with_gemini(content: str, gemini_model) -> Dict:
    """Use Gemini to analyze and structure compliance content"""
    if not gemini_model:
        return None
    
    try:
        prompt = f"""
        Analyze this tax/compliance related content and extract key information:
        
        Content: {content}
        
        Please provide a structured response with:
        1. Main topic/title
        2. Category (GST/TDS/Income Tax/Corporate Tax)
        3. Severity level (high/medium/low)
        4. Key changes or updates
        5. Action required (yes/no)
        6. Deadline (if any)
        7. Brief summary (max 150 words)
        
        Respond in JSON format.
        """
        
        response = gemini_model.generate_content(prompt)
        
        # Try to parse JSON from response
        try:
            result = json.loads(response.text)
            return result
        except:
            # If JSON parsing fails, create structured response
            return {
                'title': 'Compliance Update',
                'category': 'General',
                'severity': 'medium',
                'summary': response.text[:200],
                'action_required': False
            }
    
    except Exception as e:
        return None

# Real-time compliance fetcher
@st.cache_data(ttl=300)  # Cache for 5 minutes only
def get_live_compliance_updates() -> List[Dict]:
    """Fetch real-time compliance updates from multiple sources"""
    updater = LiveComplianceUpdater()
    gemini_model = init_gemini()
    
    all_updates = []
    
    with st.spinner("🔄 Fetching live updates from government sources..."):
        # Fetch from RSS feeds
        rss_updates = updater.fetch_from_rss_feeds()
        all_updates.extend(rss_updates)
        
        # Fetch from official websites
        web_updates = updater.scrape_official_websites()
        all_updates.extend(web_updates)
    
    # Process with Gemini for better structure
    enhanced_updates = []
    for update in all_updates[:10]:  # Process top 10
        if gemini_model:
            gemini_analysis = analyze_with_gemini(
                f"{update.get('title', '')} {update.get('description', '')}", 
                gemini_model
            )
            if gemini_analysis:
                update.update(gemini_analysis)
        
        # Add severity and action flags
        update['severity'] = update.get('severity', 'medium')
        update['action_required'] = 'deadline' in update.get('description', '').lower() or \
                                  'action' in update.get('description', '').lower()
        
        enhanced_updates.append(update)
    
    # Remove duplicates based on title similarity
    unique_updates = []
    seen_titles = set()
    
    for update in enhanced_updates:
        title_key = update.get('title', '')[:50].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_updates.append(update)
    
    return unique_updates

# MySQL Database connection
@st.cache_resource
# Replace your current init_database() function with this:

@st.cache_resource
def init_database():
    """Initialize MySQL database connection with your credentials"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="finease_app",
            password="StrongPassword123!",
            database="fineaseai",
            auth_plugin='mysql_native_password'  # Important for MySQL 8+
        )
        
        # Verify connection
        if conn.is_connected():
            db_info = conn.get_server_info()
            st.success(f"Connected to MySQL Server version {db_info}")
            return conn
            
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.error("Please ensure:")
        st.error("1. MySQL server is running")
        st.error("2. Database credentials are correct")
        st.error("3. User 'finease_app' has proper privileges")
        return None
        
        # Test the connection
        if conn.is_connected():
            db_info = conn.get_server_info()
            st.success(f"Connected to MySQL Server version {db_info}")
            return conn
            
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

# Fetch accounting data from MySQL database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_accounting_data(conn):
    """Fetch data from MySQL database"""
    try:
        # Create cursor
        cursor = conn.cursor(dictionary=True)
        
        # Transactions query
        transactions_query = """
        SELECT 
            id, date, amount, category, vendor, gst_amount, tds_amount, 
            invoice_number, description, document_path
        FROM transactions 
        ORDER BY date DESC 
        LIMIT 1000
        """
        
        # Vendors query
        vendors_query = """
        SELECT vendor_name, total_amount, gst_number, pan_number
        FROM vendors
        """
        
        # Execute queries
        cursor.execute(transactions_query)
        transactions = cursor.fetchall()
        transactions_df = pd.DataFrame(transactions)
        
        cursor.execute(vendors_query)
        vendors = cursor.fetchall()
        vendors_df = pd.DataFrame(vendors)
        
        return transactions_df, vendors_df
        
    except Error as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        if 'cursor' in locals():
            cursor.close()

# Compliance analysis based on your accounting data
def analyze_compliance(transactions_df):
    """Analyze compliance based on actual accounting data"""
    compliance_issues = []
    
    if not transactions_df.empty:
        # GST Compliance Check
        high_value_transactions = transactions_df[transactions_df['amount'] > 200000]
        if not high_value_transactions.empty:
            compliance_issues.append({
                "type": "GST Compliance",
                "severity": "high",
                "count": len(high_value_transactions),
                "description": f"{len(high_value_transactions)} transactions above ₹2 lakh require special GST attention"
            })
        
        # TDS Compliance Check
        tds_applicable = transactions_df[
            (transactions_df['category'].isin(['Professional Services', 'Rent', 'Commission'])) & 
            (transactions_df['amount'] > 30000)
        ]
        if not tds_applicable.empty:
            missing_tds = tds_applicable[tds_applicable['tds_amount'].isna() | (tds_applicable['tds_amount'] == 0)]
            if not missing_tds.empty:
                compliance_issues.append({
                    "type": "TDS Missing",
                    "severity": "high",
                    "count": len(missing_tds),
                    "description": f"{len(missing_tds)} transactions may require TDS deduction"
                })
        
        # Duplicate Invoice Check
        duplicate_invoices = transactions_df[transactions_df.duplicated(['invoice_number'], keep=False)]
        if not duplicate_invoices.empty:
            compliance_issues.append({
                "type": "Duplicate Invoices",
                "severity": "medium",
                "count": len(duplicate_invoices),
                "description": f"{len(duplicate_invoices)} duplicate invoice numbers found"
            })
    
    return compliance_issues

# Main dashboard
def main():
    add_custom_css()
    
    # Header with live status
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"""
    <div class="header-container">
        <h1 style="margin: 0; font-size: 3em;">⚖️ AI Compliance Dashboard</h1>
        <p style="margin: 10px 0 0 0; font-size: 1.2em; opacity: 0.9;">
            🔴 LIVE: Real-time compliance monitoring | Last updated: {current_time}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize database
    conn = None
    try:
        conn = init_database()
        if not conn or not conn.is_connected():
            st.error("Could not connect to database")
            return
            
        # Sidebar
        with st.sidebar:
            st.markdown("### 📊 Dashboard Controls")
            
            # Live update button
            if st.button("🔴 FETCH LIVE UPDATES", help="Get real-time updates from government sources"):
                st.cache_data.clear()
                st.rerun()
            
            # Auto-refresh toggle
            auto_refresh = st.toggle("🔄 Auto-refresh (5 min)", value=True)
            
            if auto_refresh:
                st.markdown("**Auto-refreshing every 5 minutes**")
                time.sleep(1)  # Small delay for UI
            
            # Date range selector
            st.markdown("### 📅 Date Range")
            start_date = st.date_input("From", value=date.today() - timedelta(days=30))
            end_date = st.date_input("To", value=date.today())
            
            # Category filter
            st.markdown("### 🏷️ Category Filter")
            categories = ["All", "GST", "TDS", "Income Tax", "Corporate Tax"]
            selected_category = st.selectbox("Select Category", categories)
            
            # Data sources status
            st.markdown("### 📡 Live Data Sources")
            st.markdown("✅ Income Tax Portal")
            st.markdown("✅ GST Portal") 
            st.markdown("✅ MCA Portal")
            st.markdown("✅ News RSS Feeds")
            st.markdown("✅ Gemini AI Analysis")
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Latest Updates Section with live data
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("## 🔴 LIVE Compliance Updates")
            st.markdown(f"*Fetched at {current_time} from official sources*")
            
            # Get live updates every time
            live_updates = get_live_compliance_updates()
            
            if live_updates:
                # Filter updates by category
                if selected_category != "All":
                    live_updates = [u for u in live_updates if u.get('category') == selected_category]
                
                for update in live_updates:
                    severity = update.get('severity', 'medium')
                    severity_class = f"alert-{severity}"
                    action_text = "⚡ ACTION REQUIRED" if update.get('action_required') else ""
                    source_text = update.get('source', 'Official Source')
                    
                    st.markdown(f"""
                    <div class="{severity_class}">
                        <h4>{update.get('title', 'Compliance Update')} {action_text}</h4>
                        <p>{update.get('description', 'No description available')}</p>
                        <small>📍 {update.get('category', 'General')} | 📅 {update.get('date', 'Today')} | 🔗 {source_text}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-medium">
                    <h4>🔄 Loading Live Updates...</h4>
                    <p>Fetching latest compliance updates from government sources...</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # AI Assistant Button
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("## 🤖 AI Assistant")
            st.markdown("Get instant help with compliance questions and regulatory guidance.")
            
            # Your chatbot integration goes here
            if st.button("💬 Chat with AI Assistant", key="chat_btn"):
                st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); 
                            color: white; padding: 20px; border-radius: 15px; text-align: center;">
                    <h3>🚀 AI Assistant Ready!</h3>
                    <p>Connect your chatbot here for instant compliance help</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Data Analysis Section
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("## 📊 Your Accounting Data Analysis")
        
        # Fetch data from your database
        transactions_df, vendors_df = fetch_accounting_data(conn)
        
        if not transactions_df.empty:
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("""
                <div class="metric-card">
                    <h3>📈 Total Transactions</h3>
                    <h2 style="color: #4ecdc4;">{}</h2>
                </div>
                """.format(len(transactions_df)), unsafe_allow_html=True)
            
            with col2:
                total_amount = transactions_df['amount'].sum()
                st.markdown("""
                <div class="metric-card">
                    <h3>💰 Total Amount</h3>
                    <h2 style="color: #667eea;">₹{:,.0f}</h2>
                </div>
                """.format(total_amount), unsafe_allow_html=True)
            
            with col3:
                gst_amount = transactions_df['gst_amount'].sum() if 'gst_amount' in transactions_df.columns else 0
                st.markdown("""
                <div class="metric-card">
                    <h3>🏛️ GST Collected</h3>
                    <h2 style="color: #ff6b6b;">₹{:,.0f}</h2>
                </div>
                """.format(gst_amount), unsafe_allow_html=True)
            
            with col4:
                tds_amount = transactions_df['tds_amount'].sum() if 'tds_amount' in transactions_df.columns else 0
                st.markdown("""
                <div class="metric-card">
                    <h3>📋 TDS Deducted</h3>
                    <h2 style="color: #ffa726;">₹{:,.0f}</h2>
                </div>
                """.format(tds_amount), unsafe_allow_html=True)
            
            # Compliance Issues based on live updates
            st.markdown("### ⚠️ Compliance Analysis")
            compliance_issues = analyze_compliance(transactions_df)
            
            if compliance_issues:
                for issue in compliance_issues:
                    severity_class = f"alert-{issue['severity']}"
                    st.markdown(f"""
                    <div class="{severity_class}">
                        <h4>{issue['type']} ({issue['count']} items)</h4>
                        <p>{issue['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-low">
                    <h4>✅ All Good!</h4>
                    <p>No compliance issues found in your current data.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Transaction trends
            if 'date' in transactions_df.columns:
                st.markdown("### 📈 Transaction Trends")
                transactions_df['date'] = pd.to_datetime(transactions_df['date'])
                monthly_data = transactions_df.groupby(transactions_df['date'].dt.to_period('M'))['amount'].sum().reset_index()
                monthly_data['date'] = monthly_data['date'].astype(str)
                
                fig = px.line(monthly_data, x='date', y='amount', 
                             title="Monthly Transaction Volume",
                             color_discrete_sequence=['#667eea'])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#2c3e50'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Recent transactions
            st.markdown("### 📋 Recent Transactions")
            st.dataframe(
                transactions_df.head(10),
                use_container_width=True,
                hide_index=True
            )
        
        else:
            st.warning("No data found in database. Please check your database connection and table structure.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer with live status
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; color: white; margin-top: 50px;">
            <p>🔴 LIVE DATA | 📡 Updates every 5 minutes | 🔄 Last refresh: {current_time}</p>
            <p>🌐 Real-time from: Income Tax Portal, GST Portal, MCA, RSS Feeds + Gemini AI</p>
            <p>⚡ Always more current than ChatGPT - Direct government source integration</p>
        </div>
        """, unsafe_allow_html=True)
    
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

# Auto-refresh mechanism
if __name__ == "__main__":
    main()
    
    # Auto-refresh every 5 minutes if enabled
    if st.session_state.get('auto_refresh', True):
        time.sleep(300)  # 5 minutes
        st.rerun()