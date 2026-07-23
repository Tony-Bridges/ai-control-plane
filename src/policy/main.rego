package main

# ============ DATA CLASSIFICATION RULES ============

# Rule: Classify text based on content
classify_text(text) = "sensitive" {
    contains_pii(text)
}

classify_text(text) = "public" {
    not contains_pii(text)
}

# ============ ACCESS CONTROL RULES ============

# Rule: User can access if they have permission
allow_access(user, resource) {
    user.role == "admin"
}

allow_access(user, resource) {
    user.role == "manager"
    resource.department == user.department
}

allow_access(user, resource) {
    user.role == "viewer"
    resource.public == true
}

# ============ ACTION RULES ============

# Rule: Allowed actions
allowed_action(user, action) {
    action == "read"
    user.has_read_permission
}

allowed_action(user, action) {
    action == "write"
    user.has_write_permission
    user.role in ["admin", "manager"]
}

allowed_action(user, action) {
    action == "delete"
    user.role == "admin"
}

# ============ PII DETECTION RULES ============

# Check for Personal Identifiable Information
contains_pii(text) {
    contains_id_number(text)
}

contains_pii(text) {
    contains_email(text)
}

contains_pii(text) {
    contains_phone(text)
}

contains_pii(text) {
    contains_passport(text)
}

# South African ID Number
contains_id_number(text) {
    regex.match("\\b\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{3}\\s?\\d{1}\\b", text)
}

# Email
contains_email(text) {
    regex.match("\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", text)
}

# Phone (10 digits)
contains_phone(text) {
    regex.match("\\b\\d{10}\\b", text)
}

# Passport
contains_passport(text) {
    regex.match("\\b[A-Z][0-9]{8}\\b", text)
}

# ============ TENANT RULES ============

# Isolate tenant data
tenant_allowed(user, tenant_id) {
    user.tenant_id == tenant_id
}

tenant_allowed(user, tenant_id) {
    user.role == "admin"
}

# ============ RATE LIMITING RULES ============

# Max requests per minute
max_requests_per_minute = 60

rate_allowed(user) {
    count(user.requests_in_last_minute) < max_requests_per_minute
}

# ============ BUSINESS RULES ============

# Rule: Can access financial data
can_access_financial_data(user) {
    user.role == "admin"
}

can_access_financial_data(user) {
    user.role == "finance"
    user.department == user.requested_department
}

# Rule: Can access healthcare data
can_access_healthcare_data(user) {
    user.role == "admin"
}

can_access_healthcare_data(user) {
    user.role == "doctor"
    user.patient_id == user.requested_patient_id
}