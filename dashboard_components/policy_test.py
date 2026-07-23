"""
Policy Test Component
"""
import streamlit as st
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PolicyTest:
    """Policy testing component"""
    
    def render(self):
        """Render the policy test page"""
        st.markdown("## 🧪 Test Policy")
        st.caption("Test your policies with sample data before deploying")
        st.markdown("---")
        
        from policy_dashboard import load_policies, test_opa_policy
        policies = load_policies()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Policy Selection")
            if policies:
                policy_options = [f"{p.get('name')} ({p.get('package')})" for p in policies]
                selected = st.selectbox("Select Policy", policy_options)
                
                for p in policies:
                    if f"{p.get('name')} ({p.get('package')})" == selected:
                        st.session_state.selected_policy = p
                        break
                
                package = st.text_input("Package", st.session_state.selected_policy.get('package', 'main'))
                rule = st.text_input("Rule Name", "allow")
            else:
                st.warning("No policies found")
                package = "main"
                rule = "allow"
        
        with col2:
            st.subheader("Test Input")
            test_input_json = st.text_area(
                "Input JSON",
                value='{\n  "user": {\n    "role": "admin",\n    "name": "John"\n  },\n  "action": "read"\n}',
                height=200
            )
            
            if st.button("🧪 Run Test", use_container_width=True):
                try:
                    test_input = json.loads(test_input_json)
                    result = test_opa_policy(package, rule, test_input)
                    if result:
                        st.success("✅ Test completed!")
                        st.json(result)
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON format")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")