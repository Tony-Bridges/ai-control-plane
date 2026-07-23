from fastapi_admin.app import app as admin_app
from fastapi_admin.providers.login import LoginProvider
from fastapi_admin.file_upload import FileUpload
from fastapi_admin.widgets import (
    displays, inputs, filters, 
    Table, Form, TextAreaInput
)
from fastapi_admin.models import AbstractAdmin
from typing import Any, Dict, List
import json
import os

class PolicyAdmin(AbstractAdmin):
    """Policy management admin interface"""
    
    # Policy list display
    list_display = [
        displays.IdColumn(),
        displays.Field("name", "Policy Name"),
        displays.Field("package", "Package"),
        displays.Field("enabled", "Status"),
        displays.Field("created_at", "Created"),
        displays.Field("updated_at", "Updated"),
    ]
    
    # Search fields
    search_fields = ["name", "package", "description"]
    
    # Filter fields
    list_filter = [
        filters.BooleanFilter("enabled"),
        filters.SelectFilter(
            "package",
            choices=[
                ("privacy", "Privacy"),
                ("access", "Access Control"),
                ("main", "Main"),
                ("custom", "Custom"),
            ]
        )
    ]
    
    async def get_list(self, request, pagination, filters, **kwargs):
        """Get list of policies"""
        # Read policies from files
        policies = []
        policies_dir = "policies/"
        
        if os.path.exists(policies_dir):
            for filename in os.listdir(policies_dir):
                if filename.endswith(".rego"):
                    with open(os.path.join(policies_dir, filename), 'r') as f:
                        content = f.read()
                        policies.append({
                            "id": filename,
                            "name": filename.replace(".rego", ""),
                            "package": self._extract_package(content),
                            "enabled": True,
                            "content": content,
                            "created_at": os.path.getctime(os.path.join(policies_dir, filename)),
                            "updated_at": os.path.getmtime(os.path.join(policies_dir, filename))
                        })
        return policies, len(policies)
    
    def _extract_package(self, content):
        """Extract package name from content"""
        for line in content.split('\n'):
            if line.startswith("package"):
                return line.replace("package", "").strip()
        return "unknown"