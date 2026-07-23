"""
Policy Create Component
"""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PolicyCreate:
    """Policy creation and editing component"""
    
    def __init__(self):
        self.editing = st.session_state.get('selected_policy') is not None
    
    def render(self):
        """Render the policy creation page"""
        st.markdown("## ➕ Create New Policy")
        st.caption("Build a new security policy with our visual editor")
        st.markdown("---")
        
        if self.editing:
            st.info(f"✏️ Editing policy: {st.session_state.selected_policy.get('name')}")
        
        with st.form("create_policy_form"):
            default = st.session_state.get('selected_policy')
            
            # Basic info
            col1, col2 = st.columns(2)
            with col1:
                policy_name = st.text_input(
                    "Policy Name *",
                    value=default.get('name', '') if default else '',
                    placeholder="e.g., data_privacy_policy"
                )
            
            with col2:
                package_name = st.selectbox(
                    "Package *",
                    ["privacy", "access", "main", "custom", "compliance", "security"],
                    index=0 if not default else 
                    ["privacy", "access", "main", "custom", "compliance", "security"].index(
                        default.get('package', 'privacy')
                    )
                )
            
            # Description
            description = st.text_area(
                "Description",
                value=default.get('description', '') if default else '',
                placeholder="What does this policy do?",
                height=60
            )
            
            # Status
            col1, col2 = st.columns(2)
            with col1:
                enabled = st.toggle("Enabled", value=default.get('enabled', True) if default else True)
            
            # Policy code
            st.subheader("📝 Policy Code")
            default_content = default.get('content', 'package main\n\nallow { true }') if default else 'package main\n\nallow { true }'
            policy_content = st.text_area(
                "Rego Policy",
                value=default_content,
                height=300
            )
            
            # Preview
            with st.expander("🔍 Preview Policy"):
                st.code(policy_content, language="rego")
            
            # Submit
            from policy_dashboard import call_api, load_policies
            
            if st.form_submit_button("💾 Save Policy"):
                if not policy_name:
                    st.error("❌ Policy name is required")
                elif not policy_content:
                    st.error("❌ Policy content is required")
                else:
                    policy_data = {
                        "name": policy_name,
                        "package": package_name,
                        "content": policy_content,
                        "enabled": enabled,
                        "description": description
                    }
                    
                    if self.editing:
                        result = call_api(f"/policies/{default.get('id')}", "PUT", policy_data)
                    else:
                        result = call_api("/policies", "POST", policy_data)
                    
                    if result:
                        st.success(f"✅ Policy {self.editing and 'updated' or 'created'} successfully!")
                        st.session_state.selected_policy = None
                        load_policies()
                        st.rerun()