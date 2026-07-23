"""
AI Control Plane - Policy Management Dashboard
Main entry point for the Streamlit application
"""

import streamlit as st
import requests
import json
import os
import sys
from pathlib import Path

# Add the current directory to path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components - FIXED IMPORTS
from dashboard_components.policy_list import PolicyList
from dashboard_components.policy_create import PolicyCreate
from dashboard_components.policy_test import PolicyTest
from dashboard_components.policy_analytics import PolicyAnalytics
from dashboard_components.policy_editor import PolicyEditor

# Page configuration
st.set_page_config(
    page_title="AI Control Plane - Policy Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main title */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem 0;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    
    /* Policy cards */
    .policy-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .policy-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
    }
    
    /* Status badges */
    .status-active {
        background: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .status-inactive {
        background: #ef4444;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .status-draft {
        background: #f59e0b;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    /* Sidebar */
    .sidebar-section {
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Code editor */
    .code-editor {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'selected_policy' not in st.session_state:
    st.session_state.selected_policy = None
if 'policies' not in st.session_state:
    st.session_state.policies = []
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'policy_test_result' not in st.session_state:
    st.session_state.policy_test_result = None
if 'api_url' not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"
if 'opa_url' not in st.session_state:
    st.session_state.opa_url = "http://localhost:8181"
if 'test_package' not in st.session_state:
    st.session_state.test_package = "main"
if 'test_rule' not in st.session_state:
    st.session_state.test_rule = "allow"
if 'test_template' not in st.session_state:
    st.session_state.test_template = "Custom Input"
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False

# ============ HELPER FUNCTIONS ============

def call_api(endpoint, method="GET", data=None):
    """Make API calls to the backend"""
    try:
        url = f"{st.session_state.api_url}/api/v1{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        else:
            return None
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None

def load_policies():
    """Load all policies from the backend"""
    response = call_api("/policies")
    if response:
        st.session_state.policies = response
    return st.session_state.policies

def get_policy_stats():
    """Get policy statistics"""
    policies = st.session_state.policies
    total = len(policies)
    active = sum(1 for p in policies if p.get('enabled', True))
    
    # Count by package
    packages = {}
    for p in policies:
        pkg = p.get('package', 'unknown')
        packages[pkg] = packages.get(pkg, 0) + 1
    
    return {
        'total': total,
        'active': active,
        'inactive': total - active,
        'packages': packages
    }

def test_opa_policy(package, rule, input_data):
    """Test a policy against OPA"""
    try:
        response = requests.post(
            f"{st.session_state.opa_url}/v1/data/{package}/{rule}",
            json={"input": input_data}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"OPA Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"OPA Connection Error: {str(e)}")
        return None

# ============ DASHBOARD RENDER FUNCTION ============

def render_dashboard():
    """Render the dashboard page"""
    st.markdown('<div class="main-title">🛡️ Policy Management Dashboard</div>', unsafe_allow_html=True)
    st.caption("Manage and monitor your AI security policies in one place")
    st.markdown("---")
    
    # Load policies
    policies = load_policies()
    stats = get_policy_stats()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Policies", stats['total'], delta="+2 this week")
    with col2:
        st.metric("Active Policies", stats['active'], delta="+1")
    with col3:
        st.metric("Inactive Policies", stats['inactive'], delta="-1")
    with col4:
        st.metric("Policy Packages", len(stats['packages']), delta="+0")
    
    st.markdown("---")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Policy Distribution by Package")
        if stats['packages']:
            import plotly.express as px
            fig = px.pie(
                values=list(stats['packages'].values()),
                names=list(stats['packages'].keys()),
                title="Policy Packages",
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Recent Activity")
        activity_data = {
            "Time": ["2 min ago", "5 min ago", "10 min ago", "15 min ago", "30 min ago"],
            "User": ["admin", "alice", "bob", "admin", "charlie"],
            "Action": ["Created policy 'Data Privacy'", "Updated 'Access Control'", 
                      "Tested 'Rate Limiting'", "Disabled 'Legacy Policy'", "Created 'GDPR'"],
            "Status": ["✅ Success", "✅ Success", "❌ Failed", "✅ Success", "✅ Success"]
        }
        import pandas as pd
        df = pd.DataFrame(activity_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    
    # Recent policies
    st.subheader("Recent Policies")
    if policies:
        recent_policies = policies[:5]
        for policy in recent_policies:
            status = "🟢 Active" if policy.get('enabled', True) else "🔴 Inactive"
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{policy.get('name', 'Unnamed')}**")
                with col2:
                    st.write(f"Package: {policy.get('package', 'unknown')}")
                with col3:
                    st.write(status)
                with col4:
                    if st.button("View", key=f"view_{policy.get('id')}"):
                        st.session_state.selected_policy = policy
                        st.session_state.page = "📋 Policy List"
                        st.rerun()

# ============ SIDEBAR ============

with st.sidebar:
    st.markdown("### 🛡️ AI Control Plane")
    st.markdown("---")
    
    # API URL configuration
    st.markdown("### Configuration")
    st.session_state.api_url = st.text_input("API URL", st.session_state.api_url)
    st.session_state.opa_url = st.text_input("OPA URL", st.session_state.opa_url)
    
    st.markdown("---")
    
    # Navigation
    st.markdown("### Navigation")
    page = st.radio(
        "",
        [
            "📊 Dashboard",
            "📋 Policy List",
            "➕ Create Policy",
            "🧪 Test Policy",
            "📈 Analytics",
            "⚙️ Settings"
        ],
        index=0
    )
    st.session_state.page = page
    
    st.markdown("---")
    
    # Quick stats in sidebar
    stats = get_policy_stats()
    st.markdown("### Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Policies", stats['total'])
    with col2:
        st.metric("Active", stats['active'])
    
    st.markdown("---")
    
    # System status
    st.markdown("### System Status")
    try:
        response = requests.get(f"{st.session_state.api_url}/health", timeout=2)
        api_status = "🟢 Online" if response.status_code == 200 else "🔴 Offline"
    except:
        api_status = "🔴 Offline"
    
    try:
        response = requests.get(f"{st.session_state.opa_url}/v1/data", timeout=2)
        opa_status = "🟢 Online" if response.status_code == 200 else "🔴 Offline"
    except:
        opa_status = "🔴 Offline"
    
    st.write(f"**API:** {api_status}")
    st.write(f"**OPA:** {opa_status}")

# ============ PAGE ROUTER ============

# Get the current page
current_page = st.session_state.page

# Initialize component classes
policy_list = PolicyList()
policy_create = PolicyCreate()
policy_test = PolicyTest()
policy_analytics = PolicyAnalytics()
policy_editor = PolicyEditor()

# Render the appropriate page
if current_page == "📊 Dashboard":
    render_dashboard()

elif current_page == "📋 Policy List":
    policy_list.render()

elif current_page == "➕ Create Policy":
    policy_create.render()

elif current_page == "🧪 Test Policy":
    policy_test.render()

elif current_page == "📈 Analytics":
    policy_analytics.render()

elif current_page == "⚙️ Settings":
    st.markdown('<div class="main-title">⚙️ Settings</div>', unsafe_allow_html=True)
    st.caption("Configure your policy management dashboard")
    st.markdown("---")
    
    # General settings
    st.subheader("General Settings")
    col1, col2 = st.columns(2)
    with col1:
        auto_reload = st.toggle("Auto-reload policies on change", value=True)
    with col2:
        dark_mode = st.toggle("Dark mode", value=False)
    
    # API settings
    st.subheader("API Configuration")
    api_url = st.text_input("API URL", st.session_state.api_url)
    opa_url = st.text_input("OPA URL", st.session_state.opa_url)
    
    if st.button("💾 Save Settings"):
        st.session_state.api_url = api_url
        st.session_state.opa_url = opa_url
        st.success("✅ Settings saved!")
    
    # About
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    **AI Control Plane - Policy Management Dashboard v1.0.0**
    
    This dashboard provides a visual interface for managing OPA policies.
    
    Features:
    - 📋 Policy listing with search and filters
    - ➕ Visual policy creation with rule builder
    - 🧪 Policy testing with sample data
    - 📈 Analytics and monitoring
    - ⚙️ Configuration management
    """)

# ============ FOOTER ============
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 1rem;">
        🛡️ AI Control Plane Policy Manager v1.0.0 | 
        Built with ❤️ using Streamlit
    </div>
    """,
    unsafe_allow_html=True
)