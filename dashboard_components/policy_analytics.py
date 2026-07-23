"""
Policy Analytics Component
Displays charts and metrics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

class PolicyAnalytics:
    """Policy analytics and monitoring component"""
    
    def render(self):
        """Render the analytics page"""
        st.markdown('<div class="main-title">📈 Policy Analytics</div>', unsafe_allow_html=True)
        st.caption("Monitor policy performance and insights")
        st.markdown("---")
        
        # Metrics
        self._render_metrics()
        
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            self._render_decision_chart()
        with col2:
            self._render_pii_chart()
        
        # Violations
        self._render_violations()
    
    def _render_metrics(self):
        """Render metric cards"""
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Evaluations", "15,234", delta="+12%")
        with col2:
            st.metric("Blocked Requests", "1,892", delta="-8%", delta_color="inverse")
        with col3:
            st.metric("Allowed Requests", "13,342", delta="+11%")
        with col4:
            st.metric("Avg Decision Time", "2.3ms", delta="-0.5ms")
        
        st.markdown("---")
    
    def _render_decision_chart(self):
        """Render decision chart"""
        st.subheader("Policy Decisions (Last 7 Days)")
        
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        allowed = [120, 145, 132, 168, 190, 145, 98]
        blocked = [12, 15, 8, 10, 22, 18, 5]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Allowed', x=days, y=allowed, marker_color='#10b981'))
        fig.add_trace(go.Bar(name='Blocked', x=days, y=blocked, marker_color='#ef4444'))
        fig.update_layout(barmode='stack', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_pii_chart(self):
        """Render PII detection chart"""
        st.subheader("PII Detection by Type")
        
        pii_data = {
            "ID Numbers": 245,
            "Emails": 189,
            "Phone": 156,
            "Passport": 78,
            "Credit Card": 45,
            "Other": 32
        }
        
        fig = px.pie(
            values=list(pii_data.values()),
            names=list(pii_data.keys()),
            color_discrete_sequence=px.colors.sequential.Purples_r,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_violations(self):
        """Render violations table"""
        st.subheader("Recent Policy Violations")
        
        violations_data = {
            "Time": ["1 min ago", "3 min ago", "5 min ago", "8 min ago", "12 min ago"],
            "User": ["alice@company.com", "bob@company.com", "charlie@company.com", 
                    "dave@company.com", "eve@company.com"],
            "Policy": ["Data Privacy", "Access Control", "Rate Limit", "Data Privacy", "Access Control"],
            "Action": ["Read", "Write", "Read", "Delete", "Read"],
            "Resource": ["/data/customers", "/api/documents", "/api/rates", 
                        "/data/users", "/data/products"],
            "Reason": ["PII detected", "Unauthorized access", "Rate exceeded", 
                      "PII detected", "Insufficient role"],
        }
        
        df = pd.DataFrame(violations_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # Export
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📊 Export Report", use_container_width=True):
                st.success("✅ Report exported as PDF")