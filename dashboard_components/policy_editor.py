"""
Policy Editor Component
Advanced policy editing with syntax highlighting
"""

import streamlit as st

class PolicyEditor:
    """Advanced policy editor component"""
    
    def render(self, policy=None):
        """Render the policy editor"""
        st.markdown('<div class="main-title">📝 Policy Editor</div>', unsafe_allow_html=True)
        st.caption("Edit your policy with syntax highlighting and validation")
        st.markdown("---")
        
        if policy:
            self._render_editor(policy)
        else:
            st.info("Select a policy to edit")
    
    def _render_editor(self, policy):
        """Render the editor interface"""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Code editor
            st.subheader("Policy Code")
            content = st.text_area(
                "Rego Policy",
                value=policy.get('content', ''),
                height=400,
                key="policy_editor_content"
            )
            
            # Validation
            if st.button("🔍 Validate Policy"):
                self._validate_policy(content)
            
            # Save
            if st.button("💾 Save Policy", use_container_width=True):
                self._save_policy(policy, content)
        
        with col2:
            # Info panel
            st.subheader("Policy Info")
            st.write(f"**Name:** {policy.get('name', 'Unnamed')}")
            st.write(f"**Package:** {policy.get('package', 'unknown')}")
            st.write(f"**Status:** {'Active' if policy.get('enabled', True) else 'Inactive'}")
            st.write(f"**Created:** {policy.get('created', 'N/A')}")
            st.write(f"**Updated:** {policy.get('updated', 'N/A')}")
            
            # Quick actions
            st.markdown("---")
            st.subheader("Quick Actions")
            
            if st.button("🧪 Test Policy", use_container_width=True):
                st.session_state.selected_policy = policy
                st.session_state.page = "🧪 Test Policy"
                st.rerun()
            
            if st.button("📋 View in List", use_container_width=True):
                st.session_state.selected_policy = None
                st.session_state.page = "📋 Policy List"
                st.rerun()
    
    def _validate_policy(self, content):
        """Validate policy syntax"""
        # Basic validation
        if not content.strip():
            st.error("❌ Policy is empty")
            return
        
        # Check for required elements
        if "package" not in content:
            st.warning("⚠️ Missing 'package' declaration")
        else:
            st.success("✅ Package declaration found")
        
        if "allow" not in content and "deny" not in content:
            st.warning("⚠️ No 'allow' or 'deny' rules found")
        else:
            st.success("✅ Rules found")
        
        st.info("💡 Advanced validation requires OPA to be running")
        
        # Try OPA validation
        try:
            import requests
            response = requests.post(
                "http://localhost:8181/v1/compile",
                json={"input": content}
            )
            if response.status_code == 200:
                st.success("✅ Policy compiled successfully!")
            else:
                st.error(f"❌ Compilation error: {response.text}")
        except:
            st.warning("⚠️ Could not connect to OPA for validation")
    
    def _save_policy(self, policy, content):
        """Save the edited policy"""
        from policy_dashboard import call_api, load_policies
        
        policy_data = {
            "name": policy.get('name'),
            "package": policy.get('package'),
            "content": content,
            "enabled": policy.get('enabled', True),
            "description": policy.get('description', '')
        }
        
        result = call_api(f"/policies/{policy.get('id')}", "PUT", policy_data)
        
        if result:
            st.success("✅ Policy updated successfully!")
            load_policies()
            st.rerun()