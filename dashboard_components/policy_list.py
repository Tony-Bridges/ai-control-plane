"""
Policy List Component
Displays and manages all policies
"""

import streamlit as st
import pandas as pd
from datetime import datetime

class PolicyList:
    """Policy list and management component"""
    
    def __init__(self):
        self.policies = st.session_state.get('policies', [])
    
    def render(self):
        """Render the policy list page"""
        st.markdown('<div class="main-title">📋 Policy List</div>', unsafe_allow_html=True)
        st.caption("Manage and edit your existing policies")
        st.markdown("---")
        
        # Load policies
        from policy_dashboard import load_policies
        policies = load_policies()
        
        if not policies:
            st.info("No policies found. Create your first policy!")
            return
        
        # Filters
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("🔍 Search policies", placeholder="Search by name or package...")
        with col2:
            filter_status = st.selectbox("Status", ["All", "Active", "Inactive", "Draft"])
        with col3:
            packages = list(set(p.get('package', 'unknown') for p in policies))
            filter_package = st.selectbox("Package", ["All"] + packages)
        
        # Filter policies
        filtered_policies = policies
        if search:
            filtered_policies = [p for p in filtered_policies if 
                               search.lower() in p.get('name', '').lower() or 
                               search.lower() in p.get('package', '').lower()]
        if filter_status != "All":
            status_map = {"Active": True, "Inactive": False, "Draft": None}
            filtered_policies = [p for p in filtered_policies if 
                               p.get('enabled') == status_map.get(filter_status)]
        if filter_package != "All":
            filtered_policies = [p for p in filtered_policies if 
                               p.get('package') == filter_package]
        
        # Display count
        st.write(f"Showing {len(filtered_policies)} policies")
        st.markdown("---")
        
        # Policy cards
        for policy in filtered_policies:
            self._render_policy_card(policy)
    
    def _render_policy_card(self, policy):
        """Render a single policy card"""
        with st.container():
            st.markdown('<div class="policy-card">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 2])
            
            with col1:
                st.markdown(f"### {policy.get('name', 'Unnamed')}")
                st.caption(f"ID: {policy.get('id', 'N/A')}")
            
            with col2:
                st.write(f"**Package:** {policy.get('package', 'unknown')}")
                content = policy.get('content', '')
                rules_count = content.count('allow') + content.count('deny')
                st.write(f"**Rules:** {rules_count}")
            
            with col3:
                status = policy.get('enabled', True)
                if status:
                    st.markdown('<span class="status-active">🟢 Active</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-inactive">🔴 Inactive</span>', unsafe_allow_html=True)
                last_updated = datetime.fromtimestamp(policy.get('updated', 0)).strftime("%Y-%m-%d %H:%M")
                st.caption(f"Updated: {last_updated}")
            
            with col4:
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    if st.button("👁️", key=f"view_{policy.get('id')}"):
                        st.session_state.selected_policy = policy
                        st.session_state.page = "📋 Policy List"
                with col_b:
                    if st.button("✏️", key=f"edit_{policy.get('id')}"):
                        st.session_state.selected_policy = policy
                        st.session_state.page = "➕ Create Policy"
                with col_c:
                    if st.button("🧪", key=f"test_{policy.get('id')}"):
                        st.session_state.selected_policy = policy
                        st.session_state.page = "🧪 Test Policy"
                with col_d:
                    if st.button("🗑️", key=f"delete_{policy.get('id')}"):
                        self._delete_policy(policy.get('id'))
            
            # Show content preview
            if policy.get('content'):
                with st.expander("📄 View Policy Code"):
                    st.code(policy.get('content', ''), language="rego")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
    
    def _delete_policy(self, policy_id):
        """Delete a policy"""
        from policy_dashboard import call_api
        if st.session_state.get('confirm_delete', False):
            result = call_api(f"/policies/{policy_id}", "DELETE")
            if result:
                st.success("✅ Policy deleted!")
                from policy_dashboard import load_policies
                load_policies()
                st.rerun()
        else:
            st.session_state.confirm_delete = True
            st.warning("Click delete again to confirm")